# utils.py
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_otp_via_email(email, otp):
    """
    Send OTP via email instead of SMS
    """
    try:
        subject = 'Your AHMES Parent Portal OTP'
        
        # Create HTML email content
        html_message = render_to_string('academics/email_otp_template.html', {
            'otp': otp,
            'valid_minutes': 10
        })
        
        # Create plain text version
        plain_message = f"Your AHMES Parent Portal OTP is: {otp}. Valid for 10 minutes."
        
        # Send email
        send_mail(
            subject,
            plain_message,
            'bravomzogo@gmail.com',  # From email
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
            
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return False