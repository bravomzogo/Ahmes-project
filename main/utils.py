# utils.py
import africastalking
from django.conf import settings

# Initialize Africa's Talking
def initialize_africastalking():
    username = settings.AFRICASTALKING_USERNAME
    api_key = settings.AFRICASTALKING_API_KEY
    africastalking.initialize(username, api_key)
    return africastalking.SMS

def send_otp_via_sms(phone_number, otp):
    """
    Send OTP via SMS using Africa's Talking API
    """
    try:
        # Initialize Africa's Talking SMS service
        sms = initialize_africastalking()
        
        # Format Tanzanian phone number (add country code if missing)
        if not phone_number.startswith('+'):
            if phone_number.startswith('0'):
                phone_number = '+255' + phone_number[1:]  # Convert 07... to +2557...
            else:
                phone_number = '+255' + phone_number
        
        # Create message
        message = f"Your AHMES Parent Portal OTP is: {otp}. Valid for 10 minutes."
        
        # Send message
        if settings.USE_SANDBOX:
            # In sandbox mode, just print to console
            print(f"SMS to {phone_number}: {message}")
            response = {"SMSMessageData": {"Recipients": [{"status": "Success"}]}}
        else:
            # In production, actually send the SMS
            response = sms.send(message, [phone_number])
        
        # Check if message was sent successfully
        if response['SMSMessageData']['Recipients'][0]['status'] == 'Success':
            return True
        else:
            print(f"Failed to send SMS: {response}")
            return False
            
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False