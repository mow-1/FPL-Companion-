import logging

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from fpl.fpl_api import get_manager_info, get_manager_history, get_manager_picks
from fpl.models import Gameweek, Player
from fpl.sync import sync_player_gw_stats
from .models import Squad, SquadPlayer, TransferSuggestion, CaptainSuggestion, ChipAdvice
from .serializers import (
    SquadSerializer, TransferSuggestionSerializer,
    CaptainSuggestionSerializer, ChipAdviceSerializer,
)
from .advisor import generate_transfer_suggestions, generate_captain_suggestion, generate_chip_advice, get_transfer_advice, get_best_xi_reasoning
from .optimizer import get_best_xi


# ─── Squad ────────────────────────────────────────────────────────────────────

class SquadListView(generics.ListAPIView):
    serializer_class = SquadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Squad.objects.filter(user=self.request.user).prefetch_related(
            'players__player__team'
        ).order_by('-gameweek__fpl_id')


class SquadDetailView(generics.RetrieveAPIView):
    serializer_class = SquadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        gw_id = self.kwargs.get('gw_id')
        if gw_id:
            return Squad.objects.get(user=self.request.user, gameweek__fpl_id=gw_id)
        return Squad.objects.filter(user=self.request.user).order_by('-gameweek__fpl_id').first()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_squad_from_fpl(request):
    """
    Pull the user's squad from official FPL API using their fpl_team_id.
    Requires user to have fpl_team_id set in their profile.
    """
    user = request.user
    if not user.fpl_team_id:
        return Response(
            {'error': 'Set your FPL team ID in your profile first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        gw = Gameweek.objects.filter(is_current=True).first()
        if not gw:
            return Response({'error': 'No current gameweek found.'}, status=status.HTTP_400_BAD_REQUEST)

        picks_data = get_manager_picks(user.fpl_team_id, gw.fpl_id)
        entry_data = get_manager_history(user.fpl_team_id)

        # Current season last entry
        current_season = entry_data.get('current', [])
        current_gw_entry = next((e for e in current_season if e['event'] == gw.fpl_id), {})

        squad, _ = Squad.objects.update_or_create(
            user=user, gameweek=gw,
            defaults={
                'bank': picks_data.get('entry_history', {}).get('bank', 0) / 10,
                'free_transfers': picks_data.get('entry_history', {}).get('event_transfers_cost', 0),
                'gameweek_points': current_gw_entry.get('points'),
                'total_points': current_gw_entry.get('total_points'),
                'overall_rank': current_gw_entry.get('overall_rank'),
            },
        )

        SquadPlayer.objects.filter(squad=squad).delete()
        players_to_create = []
        for pick in picks_data.get('picks', []):
            try:
                player = Player.objects.get(fpl_id=pick['element'])
            except Player.DoesNotExist:
                continue
            is_starter = pick['position'] <= 11
            bench_order = pick['position'] - 11 if not is_starter else None
            players_to_create.append(SquadPlayer(
                squad=squad,
                player=player,
                is_captain=pick.get('is_captain', False),
                is_vice_captain=pick.get('is_vice_captain', False),
                is_starter=is_starter,
                bench_order=bench_order,
                purchase_price=pick.get('purchase_price', player.now_cost),
                selling_price=pick.get('selling_price', player.now_cost),
            ))

        SquadPlayer.objects.bulk_create(players_to_create)
        squad_data = SquadSerializer(squad).data
        return Response({'detail': 'Squad synced.', 'squad': squad_data})

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Advisor endpoints ─────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def transfer_suggestions_view(request):
    """GET: return cached suggestions. POST: regenerate."""
    user = request.user
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()

    if request.method == 'POST':
        suggestions = generate_transfer_suggestions(user)
        return Response(TransferSuggestionSerializer(suggestions, many=True).data)

    qs = TransferSuggestion.objects.filter(user=user, gameweek=gw).select_related(
        'player_out__team', 'player_in__team', 'gameweek'
    ) if gw else TransferSuggestion.objects.none()
    return Response(TransferSuggestionSerializer(qs, many=True).data)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def accept_transfer_suggestion(request, suggestion_id):
    """Mark a transfer suggestion as accepted or rejected."""
    try:
        suggestion = TransferSuggestion.objects.get(id=suggestion_id, user=request.user)
    except TransferSuggestion.DoesNotExist:
        return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    accepted = request.data.get('accepted')
    if accepted is not None:
        suggestion.accepted = bool(accepted)
        suggestion.save(update_fields=['accepted'])
    return Response(TransferSuggestionSerializer(suggestion).data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def captain_suggestion_view(request):
    user = request.user
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()

    if request.method == 'POST':
        suggestion = generate_captain_suggestion(user)
        if not suggestion:
            return Response({'error': 'Could not generate — sync your squad first.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CaptainSuggestionSerializer(suggestion).data)

    try:
        suggestion = CaptainSuggestion.objects.get(user=user, gameweek=gw)
        return Response(CaptainSuggestionSerializer(suggestion).data)
    except CaptainSuggestion.DoesNotExist:
        return Response({'detail': 'No suggestion yet. POST to generate.'})


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def chip_advice_view(request):
    user = request.user
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()

    if request.method == 'POST':
        advice = generate_chip_advice(user)
        return Response(ChipAdviceSerializer(advice, many=True).data)

    qs = ChipAdvice.objects.filter(user=user, gameweek=gw) if gw else ChipAdvice.objects.none()
    return Response(ChipAdviceSerializer(qs, many=True).data)


def _get_next_fixture_fdr(player_team, gw_fpl_id):
    """
    Return the FDR for a player's next unfinished fixture.
    Looks for the nearest upcoming fixture (finished=False, gameweek >= current).
    Falls back to 3 (neutral) if no fixture found.
    """
    from fpl.models import Fixture
    from django.db.models import Q
    fix = (
        Fixture.objects
        .filter(finished=False, gameweek__fpl_id__gte=gw_fpl_id)
        .filter(Q(team_h=player_team) | Q(team_a=player_team))
        .order_by('gameweek__fpl_id', 'kickoff_time')
        .first()
    )
    if not fix:
        return 3
    return fix.team_h_difficulty if fix.team_h == player_team else fix.team_a_difficulty


def _squad_players_to_dicts(squad_players) -> list[dict]:
    """Convert SquadPlayer queryset to the list-of-dicts schema expected by advisor/optimizer."""
    from predictions.models import Prediction
    from django.db.models import Count, Q
    try:
        from predictions.models import DreamTeamEntry
        _has_dream = True
    except ImportError:
        _has_dream = False

    POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()
    gw_fpl_id = gw.fpl_id if gw else 1

    # Pre-fetch dream team stats for all squad players in one query
    dream_stats = {}
    if _has_dream:
        player_fpl_ids = [sp.player.fpl_id for sp in squad_players]
        rows = (
            DreamTeamEntry.objects
            .filter(player_fpl_id__in=player_fpl_ids)
            .values('player_fpl_id')
            .annotate(
                appearances=Count('id'),
                captain_count=Count('id', filter=Q(is_captain=True)),
            )
        )
        dream_stats = {r['player_fpl_id']: r for r in rows}

    result = []
    for sp in squad_players:
        p = sp.player
        pos = POSITION_MAP.get(p.position, str(p.position))

        pred_pts = 0.0
        if gw:
            pred = Prediction.objects.filter(player=p, gameweek=gw).order_by('-predicted_points').first()
            pred_pts = float(pred.predicted_points) if pred else float(p.form or 0)

        fdr = _get_next_fixture_fdr(p.team, gw_fpl_id)

        ds = dream_stats.get(p.fpl_id, {})
        result.append({
            'id':                         p.fpl_id,
            'name':                       p.web_name,
            'position':                   pos,
            'team':                       p.team.short_name if p.team else '',
            'price':                      round(p.now_cost / 10, 1),
            'predicted_points':           round(pred_pts, 2),
            'ownership_pct':              float(p.selected_by_percent or 0),
            'fixture_difficulty':         fdr,
            'status':                     p.status,
            'chance_of_playing_this_round': p.chance_of_playing_this_round,
            'dream_team_appearances':     ds.get('appearances', p.dream_team_count or 0),
            'captain_appearances':        ds.get('captain_count', 0),
            'photo_code':                 p.code,
        })
    return result


def _build_candidates(squad_dicts: list[dict], budget_remaining: float) -> list[dict]:
    """Top available players not in squad, filtered by position groups and budget."""
    from predictions.models import Prediction, BestPickRecommendation

    POSITION_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()
    gw_fpl_id = gw.fpl_id if gw else 1
    squad_ids = {p['id'] for p in squad_dicts}

    # Prices of squad players per position to compute max affordable replacement
    by_pos = {}
    for p in squad_dicts:
        by_pos.setdefault(p['position'], []).append(p['price'])

    max_budget_by_pos = {
        pos: min(prices) + budget_remaining
        for pos, prices in by_pos.items()
    }

    candidates = []
    for pos_code, max_cost in max_budget_by_pos.items():
        pos_int = {v: k for k, v in POSITION_MAP.items()}.get(pos_code)
        if pos_int is None:
            continue

        players = (
            Player.objects
            .filter(position=pos_int, now_cost__lte=int(max_cost * 10), status='a')
            .exclude(fpl_id__in=squad_ids)
            .select_related('team')
            .order_by('-total_points')[:20]
        )

        for p in players:
            pred_pts = 0.0
            if gw:
                pred = Prediction.objects.filter(player=p, gameweek=gw).order_by('-predicted_points').first()
                pred_pts = float(pred.predicted_points) if pred else float(p.form or 0)

            fdr = _get_next_fixture_fdr(p.team, gw_fpl_id if gw else 1)

            candidates.append({
                'id':                p.fpl_id,
                'name':              p.web_name,
                'position':          pos_code,
                'team':              p.team.short_name if p.team else '',
                'price':             round(p.now_cost / 10, 1),
                'predicted_points':  round(pred_pts, 2),
                'ownership_pct':     float(p.selected_by_percent or 0),
                'fixture_difficulty': fdr,
                'status':            p.status,
            })

    # Deduplicate by fpl_id (a player can appear in multiple position buckets)
    seen = set()
    unique = []
    for c in candidates:
        if c['id'] not in seen:
            seen.add(c['id'])
            unique.append(c)

    # Return top 30 by predicted points
    unique.sort(key=lambda c: -c['predicted_points'])
    return unique[:30]


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def claude_advice_view(request):
    """
    GET  /api/manager/advice/
        Auto-loads the authenticated user's current squad from DB, builds
        candidate list, calls Claude for transfer advice, runs LP optimizer
        for best-XI, returns combined JSON.

    POST /api/manager/advice/
        Body: { "squad": [...], "budget_remaining": float, "free_transfers": int }
        Uses the provided squad instead of DB lookup.

    Response:
        {
          "best_xi":         { starting_xi, bench, formation, captain, vice_captain },
          "transfer_advice": { transfer_out, transfer_in, budget_after, risk_level, reasoning }
        }
    """
    if request.method == 'GET':
        user = request.user
        squad_obj = Squad.objects.filter(user=user).prefetch_related(
            'players__player__team'
        ).order_by('-gameweek__fpl_id').first()

        if not squad_obj:
            return Response(
                {'error': 'No squad found. Sync your squad first via POST /api/manager/squad/sync/'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        squad_players = squad_obj.players.select_related('player__team').all()
        squad_dicts = _squad_players_to_dicts(squad_players)
        budget_remaining = float(squad_obj.bank or 0)
        free_transfers = int(squad_obj.free_transfers or 1)

    else:  # POST
        squad_dicts = request.data.get('squad')
        budget_remaining = float(request.data.get('budget_remaining', 0))
        free_transfers = int(request.data.get('free_transfers', 1))

        if not squad_dicts or not isinstance(squad_dicts, list):
            return Response(
                {'error': '"squad" must be a non-empty list of player dicts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    candidates = _build_candidates(squad_dicts, budget_remaining)

    try:
        transfer_advice = get_transfer_advice(squad_dicts, candidates, budget_remaining, free_transfers)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        best_xi = get_best_xi(squad_dicts)
    except Exception as e:
        return Response({'error': f'Optimizer error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Layer 4: Groq critique of the PuLP result
    try:
        xi_reasoning = get_best_xi_reasoning(best_xi, candidates, budget_remaining, free_transfers)
    except Exception as e:
        logger.warning("XI reasoning failed: %s", e)
        xi_reasoning = {'approved': True, 'swaps': [], 'captain_reasoning': '',
                        'team_rating': 'average', 'overall_comment': ''}

    return Response({
        'best_xi':         best_xi,
        'xi_reasoning':    xi_reasoning,
        'transfer_advice': transfer_advice,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_view(request):
    """One-shot endpoint: current squad + suggestions + captain pick."""
    user = request.user
    gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()

    squad = Squad.objects.filter(user=user).prefetch_related('players__player__team').order_by('-gameweek__fpl_id').first()
    transfers = TransferSuggestion.objects.filter(user=user, gameweek=gw).select_related(
        'player_out__team', 'player_in__team'
    )[:5] if gw else []
    captain = None
    if gw:
        captain = CaptainSuggestion.objects.filter(user=user, gameweek=gw).select_related(
            'captain__team', 'vice_captain__team', 'differential_captain'
        ).first()

    return Response({
        'current_gameweek': gw.name if gw else None,
        'squad': SquadSerializer(squad).data if squad else None,
        'transfer_suggestions': TransferSuggestionSerializer(transfers, many=True).data,
        'captain_suggestion': CaptainSuggestionSerializer(captain).data if captain else None,
    })
