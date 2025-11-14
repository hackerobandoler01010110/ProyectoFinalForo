from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError # Necesario para manejar duplicados

# Importamos los modelos y las opciones
from .models import Comerciante, Post, INTERESTS_CHOICES
from django.contrib.auth.hashers import make_password, check_password # Usaremos estos para simular el hasheo
from django.core.files.storage import default_storage 
from django.utils import timezone

# Importamos todos los formularios necesarios
from .forms import (
    RegistroComercianteForm,
    LoginForm,
    PostForm,
    ProfilePhotoForm,
    BusinessDataForm,
    ContactInfoForm,
    InterestsForm
)

# --- SIMULACIÓN DE ESTADO DE SESIÓN GLOBAL ---
current_logged_in_user = None 

# Definición de Roles
ROLES = {
    'COMERCIANTE': 'Comerciante Verificado',
    'ADMIN': 'Administrador',
    'INVITADO': 'Invitado'
}

# --- VISTAS BÁSICAS DE AUTENTICACIÓN ---

def index(request):
    """Vista de inicio o landing page."""
    return redirect('registro') # Redirigir a registro/login

def registro_view(request):
    """Vista para el registro de nuevos comerciantes."""
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
            
            except Exception as e:
                messages.error(request, f'Ocurrió un error inesperado al guardar: {e}')
                
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
            
    else:
        form = RegistroComercianteForm()
    
    context = {
        'form': form
    }
    return render(request, 'usuarios/cuenta.html', context)


def login_view(request):
    """Vista para el inicio de sesión."""
    global current_logged_in_user
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                comerciante = Comerciante.objects.get(email=email)

                # Usamos check_password para verificar el hash
                if check_password(password, comerciante.password_hash):
                    comerciante.ultima_conexion = timezone.now()
                    comerciante.save(update_fields=['ultima_conexion'])
                    
                    # SIMULACIÓN DE SESIÓN: Almacenamos el objeto globalmente.
                    current_logged_in_user = comerciante
                    
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
        current_logged_in_user = None 

    context = {
        'form': form
    }
    return render(request, 'usuarios/cuenta.html', context)


def logout_view(request):
    """Vista para cerrar la sesión."""
    global current_logged_in_user
    if current_logged_in_user:
        messages.info(request, f'Adiós, {current_logged_in_user.nombre_apellido}. Has cerrado sesión.')
        current_logged_in_user = None
    return redirect('login')


# --- VISTA PRINCIPAL DE LA PLATAFORMA ---

def plataforma_comerciante_view(request):
    """Vista principal de la plataforma para comerciantes."""
    global current_logged_in_user

    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a la plataforma.')
        return redirect('login') 
        
    # 1. Manejo del Filtro de Categoría (Usa getlist para múltiples valores)
    categoria_filtros = request.GET.getlist('categoria', [])
    
    if categoria_filtros and 'TODAS' not in categoria_filtros:
        posts = Post.objects.filter(categoria__in=categoria_filtros)
    else:
        posts = Post.objects.all()
        if not categoria_filtros or 'TODAS' in categoria_filtros:
            categoria_filtros = ['TODAS']
        
    # 2. Obtener el formulario de publicación vacío para el modal
    post_form = PostForm()

    # 3. Datos de Contexto
    context = {
        'comerciante': current_logged_in_user,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'), 
        'post_form': post_form,
        'posts': posts,
        # Importar de models.py si se requiere una lista
        'CATEGORIA_POST_CHOICES': Post._meta.get_field('categoria').choices, 
        'categoria_seleccionada': categoria_filtros, 
        'message': f'Bienvenido a la plataforma, {current_logged_in_user.nombre_apellido.split()[0]}.'
    }
    
    return render(request, 'usuarios/plataforma_comerciante.html', context)


def publicar_post_view(request):
    """Vista para publicar un nuevo post, manejando la subida de archivos."""
    global current_logged_in_user
    
    if request.method == 'POST':
        if not current_logged_in_user:
            messages.error(request, 'Debes iniciar sesión para publicar.')
            return redirect('login') 
            
        try:
            form = PostForm(request.POST, request.FILES) 
            
            if form.is_valid():
                nuevo_post = form.save(commit=False)
                nuevo_post.comerciante = current_logged_in_user
                
                # --- Manejo de Archivos Subidos ---
                uploaded_file = form.cleaned_data.get('uploaded_file')
                
                if uploaded_file:
                    file_name = default_storage.save(f'posts/{uploaded_file.name}', uploaded_file)
                    nuevo_post.imagen_url = default_storage.url(file_name) 
                
                # La URL externa ya fue manejada en form.clean()
                
                nuevo_post.save()
                messages.success(request, '¡Publicación creada con éxito! Se ha añadido al foro.')
                return redirect('plataforma_comerciante')
            else:
                messages.error(request, f'Error al publicar. Por favor, corrige los errores: {form.errors.as_text()}')
                return redirect('plataforma_comerciante') 
        
        except Exception as e:
            messages.error(request, f'Ocurrió un error al publicar: {e}')
            
    return redirect('plataforma_comerciante')


