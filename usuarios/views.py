# usuarios/views.py (CONTENIDO MODIFICADO)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password 
from django.core.files.storage import default_storage 
from django.utils import timezone
from django.db.models import Count, Q # Se mantienen para contar likes/comentarios en el feed
from django.db import IntegrityError 

# Importamos los modelos y las opciones
from .models import Comerciante, Post, Like, Comentario, INTERESTS_CHOICES 

# Importamos todos los formularios necesarios
from .forms import (
    RegistroComercianteForm,
    LoginForm,
    PostForm,
    ProfilePhotoForm,
    BusinessDataForm,
    ContactInfoForm,
    InterestsForm,
    ComentarioForm 
)

# --- SIMULACIÓN DE ESTADO DE SESIÓN GLOBAL ---
current_logged_in_user = None 

# Definición de Roles
ROLES = {
    'COMERCIANTE': 'Comerciante Verificado',
    'ADMIN': 'Administrador',
    'INVITADO': 'Invitado'
}

# --- VISTAS BÁSICAS DE AUTENTICACIÓN (Se mantienen) ---

def index(request):
    return redirect('registro') 

def registro_view(request):
    if request.method == 'POST':
        form = RegistroComercianteForm(request.POST)
        if form.is_valid():
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
    global current_logged_in_user
    
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
    global current_logged_in_user
    if current_logged_in_user:
        messages.info(request, f'Adiós, {current_logged_in_user.nombre_apellido}. Has cerrado sesión.')
        current_logged_in_user = None
    return redirect('login')


# --- VISTA PRINCIPAL DE LA PLATAFORMA (Actualizada para forzar el orden) ---

def plataforma_comerciante_view(request):
    global current_logged_in_user

    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a la plataforma.')
        return redirect('login') 
        
    # Obtener Posts con Conteo de Comentarios, Likes y si el usuario actual ya dio like
    posts_query = Post.objects.select_related('comerciante').annotate(
        comentarios_count=Count('comentarios', distinct=True), 
        likes_count=Count('likes', distinct=True),
        is_liked=Count('likes', filter=Q(likes__comerciante=current_logged_in_user)) 
    ).prefetch_related(
        'comentarios', 
        'comentarios__comerciante' 
    )
    
    categoria_filtros = request.GET.getlist('categoria', [])
    
    if categoria_filtros and 'TODAS' not in categoria_filtros:
        # Se filtra y se ORDENA explícitamente por el más nuevo
        posts = posts_query.filter(categoria__in=categoria_filtros).order_by('-fecha_publicacion')
    else:
        # Se obtiene todo y se ORDENA explícitamente por el más nuevo
        posts = posts_query.all().order_by('-fecha_publicacion')
        if not categoria_filtros or 'TODAS' in categoria_filtros:
            categoria_filtros = ['TODAS']
        
    context = {
        'comerciante': current_logged_in_user,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'), 
        'post_form': PostForm(),
        'posts': posts,
        'CATEGORIA_POST_CHOICES': Post._meta.get_field('categoria').choices, 
        'categoria_seleccionada': categoria_filtros, 
        'comentario_form': ComentarioForm(), 
        'message': f'Bienvenido a la plataforma, {current_logged_in_user.nombre_apellido.split()[0]}.',
    }
    
    return render(request, 'usuarios/plataforma_comerciante.html', context)


def publicar_post_view(request):
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
                
                uploaded_file = form.cleaned_data.get('uploaded_file')
                
                if uploaded_file:
                    file_name = default_storage.save(f'posts/{uploaded_file.name}', uploaded_file)
                    nuevo_post.imagen_url = default_storage.url(file_name) 
                
                nuevo_post.save()
                messages.success(request, '¡Publicación creada con éxito! Se ha añadido al foro.')
                return redirect('plataforma_comerciante')
            else:
                messages.error(request, f'Error al publicar. Por favor, corrige los errores: {form.errors.as_text()}')
                return redirect('plataforma_comerciante') 
        
        except Exception as e:
            messages.error(request, f'Ocurrió un error al publicar: {e}')
            
    return redirect('plataforma_comerciante')


# --- VISTA DE PERFIL (Se mantiene) ---

