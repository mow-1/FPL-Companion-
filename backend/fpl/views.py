from django.db.models import Q
from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Team, Gameweek, Player, PlayerGameweekStats, Fixture
from .serializers import (
    TeamSerializer, GameweekSerializer, PlayerListSerializer,
    PlayerDetailSerializer, PlayerGameweekStatsSerializer, FixtureSerializer,
)
from .fpl_api import get_manager_info, get_manager_history, get_manager_picks
from .tasks import task_full_sync


class TeamListView(generics.ListAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.AllowAny]


class GameweekListView(generics.ListAPIView):
    queryset = Gameweek.objects.all()
    serializer_class = GameweekSerializer
    permission_classes = [permissions.AllowAny]


class CurrentGameweekView(generics.RetrieveAPIView):
    serializer_class = GameweekSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        gw = Gameweek.objects.filter(is_current=True).first()
        if not gw:
            gw = Gameweek.objects.filter(is_next=True).first()
        return gw


class PlayerListView(generics.ListAPIView):
    serializer_class = PlayerListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['position', 'team', 'status']
    search_fields = ['web_name', 'first_name', 'second_name']
    ordering_fields = ['total_points', 'now_cost', 'form', 'selected_by_percent', 'ict_index']
    ordering = ['-total_points']

    def get_queryset(self):
        qs = Player.objects.select_related('team').all()
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            qs = qs.filter(now_cost__gte=int(float(min_price) * 10))
        if max_price:
            qs = qs.filter(now_cost__lte=int(float(max_price) * 10))
        return qs


class PlayerDetailView(generics.RetrieveAPIView):
    queryset = Player.objects.select_related('team').all()
    serializer_class = PlayerDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'fpl_id'


class PlayerHistoryView(generics.ListAPIView):
    serializer_class = PlayerGameweekStatsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        fpl_id = self.kwargs['fpl_id']
        return PlayerGameweekStats.objects.filter(
            player__fpl_id=fpl_id
        ).select_related('gameweek', 'opponent_team').order_by('gameweek__fpl_id')


class FixtureListView(generics.ListAPIView):
    serializer_class = FixtureSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['gameweek', 'finished']

    def get_queryset(self):
        qs = Fixture.objects.select_related('gameweek', 'team_h', 'team_a').all()
        team_id = self.request.query_params.get('team')
        if team_id:
            qs = qs.filter(Q(team_h__fpl_id=team_id) | Q(team_a__fpl_id=team_id))
        return qs


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fpl_manager_proxy(request, manager_id):
    """Proxy the official FPL manager info."""
    try:
        data = get_manager_info(manager_id)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fpl_manager_history_proxy(request, manager_id):
    try:
        data = get_manager_history(manager_id)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fpl_manager_picks_proxy(request, manager_id, gameweek):
    try:
        data = get_manager_picks(manager_id, gameweek)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_sync(request):
    """Admin-only: trigger a full FPL data sync via Celery."""
    task_full_sync.delay()
    return Response({'detail': 'Full sync task queued.'})
