# usuarios/backends.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import Comerciante # Asegúrate de importar tu modelo

class ComercianteBackend(BaseBackend):
    """
    Autentica al usuario usando el correo electrónico y la contraseña hash
    del modelo Comerciante.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # El username aquí es el email que pasa Django
        try:
            comerciante = Comerciante.objects.get(email=username)
        except Comerciante.DoesNotExist:
            return None # Usuario no encontrado

        # Usa tu lógica actual de verificación de contraseña
        if check_password(password, comerciante.password_hash):
            
            # Si el usuario es autenticado, Django necesita que el objeto 
            # tenga la propiedad 'is_active', incluso si no está implementada.
            # Como Comerciante no es un User estándar, lo devolvemos directamente
            # y confiamos en que tu modelo tiene los métodos mínimos requeridos.
            return comerciante 
        return None

    def get_user(self, user_id):
        """Requerido por Django para reconstruir el usuario a partir de la sesión."""
        try:
            return Comerciante.objects.get(pk=user_id)
        except Comerciante.DoesNotExist:
            return None