# create folder accounts/templatetags/__init__.py (empty file) too
from django import template
register = template.Library()

@register.filter
def add_class(field, css):
    return field.as_widget(attrs={"class": css})
