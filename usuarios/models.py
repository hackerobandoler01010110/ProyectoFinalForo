# usuarios/models.py

from django.db import models
from django.utils import timezone # Necesario para la fecha de publicación

# Definición de opciones (CHOICES) para Comerciante (se mantiene)
RELACION_NEGOCIO_CHOICES = [
    ('DUENO', 'Dueño/a'),
    ('CONYUGE', 'Cónyuge'),
    ('HIJO', 'Hijo/a'),
    ('TRABAJADOR', 'Trabajador/a'),
    ('OTRO_RELACION', 'Otro'),
]

TIPO_NEGOCIO_CHOICES = [
    ('ALMACEN', 'Almacén'),
    ('BOTILLERIA', 'Botillería'),
    ('CARNICERIA', 'Carnicería'),
    ('COMIDA_RAPIDA', 'Comida rápida'),
    ('FERIA_LIBRE', 'Feria libre'),
    ('FERRETERIA', 'Ferretería'),
    ('FRUTERIA', 'Frutería y Verdulería'),
    ('OTRO_NEGOCIO', 'Otro'),
]

# OPCIONES PARA EL FORO (DEBE ESTAR FUERA DE LA CLASE POST para fácil acceso en Vistas/Templates)
CATEGORIA_POST_CHOICES = [
    ('DUDA', 'Duda / Pregunta'),
    ('OPINION', 'Opinión / Debate'),
    ('RECOMENDACION', 'Recomendación'),
    ('NOTICIA', 'Noticia del Sector'),
    ('GENERAL', 'General'),
]

class Comerciante(models.Model):
    # ... (Modelo Comerciante se mantiene) ...
    """
    Modelo que representa a un comerciante registrado en la plataforma.
    Corresponde a la tabla 'comerciantes' en la base de datos.
    """
    # 1. Información Personal
    nombre_apellido = models.CharField(
        max_length=150,
        verbose_name='Nombre y Apellido completo'
    )
    email = models.EmailField(
        max_length=100,
        unique=True,
        verbose_name='Correo Electrónico (Único)'
    )
    whatsapp = models.CharField(
        max_length=20,
        verbose_name='Número de WhatsApp'
    )
    
    # 2. Seguridad
    password_hash = models.CharField(
        max_length=255,
        verbose_name='Hash de Contraseña'
    )

    # 3. Información del Negocio
    relacion_negocio = models.CharField(
        max_length=50,
        choices=RELACION_NEGOCIO_CHOICES,
        verbose_name='Relación con el Negocio'
    )

    tipo_negocio = models.CharField(
        max_length=50,
        choices=TIPO_NEGOCIO_CHOICES,
        verbose_name='Tipo de Negocio'
    )

    comuna = models.CharField(
        max_length=50,
        verbose_name='Comuna de Ubicación'
    )

    # 4. Metadatos de Registro
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )

    ultima_conexion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Última Conexión'
    )

    class Meta:
        verbose_name = 'Comerciante'
        verbose_name_plural = 'Comerciantes'

    def __str__(self):
        # Representación legible del objeto Comerciante
        return f"{self.nombre_apellido} ({self.email})"


class Post(models.Model):
    """
    Modelo que representa una publicación en el foro.
    """
    comerciante = models.ForeignKey(
        'Comerciante',
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Comerciante'
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name='Título de la Publicación'
    )
    contenido = models.TextField(
        verbose_name='Contenido del Post'
    )
    categoria = models.CharField(
        max_length=50,
        choices=CATEGORIA_POST_CHOICES,
        default='GENERAL',
        verbose_name='Categoría'
    )
    imagen_url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='URL de Imagen/Link de Archivo Subido'
    )
    etiquetas = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Etiquetas (@usuarios, hashtags)'
    )
    fecha_publicacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Publicación'
    )
    
    class Meta:
        verbose_name = 'Publicación de Foro'
        verbose_name_plural = 'Publicaciones de Foro'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"[{self.get_categoria_display()}] {self.titulo} por {self.comerciante.nombre_apellido}"