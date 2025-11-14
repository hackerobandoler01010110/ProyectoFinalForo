# usuarios/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError 
from django.contrib.auth.hashers import make_password, check_password
# Importar CATEGORIA_POST_CHOICES, Comerciante y Post
from .models import Comerciante, Post, CATEGORIA_POST_CHOICES 
from .forms import RegistroComercianteForm, LoginForm, PostForm 
from django.utils import timezone
# Necesario para guardar archivos en el sistema MEDIA_ROOT
from django.core.files.storage import default_storage 


def registro_comerciante_view(request):
    """
    Vista para manejar el registro de nuevos comerciantes.
    """
    if request.method == 'POST':
        form = RegistroComercianteForm(request.POST)
        if form.is_valid():
            
            # --- Lógica de Guardado ---
            raw_password = form.cleaned_data.pop('password')
            hashed_password = make_password(raw_password)

            nuevo_comerciante = form.save(commit=False)
            nuevo_comerciante.password_hash = hashed_password
            
            comuna_final = form.cleaned_data.get('comuna') 
            if comuna_final:
                nuevo_comerciante.comuna = comuna_final
            
            try:
                nuevo_comerciante.save()
                messages.success(request, '¡Registro exitoso! Ya puedes iniciar sesión.')
                return redirect('login') 
            
            except IntegrityError:
                messages.error(request, 'Este correo electrónico ya está registrado. Por favor, inicia sesión o usa otro correo.')
                print("ERROR DE DB: Intento de registro con email duplicado.")
            
            except Exception as e:
                messages.error(request, f'Ocurrió un error inesperado al guardar: {e}')
                print(f"ERROR DE DB GENERAL: {e}") 
                
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
            
    else:
        form = RegistroComercianteForm()
    
    context = {
        'form': form
    }
    return render(request, 'usuarios/cuenta.html', context)


# -------------------------------------------------------------------------------------
def login_view(request):
    """
    Vista para manejar el inicio de sesión de comerciantes registrados.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                comerciante = Comerciante.objects.get(email=email)

                if check_password(password, comerciante.password_hash):
                    comerciante.ultima_conexion = timezone.now()
                    comerciante.save(update_fields=['ultima_conexion'])

                    messages.success(request, f'¡Bienvenido {comerciante.nombre_apellido}!')
                    return redirect('plataforma_comerciante')

                else:
                    messages.error(request, 'Contraseña incorrecta. Intenta nuevamente.')

            except Comerciante.DoesNotExist:
                messages.error(request, 'Este correo no está registrado. Por favor, regístrate primero.')

        else:
            messages.error(request, 'Por favor, completa todos los campos correctamente.')

    else:
        form = LoginForm()

    context = {
        'form': form
    }
    return render(request, 'usuarios/cuenta.html', context)

# -------------------------------------------------------------------------------------
def crear_publicacion_view(request):
    """
    Vista para crear publicaciones en el foro, manejando la subida de archivos.
    """
    if request.method == 'POST':
        try:
            # Placeholder: Obtener el primer comerciante disponible (simulación de usuario logueado)
            comerciante_simulado = Comerciante.objects.first() 
            if not comerciante_simulado:
                messages.error(request, 'Error: No hay usuarios registrados.')
                return redirect('registro') 
            
            # Pasar request.FILES para manejar la subida de archivos
            form = PostForm(request.POST, request.FILES) 
            
            if form.is_valid():
                nuevo_post = form.save(commit=False)
                nuevo_post.comerciante = comerciante_simulado 
                
                # --- Manejo de Archivos Subidos ---
                uploaded_file = form.cleaned_data.get('uploaded_file')
                
                if uploaded_file:
                    # Guardar el archivo en el sistema MEDIA_ROOT/posts/
                    file_name = default_storage.save(f'posts/{uploaded_file.name}', uploaded_file)
                    # Almacenar la URL pública del archivo en imagen_url
                    nuevo_post.imagen_url = default_storage.url(file_name) 
                
                # Si no se subió archivo, 'imagen_url' contendrá el link de 'url_link' (si se proporcionó)
                
                nuevo_post.save()
                messages.success(request, '¡Publicación creada con éxito! Se ha añadido al foro.')
                return redirect('plataforma_comerciante')
            else:
                # Si el formulario no es válido (ej: error de validación del formulario)
                # form.errors contiene los detalles del error
                messages.error(request, f'Error al publicar. Por favor, corrige los errores: {form.errors.as_text()}')
                return redirect('plataforma_comerciante') 
        
        except Exception as e:
            messages.error(request, f'Ocurrió un error al publicar: {e}')
            print(f"ERROR AL CREAR POST: {e}")
            
    return redirect('plataforma_comerciante')


# -------------------------------------------------------------------------------------
def plataforma_comerciante_view(request):
    """
    Vista principal de la plataforma, que maneja el filtro de selección múltiple.
    """
    
    # 1. Manejo del Filtro de Categoría (Usa getlist para múltiples valores)
    categoria_filtros = request.GET.getlist('categoria', [])
    
    if categoria_filtros and 'TODAS' not in categoria_filtros:
        # Filtra por CUALQUIERA de las categorías seleccionadas
        posts = Post.objects.filter(categoria__in=categoria_filtros)
    else:
        posts = Post.objects.all()
        # Si no hay filtros o está marcado 'TODAS', ajustamos la lista para marcar el checkbox
        if not categoria_filtros or 'TODAS' in categoria_filtros:
            categoria_filtros = ['TODAS']
        
    # 2. Obtener el formulario de publicación vacío para el modal
    post_form = PostForm()

    # 3. Datos de Contexto
    context = {
        'post_form': post_form,
        'posts': posts,
        'CATEGORIA_POST_CHOICES': CATEGORIA_POST_CHOICES, 
        'categoria_seleccionada': categoria_filtros, 
        'message': 'Bienvenido a la plataforma del comerciante.'
    }
    
    return render(request, 'usuarios/plataforma_comerciante.html', context)