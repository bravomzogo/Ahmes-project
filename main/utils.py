# utils.py (updated with correct sender ID)
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
        
        # Get Africa's Talking credentials
        username = getattr(settings, 'AFRICASTALKING_USERNAME', 'shaibu')
        api_key = getattr(settings, 'AFRICASTALKING_API_KEY', 'atsk_fe8fac6e9b297438cd3b231e9fd0582a48737d47d8b21365e11bbfcb468178acaf8a5213')
        
        # Send SMS - REMOVE the 'from' parameter or use an approved sender ID
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
            # REMOVE the 'from' parameter to use Africa's Talking default shortcode
            # OR use an approved sender ID from your dashboard
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        logger.info(f"SMS API Response: {response.status_code} - {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            
            # Handle response
            if ('SMSMessageData' in result and 
                'Recipients' in result['SMSMessageData'] and 
                len(result['SMSMessageData']['Recipients']) > 0):
                
                recipient = result['SMSMessageData']['Recipients'][0]
                if recipient['status'] == 'Success':
                    logger.info(f"SMS sent successfully to {phone_number}")
                    return True
                else:
                    error_message = recipient.get('message', 'Unknown error')
                    logger.error(f"SMS failed for {phone_number}: {error_message}")
                    return False
            else:
                # Check for specific error messages
                if ('SMSMessageData' in result and 
                    'Message' in result['SMSMessageData']):
                    error_msg = result['SMSMessageData']['Message']
                    logger.error(f"SMS failed: {error_msg}")
                    
                    # If it's a sender ID issue, try without sender ID
                    if 'InvalidSenderId' in error_msg:
                        logger.info("Retrying without sender ID...")
                        # Remove 'from' parameter and retry
                        if 'from' in data:
                            del data['from']
                            retry_response = requests.post(url, headers=headers, data=data)
                            logger.info(f"Retry response: {retry_response.status_code} - {retry_response.text}")
                            return retry_response.status_code == 201
                    
                    return False
                else:
                    # Unexpected but successful response
                    logger.warning(f"Unexpected API response: {result}")
                    return True
                    
        else:
            logger.error(f"Africa's Talking API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False