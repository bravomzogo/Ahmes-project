from .models import Comment, Gallery

def admin_counts(request):
    if request.user.is_authenticated and request.user.is_admin:
        return {
            'pending_comments': Comment.objects.filter(is_approved=False).count(),
            'gallery_count': Gallery.objects.count(),
        }
    return {}











# context_processors.py
from .models import Message

def unread_messages_count(request):
    if request.user.is_authenticated:
        count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        print(f"DEBUG: Unread messages count for {request.user}: {count}")  # Debug output
        return {'unread_messages_count': count}
    return {}