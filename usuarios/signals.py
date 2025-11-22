# usuarios/signals.py

from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Comerciante # Importa tu modelo Comerciante

# Desconecta la señal de last_login. Esto se hace para evitar que Django 
# intente actualizar el campo 'last_login' que no existe en Comerciante.

# Nota: Si tu modelo Comerciante es el modelo de usuario principal de Django,
# usa get_user_model(). Si es un modelo auxiliar, usa Comerciante.

def disable_last_login_update(sender, user, request, **kwargs):
    """
    Función que previene la actualización del last_login.
    Dado que tu modelo Comerciante ya maneja 'ultima_conexion',
    simplemente retornamos None para saltar el proceso de Django.
    """
    # Aquí puedes hacer cualquier verificación si quieres, pero por ahora, solo la desconexión.
    pass

# Desconectar la señal global
# La señal está conectada a la función django.contrib.auth.models.update_last_login
try:
    from django.contrib.auth.models import update_last_login
    # Desconecta la señal antes de que se dispare
    user_logged_in.disconnect(update_last_login)
    
    # Reconecta con una función que no hace nada (o maneja tu propia lógica)
    user_logged_in.connect(disable_last_login_update, sender=Comerciante)
    
except ImportError:
    # Manejar si la importación falla por versión
    pass

@receiver(user_logged_in, sender=Comerciante)
def do_not_update_last_login(sender, request, **kwargs):
    pass