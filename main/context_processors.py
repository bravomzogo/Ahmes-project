from .models import Comment, Gallery

def admin_counts(request):
    if request.user.is_authenticated and request.user.is_admin:
        return {
            'pending_comments': Comment.objects.filter(is_approved=False).count(),
            'gallery_count': Gallery.objects.count(),
        }
    return {}