# --- VISTA DE PERFIL (ACTUALIZADA Y FUNCIONAL) ---

def perfil_view(request):
    """
    Vista para mostrar la información detallada del perfil y manejar todas las ediciones
    mediante diferentes formularios (usando 'action' para distinguir el POST).
    """
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a tu perfil.')
        return redirect('login') 
        
    comerciante = current_logged_in_user 

    if request.method == 'POST':
        action = request.POST.get('action') 
        
        # --- 1. Edición de Foto de Perfil (Requiere request.FILES) ---
        if action == 'edit_photo':
            photo_form = ProfilePhotoForm(request.POST, request.FILES, instance=comerciante)
            if photo_form.is_valid():
                photo_form.save()
                messages.success(request, '¡Foto de perfil actualizada con éxito!')
                return redirect('perfil')
            else:
                messages.error(request, 'Error al subir la foto. Asegúrate de que sea un archivo válido.')

        # --- 2. Edición de Datos de Contacto (Email, WhatsApp) ---
        elif action == 'edit_contact':
            contact_form = ContactInfoForm(request.POST, instance=comerciante) 
            if contact_form.is_valid():
                nuevo_email = contact_form.cleaned_data.get('email')
                
                if nuevo_email != comerciante.email and Comerciante.objects.filter(email=nuevo_email).exists():
                    messages.error(request, 'Este correo ya está registrado por otro usuario.')
                else:
                    contact_form.save()
                    messages.success(request, 'Datos de contacto actualizados con éxito.')
                    # Actualizamos el objeto global simulado
                    current_logged_in_user.email = nuevo_email 
                    current_logged_in_user.whatsapp = contact_form.cleaned_data.get('whatsapp')
                    return redirect('perfil')
            else:
                error_msgs = [f"{field.label}: {', '.join(error for error in field.errors)}" for field in contact_form if field.errors]
                messages.error(request, f'Error en los datos de contacto. {"; ".join(error_msgs)}')

        # --- 3. Edición de Datos de Negocio ---
        elif action == 'edit_business':
            business_form = BusinessDataForm(request.POST, instance=comerciante)
            if business_form.is_valid():
                business_form.save()
                messages.success(request, 'Datos del negocio actualizados con éxito.')
                current_logged_in_user.nombre_negocio = business_form.cleaned_data.get('nombre_negocio')
                return redirect('perfil')
            else:
                error_msgs = [f"{field.label}: {', '.join(error for error in field.errors)}" for field in business_form if field.errors]
                messages.error(request, f'Error en los datos del negocio. {"; ".join(error_msgs)}')

        # --- 4. Edición de Intereses ---
        elif action == 'edit_interests':
            interests_form = InterestsForm(request.POST)
            if interests_form.is_valid():
                intereses_seleccionados = interests_form.cleaned_data['intereses']
                intereses_csv = ','.join(intereses_seleccionados)
                
                comerciante.intereses = intereses_csv
                comerciante.save(update_fields=['intereses']) 
                
                messages.success(request, 'Intereses actualizados con éxito.')
                return redirect('perfil')
            else:
                messages.error(request, 'Error al actualizar los intereses.')

    # --- Manejo de GET o POST fallido ---
    
    photo_form = ProfilePhotoForm()
    contact_form = ContactInfoForm(instance=comerciante) 
    business_form = BusinessDataForm(instance=comerciante) 

    intereses_actuales_codigos = comerciante.intereses.split(',') if comerciante.intereses else []
    interests_form = InterestsForm(initial={'intereses': [c for c in intereses_actuales_codigos if c]})

    intereses_choices_dict = dict(INTERESTS_CHOICES)

    context = {
        'comerciante': comerciante,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'),
        'nombre_negocio_display': comerciante.nombre_negocio,
        
        # Forms
        'photo_form': photo_form,
        'contact_form': contact_form,
        'business_form': business_form,
        'interests_form': interests_form,
        
        # Intereses para mostrar en la vista
        'intereses_actuales_codigos': [c for c in intereses_actuales_codigos if c],
        'intereses_choices_dict': intereses_choices_dict,
    }
    
    return render(request, 'usuarios/perfil.html', context)