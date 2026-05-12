from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from fpl.models import Gameweek, Player, PlayerGameweekStats
from .models import Prediction, BestPickRecommendation
from .serializers import PredictionSerializer, BestPickSerializer
from .ml_loader import predict_player, predict_all_players_for_gw, BEST_MODEL_PER_POSITION, POSITION_MAP
from .tasks import task_run_predictions_for_gw


class PredictionListView(generics.ListAPIView):
    serializer_class = PredictionSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['gameweek', 'model_name', 'player__position']

    def get_queryset(self):
        qs = Prediction.objects.select_related('player__team', 'gameweek').all()
        gw_id = self.request.query_params.get('gameweek')
        if not gw_id:
            current = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()
            if current:
                qs = qs.filter(gameweek=current)
        return qs.order_by('-predicted_points')


class BestPicksView(generics.ListAPIView):
    serializer_class = BestPickSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        gw_id = self.request.query_params.get('gameweek')
        position = self.request.query_params.get('position')
        top_n = int(self.request.query_params.get('top', 10))

        if gw_id:
            qs = BestPickRecommendation.objects.filter(gameweek__fpl_id=gw_id)
        else:
            gw = Gameweek.objects.filter(is_next=True).first() or Gameweek.objects.filter(is_current=True).first()
            qs = BestPickRecommendation.objects.filter(gameweek=gw) if gw else BestPickRecommendation.objects.none()

        if position:
            qs = qs.filter(position=position)

        qs = qs.filter(rank_in_position__lte=top_n)
        return qs.select_related('player__team', 'gameweek').order_by('position', 'rank_in_position')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def predict_player_view(request, fpl_id):
    """
    On-demand prediction for a single player.
    Query params: model_type (optional)
    """
    try:
        player = Player.objects.select_related('team').get(fpl_id=fpl_id)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=status.HTTP_404_NOT_FOUND)

    model_type = request.query_params.get('model_type')
    gw_stats = PlayerGameweekStats.objects.filter(player=player).order_by('-gameweek__fpl_id')

    if not model_type:
        pos_name = POSITION_MAP.get(player.position, 'MID')
        model_type = BEST_MODEL_PER_POSITION.get(pos_name, 'lstm_base')

    pred = predict_player(player, gw_stats, model_type)

    if pred is None:
        return Response({
            'player': player.web_name,
            'error': 'Model not available. Ensure ML artifacts are loaded.',
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({
        'player_fpl_id': player.fpl_id,
        'player_name': player.web_name,
        'team': player.team.short_name if player.team else '',
        'position': player.get_position_display(),
        'price': player.price,
        'model_type': model_type,
        'predicted_points': round(pred, 2),
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def predict_all_view(request):
    """Run live predictions for all players (no DB write, for quick previews)."""
    position_filter = request.query_params.getlist('position')
    pos_ints = [int(p) for p in position_filter] if position_filter else None
    results = predict_all_players_for_gw(pos_ints)
    return Response({'count': len(results), 'results': results})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_predictions(request):
    """Admin: queue a Celery task to run predictions for the next GW."""
    gw_id = request.data.get('gameweek_id')
    task_run_predictions_for_gw.delay(gw_id)
    return Response({'detail': 'Prediction task queued.'})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def best_team_view(request):
    """
    Build and return the prediction-best XI + bench.
    Players are ranked purely by predicted points; budget is not a constraint.
    FPL rules still apply: valid formation, max 3 per club, squad composition.
    """
    from .optimizer import build_best_team
    result = build_best_team()
    return Response(result)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def track_record_view(request):
    """
    Returns full best-team (with pitch/squad) for N past GWs.
    Query params:
      n (int, default 3, max 30)
      gw (int) — single specific GW
    """
    from .optimizer import build_past_best_team
    from .models import ScorerWeights
    from fpl.models import Gameweek

    # Build captain_fpl_id lookup from cal_log so pitch view shows same captain
    # as the GW History table (both sourced from the same simulation run).
    sw = ScorerWeights.objects.first()
    log = (sw.calibration_log if sw else []) or []
    cap_id_by_gw: dict[int, int] = {
        entry['gw']: entry['captain_fpl_id']
        for entry in log
        if isinstance(entry, dict) and 'gw' in entry and entry.get('captain_fpl_id')
    }

    gw_param = request.query_params.get('gw')
    if gw_param:
        gw_id = int(gw_param)
        data = build_past_best_team(gw_id, captain_fpl_id=cap_id_by_gw.get(gw_id))
        return Response([data])

    n = min(int(request.query_params.get('n', 3)), 30)
    past_gws = Gameweek.objects.filter(finished=True).order_by('-fpl_id')[:n]
    results = [
        build_past_best_team(gw.fpl_id, captain_fpl_id=cap_id_by_gw.get(gw.fpl_id))
        for gw in past_gws
    ]
    return Response(results)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def gw_history_view(request):
    """
    Lightweight summary of all finished GWs + current GW prediction.
    Reads pre-computed results from the calibration_log in ScorerWeights,
    then appends the current/next GW prediction (no actual yet).

    Returns a list ordered GW1 → latest:
      {gw, predicted_pts, actual_pts, diff, mae, captain, formation,
       pos_bias, has_actual}
    """
    from .models import ScorerWeights
    from .optimizer import build_best_team
    from fpl.models import Gameweek

    # Load stored history from the learning simulation log
    sw = ScorerWeights.objects.first()
    log = (sw.calibration_log if sw else []) or []

    history = []
    for entry in log:
        if not isinstance(entry, dict) or 'gw' not in entry:
            continue
        _perfect = entry.get('perfect_pts')
        _actual  = entry.get('actual_pts')
        history.append({
            'gw':            entry.get('gw'),
            'gw_name':       f"Gameweek {entry.get('gw')}",
            'predicted_pts': entry.get('predicted_pts'),
            'actual_pts':    _actual,
            'diff':          entry.get('diff'),
            'perfect_pts':   _perfect,
            'model_gap':     entry.get('model_gap'),
            'squad_gap':     entry.get('squad_gap'),
            'mae':           entry.get('mae'),
            'captain':       entry.get('captain'),
            'formation':     entry.get('formation'),
            'pos_bias':      entry.get('pos_bias', {}),
            'n_players':     entry.get('n_players'),
            'has_actual':    True,
        })

    # Sort by GW number
    history.sort(key=lambda x: x['gw'])

    # Append current / next GW (GW30) — best team prediction, no actual
    gw30 = (Gameweek.objects.filter(is_next=True).first()
            or Gameweek.objects.filter(is_current=True).first())
    if gw30:
        covered = {h['gw'] for h in history}
        if gw30.fpl_id not in covered:
            team = build_best_team()
            history.append({
                'gw':            gw30.fpl_id,
                'gw_name':       gw30.name,
                'predicted_pts': team.get('xi_predicted_pts'),
                'actual_pts':    None,
                'diff':          None,
                'mae':           None,
                'captain':       team.get('captain'),
                'formation':     team.get('formation'),
                'pos_bias':      {},
                'n_players':     None,
                'has_actual':    False,
            })

    return Response(history)


# ─── Edge feature helpers ─────────────────────────────────────────────────────

_POS_AVG = {1: 3.0, 2: 3.2, 3: 3.8, 4: 4.0}
_POS_MAP = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}


def _build_fdr_map(gw_id):
    """Return {team_id: fdr} for each team's next fixture from gw_id onward."""
    from fpl.models import Fixture
    fdr_map = {}
    try:
        for fix in (
            Fixture.objects
            .filter(finished=False, gameweek__fpl_id__gte=gw_id)
            .order_by('gameweek__fpl_id', 'kickoff_time')
        ):
            if fix.team_h_id and fix.team_h_id not in fdr_map:
                fdr_map[fix.team_h_id] = fix.team_h_difficulty or 3
            if fix.team_a_id and fix.team_a_id not in fdr_map:
                fdr_map[fix.team_a_id] = fix.team_a_difficulty or 3
    except Exception:
        pass
    return fdr_map


def _build_form_l3_map(gw_id):
    """Return {player_db_id: form_l3} — avg actual pts over last 3 completed GWs."""
    from fpl.models import PlayerGameweekStats
    from collections import defaultdict
    recent = (
        PlayerGameweekStats.objects
        .filter(gameweek__fpl_id__lt=gw_id, minutes__gt=0)
        .order_by('player_id', '-gameweek__fpl_id')
        .values('player_id', 'total_points')
    )
    pts_map = defaultdict(list)
    for row in recent:
        if len(pts_map[row['player_id']]) < 3:
            pts_map[row['player_id']].append(row['total_points'])
    return {
        pid: round(sum(pts) / len(pts), 2)
        for pid, pts in pts_map.items()
        if pts
    }


def _compute_ceiling_flag(predicted_points, fdr, form_l3, position):
    """
    Flag as 'high_ceiling' if ALL of:
      - predicted_points > position_avg * 1.3
      - fdr <= 2  (easy fixture)
      - form_l3 > position_avg  (in good recent form)
    Returns: 'high_ceiling' | 'solid' | 'avoid'
    """
    pos_avg = _POS_AVG.get(position, 3.5)
    if predicted_points > pos_avg * 1.3 and fdr <= 2 and form_l3 > pos_avg:
        return 'high_ceiling'
    if predicted_points < pos_avg * 0.7:
        return 'avoid'
    return 'solid'


# ─── Differentials endpoint ───────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def differentials_view(request):
    """
    GET /api/predictions/differentials/

    Returns top 15 differential picks:
      - predicted_points >= position average
      - ownership_pct <= 15%
      - chance_of_playing >= 75% (or not set)
    Sorted by value_score = predicted_points / ownership_pct (descending).
    """
    from .ml_loader import _fallback_score
    from fpl.models import Player, Gameweek

    gw = (Gameweek.objects.filter(is_next=True).first()
          or Gameweek.objects.filter(is_current=True).first())
    gw_id = gw.fpl_id if gw else 1

    fdr_map    = _build_fdr_map(gw_id)
    form_l3_map = _build_form_l3_map(gw_id)

    players = Player.objects.select_related('team').filter(
        status__in=('a', 'd'), now_cost__gt=0
    )

    results = []
    for pl in players:
        ownership = float(pl.selected_by_percent or 0)
        if ownership > 15.0:
            continue
        cop = pl.chance_of_playing_next_round
        if cop is not None and cop < 75:
            continue

        pred    = _fallback_score(pl)
        pos_avg = _POS_AVG.get(pl.position, 3.5)
        if pred < pos_avg:
            continue

        fdr     = fdr_map.get(pl.team_id, 3)
        form_l3 = form_l3_map.get(pl.pk, 0.0)
        ceiling = _compute_ceiling_flag(pred, fdr, form_l3, pl.position)

        # Avoid division by zero: treat 0% ownership as 0.5%
        value_score = round(pred / max(ownership, 0.5), 2)

        reason_parts = []
        if pred >= pos_avg * 1.3:
            reason_parts.append('High predicted pts')
        if ownership < 5:
            reason_parts.append('very low ownership')
        elif ownership < 10:
            reason_parts.append('low ownership')
        if fdr <= 2:
            reason_parts.append('easy fixture')
        if ceiling == 'high_ceiling':
            reason_parts.append('ceiling pick')

        results.append({
            'id':               pl.fpl_id,
            'name':             pl.web_name,
            'team':             pl.team.short_name if pl.team else '',
            'position':         _POS_MAP.get(pl.position, 'MID'),
            'predicted_points': round(pred, 2),
            'ownership_pct':    ownership,
            'fixture_difficulty': fdr,
            'form_l3':          form_l3,
            'ceiling_flag':     ceiling,
            'value_score':      value_score,
            'reason':           ', '.join(reason_parts) or 'Model pick',
        })

    results.sort(key=lambda x: x['value_score'], reverse=True)
    return Response(results[:15])


# ─── Community compare endpoint ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def community_compare_view(request):
    """
    GET /api/predictions/community-compare/

    Compares the model's predicted XI score against the community's consensus.
    Community proxy: FPL's own 'form' field (4-GW avg) as community expectation.
    Model proxy: _fallback_score() calibrated predictions.

    Returns:
      community_xi_predicted  — ownership-weighted community expected score
      model_xi_predicted      — model's best XI predicted score from calibration_log
      model_edge              — difference
      differentials           — top 5 where model rates higher than community by >1.5pts
      traps                   — top 5 where community rates higher than model by >1.5pts
    """
    from .ml_loader import _fallback_score
    from fpl.models import Player, Gameweek

    gw = (Gameweek.objects.filter(is_next=True).first()
          or Gameweek.objects.filter(is_current=True).first())
    gw_id = gw.fpl_id if gw else 1

    fdr_map = _build_fdr_map(gw_id)

    players = Player.objects.select_related('team').filter(
        status__in=('a', 'd'), now_cost__gt=0
    )

    all_players = []
    for pl in players:
        ownership  = float(pl.selected_by_percent or 0)
        model_pred = _fallback_score(pl)
        community  = float(pl.form or 0)   # FPL 4-GW form as community proxy
        diff       = round(model_pred - community, 2)

        all_players.append({
            'fpl_id':             pl.fpl_id,
            'name':               pl.web_name,
            'team':               pl.team.short_name if pl.team else '',
            'position':           _POS_MAP.get(pl.position, 'MID'),
            'model_pred':         round(model_pred, 2),
            'community_expected': round(community, 2),
            'diff':               diff,
            'ownership_pct':      ownership,
            'fixture_difficulty': fdr_map.get(pl.team_id, 3),
        })

    # Ownership-weighted community expected XI score
    total_own        = sum(p['ownership_pct'] for p in all_players) or 1
    community_xi_pred = (
        sum(p['community_expected'] * p['ownership_pct'] for p in all_players)
        / total_own * 11
    )

    # Model best XI from calibration_log (most recent entry without actual_pts = current GW)
    from .models import ScorerWeights
    sw  = ScorerWeights.objects.first()
    log = (sw.calibration_log if sw else []) or []
    model_xi_pred = None
    for entry in reversed(log):
        if entry.get('predicted_pts') and not entry.get('actual_pts'):
            model_xi_pred = entry['predicted_pts']
            break
    if model_xi_pred is None:
        # Fall back to last finished GW prediction
        for entry in reversed(log):
            if entry.get('predicted_pts'):
                model_xi_pred = entry['predicted_pts']
                break
    if model_xi_pred is None:
        # Last resort: build best team live
        from .optimizer import build_best_team
        team = build_best_team()
        model_xi_pred = team.get('xi_predicted_pts', 0) or 0

    model_edge = round(float(model_xi_pred) - community_xi_pred, 1)

    # Differentials: model > community by >1.5pts AND ownership <= 20%
    differentials = sorted(
        [p for p in all_players if p['diff'] > 1.5 and p['ownership_pct'] <= 20],
        key=lambda x: x['diff'], reverse=True
    )[:5]

    # Traps: community > model by >1.5pts AND ownership >= 10%
    traps = sorted(
        [p for p in all_players if p['diff'] < -1.5 and p['ownership_pct'] >= 10],
        key=lambda x: x['diff']
    )[:5]

    return Response({
        'community_xi_predicted': round(community_xi_pred, 1),
        'model_xi_predicted':     round(float(model_xi_pred), 1),
        'model_edge':             model_edge,
        'differentials':          differentials,
        'traps':                  traps,
    })
