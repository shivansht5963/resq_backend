from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def home(request):
    """Render the ResQ homepage."""
    return render(request, 'home.html')


@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint for Render — always returns 200."""
    return JsonResponse({"status": "ok"})
