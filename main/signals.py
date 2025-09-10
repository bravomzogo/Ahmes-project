from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog

def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if sender.__name__ == 'ActivityLog':
        return
    
    action = 'CREATE' if created else 'UPDATE'
    details = f"{sender.__name__} {instance.pk} was {action.lower()}d"
    
    ActivityLog.objects.create(
        content_object=instance,
        action=action,
        details=details
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender.__name__ == 'ActivityLog':
        return
    
    ActivityLog.objects.create(
        content_object=None,
        action='DELETE',
        details=f"{sender.__name__} {instance.pk} was deleted"
    )

# main/signals.py
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    try:
        ActivityLog.objects.create(
            user=user,
            action='LOGIN',
            details=f"User {user.username} logged in",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    except Exception as e:
        # Log the error but don't break the login process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log user login: {e}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    try:
        ActivityLog.objects.create(
            user=user,
            action='LOGOUT',
            details=f"User {user.username} logged out",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log user logout: {e}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    try:
        ActivityLog.objects.create(
            action='LOGIN_FAILED',
            details=f"Failed login attempt for username: {credentials.get('username', 'unknown')}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log login failure: {e}")