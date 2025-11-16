from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a un valor de un diccionario por su clave."""
    if key in dictionary:
        return dictionary.get(key)
    return key
    
@register.filter
def add(value, arg):
    """Suma el argumento al valor."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except TypeError:
            return value