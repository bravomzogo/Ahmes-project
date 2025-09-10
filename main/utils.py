# utils.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def send_otp_via_sms(phone_number, otp):
    """
    Send OTP via SMS using Africa's Talking API
    """
    try:
        # Format Tanzanian phone number
        if not phone_number.startswith('+'):
            if phone_number.startswith('0'):
                phone_number = '+255' + phone_number[1:]  # Convert 07... to +2557...
            else:
                phone_number = '+255' + phone_number
        
        message = f"Your AHMES Parent Portal OTP is: {otp}. Valid for 10 minutes."
        
        # Always log the OTP for debugging
        logger.info(f"Attempting to send OTP to {phone_number}: {otp}")
        
        # Get Africa's Talking credentials from settings
        username = getattr(settings, 'AFRICASTALKING_USERNAME', 'sandbox')
        api_key = getattr(settings, 'AFRICASTALKING_API_KEY', 'atsk_cab59d0e52963c0fa8fd02f2b1f0855a0b344175ad19a47ad7a4fc25c981b01aa8320f47')
        
        if not username or not api_key:
            logger.error("Africa's Talking credentials not configured")
            return False
        
        # Use Africa's Talking API directly (more reliable than SDK)
        url = "https://api.africastalking.com/version1/messaging"
        headers = {
            "ApiKey": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "username": username,
            "to": phone_number,
            "message": message,
            "from": "AHMES"  # Your approved sender ID
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 201:
            result = response.json()
            if result['SMSMessageData']['Recipients'][0]['status'] == 'Success':
                logger.info(f"SMS sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"SMS failed: {result}")
                return False
        else:
            logger.error(f"Africa's Talking API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False