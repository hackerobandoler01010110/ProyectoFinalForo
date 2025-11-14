# usuarios/models.py

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings
# Importamos static para resolver la URL de la imagen por defecto
from django.templatetags.static import static 

# --- Opciones de Selección Múltiple ---

RELACION_NEGOCIO_CHOICES = [
    ('DUEÑO', 'Dueño/a'),
    ('ADMIN', 'Administrador/a'),
    ('EMPLEADO', 'Empleado/a clave'),
    ('FAMILIAR', 'Familiar a cargo'),
]

TIPO_NEGOCIO_CHOICES = [
    ('ALMACEN', 'Almacén de Barrio'),
    ('MINIMARKET', 'Minimarket'),
    ('BOTILLERIA', 'Botillería'),
    ('PANADERIA', 'Panadería/Pastelería'),
    ('FERIA', 'Feria Libre'),
    ('KIOSCO', 'Kiosco'),
    ('FOODTRUCK', 'Food Truck/Carro de Comida'),
]

# Opciones de Intereses (Mínimo 15 para la selección)
INTERESTS_CHOICES = [
    ('MARKETING', 'Marketing Digital'),
    ('INVENTARIO', 'Gestión de Inventario'),
    ('PROVEEDORES', 'Proveedores Locales'),
    ('FINANZAS', 'Finanzas y Contabilidad'),
    ('CLIENTES', 'Atención al Cliente'),
    ('LEYES', 'Normativa y Leyes'),
    ('TECNOLOGIA', 'Uso de Tecnología y Apps'),
    ('REDES_SOCIALES', 'Redes Sociales para Negocios'),
    ('VENTAS', 'Técnicas de Ventas'),
    ('CREDITOS', 'Créditos y Préstamos Pyme'),
    ('IMPUESTOS', 'Impuestos y Contabilidad Básica'),
    ('DECORACION', 'Decoración y Merchandising'),
    ('SOSTENIBILIDAD', 'Sostenibilidad y Reciclaje'),
    ('SEGURIDAD', 'Seguridad del Negocio'),
    ('LOGISTICA', 'Logística y Reparto'),
    ('INNOVACION', 'Innovación en Productos'),
    ('EMPRENDIMIENTO', 'Modelos de Emprendimiento'),
    ('SEGUROS', 'Seguros para Negocios'),
]

# Categorías para publicaciones del foro (se mantiene)
CATEGORIA_POST_CHOICES = [
    ('DUDA', 'Duda / Pregunta'),
    ('OPINION', 'Opinión / Debate'),
    ('RECOMENDACION', 'Recomendación'),
    ('NOTICIA', 'Noticia del Sector'),
    ('GENERAL', 'General'),
]


class Comerciante(models.Model):
    # Campos de Autenticación y Contacto
    nombre_apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128) # Almacena la contraseña hasheada
    
    # Validador de WhatsApp para formato chileno (+569XXXXXXXX)
    whatsapp_validator = RegexValidator(
        regex=r'^\+569\d{8}$', 
        message="El formato debe ser '+569XXXXXXXX'."
    )
    whatsapp = models.CharField(
        validators=[whatsapp_validator], 
        max_length=12, 
        blank=True, 
        null=True,
        help_text="Formato: +569XXXXXXXX"
    )

    # Campos de Negocio
    relacion_negocio = models.CharField(max_length=10, choices=RELACION_NEGOCIO_CHOICES)
    tipo_negocio = models.CharField(max_length=20, choices=TIPO_NEGOCIO_CHOICES)
    comuna = models.CharField(max_length=50) # Nombre de la comuna

    # Campos de Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_conexion = models.DateTimeField(default=timezone.now)

    # --- NUEVOS CAMPOS DE PERFIL ---
    
    # 1. Foto de Perfil
    # Usamos la cadena literal como default para que funcione la migración.
    foto_perfil = models.ImageField(
        upload_to='perfiles/', 
        # La ruta del default debe coincidir con la definida en settings.py y existir en static/
        default='usuarios/img/default_profile.png', 
        blank=True, 
        null=True
    )

    # 2. Intereses (guardamos una lista de códigos separados por coma)
    intereses = models.CharField(
        max_length=512, 
        default='', 
        blank=True, 
        help_text="Códigos de intereses separados por coma."
    )
    
    # 3. Campo para el nombre del negocio
    nombre_negocio = models.CharField(max_length=100, default='Mi Negocio Local', blank=True)
    
    class Meta:
        verbose_name = 'Comerciante'
        verbose_name_plural = 'Comerciantes'

    def __str__(self):
        return f"{self.nombre_apellido} ({self.email})"

    # Método para obtener la URL de la foto de perfil (maneja el valor por defecto)
    def get_profile_picture_url(self):
        # La ruta por defecto usada como string
        DEFAULT_IMAGE_PATH = 'usuarios/img/default_profile.png'
        
        # Si tiene una foto subida y no es el placeholder, retorna su URL MEDIA
        if self.foto_perfil.name and self.foto_perfil.name != DEFAULT_IMAGE_PATH:
            return self.foto_perfil.url
        
        # Si no, retorna la URL estática de la imagen por defecto
        # La función static() buscará 'img/default_profile.png' dentro de la carpeta 'static' de la app 'usuarios'
        return static('img/default_profile.png')


class Post(models.Model):
    """
    Modelo que representa una publicación en el foro.
    """
    comerciante = models.ForeignKey(
        Comerciante,
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