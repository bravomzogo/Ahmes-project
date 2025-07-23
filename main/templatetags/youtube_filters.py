from django import template
import re

register = template.Library()

@register.filter(name='duration_format')
def duration_format(duration_str):
    """Convert YouTube duration (PT#H#M#S) to readable format"""
    if not duration_str:
        return '0:00'
    
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return '0:00'
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"