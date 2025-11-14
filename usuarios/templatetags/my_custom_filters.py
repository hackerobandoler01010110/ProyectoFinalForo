from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a un valor de un diccionario por su clave."""
    if key in dictionary:
        return dictionary.get(key)
    return key