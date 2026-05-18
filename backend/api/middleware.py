import base64
import secrets

from django.conf import settings
from django.http import HttpResponse


class BetaBasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            not settings.BETA_BASIC_AUTH_ENABLED
            or request.method == "OPTIONS"
            or self._is_exempt(request.path)
        ):
            return self.get_response(request)

        if self._is_authorized(request.META.get("HTTP_AUTHORIZATION", "")):
            return self.get_response(request)

        response = HttpResponse("Authentication required.", status=401)
        response["WWW-Authenticate"] = f'Basic realm="{settings.BETA_BASIC_AUTH_REALM}"'
        return response

    def _is_exempt(self, path: str) -> bool:
        return any(path == exempt for exempt in settings.BETA_BASIC_AUTH_EXEMPT_PATHS)

    def _is_authorized(self, authorization: str) -> bool:
        if not authorization.startswith("Basic "):
            return False

        try:
            decoded = base64.b64decode(authorization.removeprefix("Basic ").strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False

        username, separator, password = decoded.partition(":")
        if separator != ":":
            return False

        return secrets.compare_digest(username, settings.BETA_BASIC_AUTH_USERNAME) and secrets.compare_digest(
            password,
            settings.BETA_BASIC_AUTH_PASSWORD,
        )
