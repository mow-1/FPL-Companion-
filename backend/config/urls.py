from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        'name': 'FPL Manager Assistant API',
        'version': '1.0',
        'endpoints': {
            'auth': '/api/auth/',
            'fpl': '/api/fpl/',
            'predictions': '/api/predictions/',
            'manager': '/api/manager/',
            'admin': '/admin/',
        },
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/fpl/', include('fpl.urls')),
    path('api/predictions/', include('predictions.urls')),
    path('api/manager/', include('manager.urls')),
]
