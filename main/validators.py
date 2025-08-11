from django.core.exceptions import ValidationError
from urllib.parse import urlparse
import os

def validate_pdf_extension(value):
    if value:
        # Get the URL of the Cloudinary file
        url = value.url if hasattr(value, 'url') else str(value)
        # Parse the URL to get the path
        parsed = urlparse(url)
        # Get the file extension
        ext = os.path.splitext(parsed.path)[1][1:].lower()
        if ext != 'pdf':
            raise ValidationError('Only PDF files are allowed.')