def perfil_view(request):
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a tu perfil.')
        return redirect('login') 
        
    comerciante = current_logged_in_user 

    if request.method == 'POST':
        action = request.POST.get('action') 
        
        if action == 'edit_photo':
            photo_form = ProfilePhotoForm(request.POST, request.FILES, instance=comerciante)
            if photo_form.is_valid():
                photo_form.save()
                messages.success(request, '¡Foto de perfil actualizada con éxito!')
                return redirect('perfil')
            else:
                messages.error(request, 'Error al subir la foto. Asegúrate de que sea un archivo válido.')

        elif action == 'edit_contact':
            contact_form = ContactInfoForm(request.POST, instance=comerciante) 
            if contact_form.is_valid():
                nuevo_email = contact_form.cleaned_data.get('email')
                
                if nuevo_email != comerciante.email and Comerciante.objects.filter(email=nuevo_email).exists():
                    messages.error(request, 'Este correo ya está registrado por otro usuario.')
                else:
                    contact_form.save()
                    messages.success(request, 'Datos de contacto actualizados con éxito.')
                    current_logged_in_user.email = nuevo_email 
                    current_logged_in_user.whatsapp = contact_form.cleaned_data.get('whatsapp')
                    return redirect('perfil')
            else:
                error_msgs = [f"{field.label}: {', '.join(error for error in field.errors)}" for field in contact_form if field.errors]
                messages.error(request, f'Error en los datos de contacto. {"; ".join(error_msgs)}')

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
        
        'photo_form': photo_form,
        'contact_form': contact_form,
        'business_form': business_form,
        'interests_form': interests_form,
        
        'intereses_actuales_codigos': [c for c in intereses_actuales_codigos if c],
        'intereses_choices_dict': intereses_choices_dict,
    }
    
    return render(request, 'usuarios/perfil.html', context)


# --- VISTAS DE DETALLE DE POST Y ACCIONES (Modificadas para foro principal) ---

def post_detail_view(request, post_id):
    """Muestra un post individual y su lista de comentarios (mantenida por si se usa, pero no es el destino principal)."""
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Debes iniciar sesión para ver los detalles.')
        return redirect('login') 
        
    # Obtener post con conteos de likes y si el usuario actual ya dio like
    post = get_object_or_404(Post.objects.select_related('comerciante').annotate(
        comentarios_count=Count('comentarios', distinct=True),
        likes_count=Count('likes', distinct=True),
        is_liked=Count('likes', filter=Q(likes__comerciante=current_logged_in_user))
    ), pk=post_id)
        
    # Obtener comentarios y seleccionar el comerciante autor para optimización
    comentarios = post.comentarios.select_related('comerciante').all().order_by('fecha_creacion')
    
    context = {
        'comerciante': current_logged_in_user,
        'post': post,
        'comentarios': comentarios,
        'comentario_form': ComentarioForm(),
    }
    
    return render(request, 'usuarios/post_detail.html', context)


def add_comment_view(request, post_id):
    """Maneja la lógica para añadir un comentario y redirige al foro principal."""
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.error(request, 'No autorizado para comentar. Inicia sesión.')
        return redirect('login')
        
    post = get_object_or_404(Post, pk=post_id)

    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            nuevo_comentario = form.save(commit=False)
            nuevo_comentario.post = post
            nuevo_comentario.comerciante = current_logged_in_user
            nuevo_comentario.save()
            messages.success(request, '¡Comentario publicado con éxito!')
            # REDIRECCIÓN: Va a la plataforma principal
            return redirect('plataforma_comerciante') 
        else:
            messages.error(request, 'Error al publicar el comentario. Asegúrate de que el contenido no esté vacío.')
            # REDIRECCIÓN: Va a la plataforma principal
            return redirect('plataforma_comerciante') 
            
    # REDIRECCIÓN: Va a la plataforma principal
    return redirect('plataforma_comerciante')


def like_post_view(request, post_id):
    """Maneja la adición/eliminación de likes y redirige al foro principal."""
    global current_logged_in_user

    if not current_logged_in_user:
        messages.error(request, 'Debes iniciar sesión para dar like.')
        return redirect('login')

    post = get_object_or_404(Post, pk=post_id)

    if request.method == 'POST':
        # Intenta obtener el Like. Si no existe, lo crea.
        like, created = Like.objects.get_or_create(
            post=post,
            comerciante=current_logged_in_user
        )
        
        if not created:
            # Si ya existía, lo elimina (dislike)
            like.delete()
            messages.success(request, 'Dislike registrado.')
        else:
            # Si se creó, es un nuevo like
            messages.success(request, '¡Like registrado!')

    # REDIRECCIÓN: Va a la plataforma principal
    return redirect('plataforma_comerciante')