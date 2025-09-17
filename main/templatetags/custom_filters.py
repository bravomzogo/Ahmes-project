# main/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def intcomma(value):
    """Format a number with comma as thousands separator and no decimals."""
    try:
        value = int(value)
        return "{:,}".format(value)
    except (ValueError, TypeError):
        return value