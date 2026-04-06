from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LenientJWTAuthentication(JWTAuthentication):
    """
    JWT auth that returns None (anonymous) instead of raising 401
    when a token is present but invalid/expired. This lets AllowAny
    views work even when a stale token lingers in the client's localStorage.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError):
            return None
