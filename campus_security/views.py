from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def home(request):
    """Render the ResQ homepage."""
    return render(request, 'home.html')
