from .models import ADDIS_AREAS, Listing

def site_context(request):
    return {
        'ADDIS_AREAS': ADDIS_AREAS,
        'SITE_NAME': 'Addis Realty',
        'pending_count': Listing.objects.filter(status='pending').count() if (
            request.user.is_authenticated and (request.user.is_admin_role or request.user.is_staff)
        ) else 0,
    }
