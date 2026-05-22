from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    """Liveness check: confirms the API is reachable and CORS is wired up."""
    return Response({"status": "ok", "service": "web-cemented-api"})
