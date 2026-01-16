from django.conf import settings


def adminend_view_only(request):
    """Expose ADMINEND_VIEW_ONLY to all templates as `adminend_view_only`."""
    return {'adminend_view_only': getattr(settings, 'ADMINEND_VIEW_ONLY', True)}
