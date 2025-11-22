# usuarios/views.py (CONTENIDO COMPLETO MODIFICADO)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password 
from django.core.files.storage import default_storage 
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.db.models import Count, Q 
from django.db import IntegrityError 
from datetime import timedelta 
from django.contrib.auth.decorators import login_required 

# Importamos los modelos y las opciones
from .models import (
    Comerciante, Post, Like, Comentario, INTERESTS_CHOICES, Beneficio,
    NIVELES, CATEGORIAS 
) 

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

# --- FUNCIÓN DE CÁLCULO DE NIVEL (LÓGICA SOLICITADA) ---
def calcular_nivel_y_progreso(puntos):
    NIVELES_VALORES = [nivel[0] for nivel in NIVELES] # BRONCE, PLATA, ORO, PLATINO, DIAMANTE
    UMBRAL_PUNTOS = 100 
    MAX_NIVEL_INDEX = len(NIVELES_VALORES) - 1 # Índice de Diamante (4)
    
    # 1. Determinar el índice del nivel actual
    # 0-99 = BRONCE (Index 0), 100-199 = PLATA (Index 1), etc.
    nivel_index = min(MAX_NIVEL_INDEX, puntos // UMBRAL_PUNTOS)
    
    # 2. Asignar el nivel actual
    nivel_actual_codigo = NIVELES_VALORES[nivel_index]
    
    # 3. Calcular umbrales para progreso
    current_threshold = nivel_index * UMBRAL_PUNTOS
    
    if nivel_actual_codigo == 'DIAMANTE':
        # Nivel Diamante: progreso siempre 100%, meta es el punto actual (no hay tope)
        progreso_porcentaje = 100
        puntos_restantes = 0
        puntos_siguiente_nivel = puntos 
        proximo_nivel_display = 'Máximo'
    else:
        next_threshold = (nivel_index + 1) * UMBRAL_PUNTOS
        puntos_en_nivel = puntos - current_threshold
        puntos_a_avanzar = UMBRAL_PUNTOS # Siempre 100 puntos para el siguiente nivel
        
        puntos_restantes = next_threshold - puntos
        progreso_porcentaje = int((puntos_en_nivel / puntos_a_avanzar) * 100)
        puntos_siguiente_nivel = next_threshold
        proximo_nivel_display = NIVELES_VALORES[nivel_index + 1]

    return {
        'nivel_codigo': nivel_actual_codigo,
        'puntos_restantes': puntos_restantes,
        'puntos_siguiente_nivel': puntos_siguiente_nivel,
        'progreso_porcentaje': progreso_porcentaje,
        'proximo_nivel': proximo_nivel_display,
    }


# --- VISTAS BÁSICAS DE AUTENTICACIÓN ---

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
            
            # Inicializar Puntos y Nivel al registrar (BRONCE con 0 puntos)
            nuevo_comerciante.puntos = 0
            nuevo_comerciante.nivel_actual = 'BRONCE'
            
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


# views.py
def login_view(request):
    global current_logged_in_user
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # 🚀 PASO CRÍTICO: Usar authenticate() que llama al ComercianteBackend
            comerciante = authenticate(request, username=email, password=password) 

            if comerciante is not None:
                # 1. Iniciar Sesión de Django (sin last_login porque el backend lo maneja)
                login(request, comerciante) 
                
                # 2. Tu lógica de negocio (mantén esto)
                progreso = calcular_nivel_y_progreso(comerciante.puntos)
                comerciante.nivel_actual = progreso['nivel_codigo']
                comerciante.ultima_conexion = timezone.now() # Tu campo de conexión
                comerciante.save(update_fields=['ultima_conexion', 'nivel_actual'])
                current_logged_in_user = comerciante
                
                messages.success(request, f'¡Bienvenido {comerciante.nombre_apellido}!')
                
                # 3. Redirección
                next_url = request.GET.get('next') 
                return redirect(next_url if next_url else 'plataforma_comerciante')
            else:
                # El backend devolvió None (credenciales incorrectas)
                messages.error(request, 'Correo o contraseña incorrectos. Intenta nuevamente.')
        else:
            messages.error(request, 'Por favor, completa todos los campos correctamente.')
    else:
        form = LoginForm()
        current_logged_in_user = None 

    context = {'form': form}
    return render(request, 'usuarios/cuenta.html', context)


def logout_view(request):
    global current_logged_in_user
    if current_logged_in_user:
        messages.info(request, f'Adiós, {current_logged_in_user.nombre_apellido}. Has cerrado sesión.')
        current_logged_in_user = None
    return redirect('login')


# --- VISTA PRINCIPAL DE LA PLATAFORMA (Foro) ---

def plataforma_comerciante_view(request):
    global current_logged_in_user

    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a la plataforma.')
        return redirect('login') 
        
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
        posts = posts_query.filter(categoria__in=categoria_filtros).order_by('-fecha_publicacion')
    else:
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


# --- VISTA DE PERFIL (Actualizada para mostrar PUNTOS) ---

def perfil_view(request):
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a tu perfil.')
        return redirect('login') 
        
    comerciante = current_logged_in_user 
    progreso = calcular_nivel_y_progreso(comerciante.puntos) # Calcular progreso
    
    # Asegurar que el nivel del modelo esté actualizado
    if comerciante.nivel_actual != progreso['nivel_codigo']:
        comerciante.nivel_actual = progreso['nivel_codigo']
        comerciante.save(update_fields=['nivel_actual'])
    
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
        
        # --- CONTEXTO DE PUNTOS Y NIVEL ---
        'puntos_actuales': comerciante.puntos,
        'nivel_actual': dict(NIVELES).get(comerciante.nivel_actual, 'Desconocido'),
        'puntos_restantes': progreso['puntos_restantes'],
        'progreso_porcentaje': progreso['progreso_porcentaje'],
        # ----------------------------------
        
        'photo_form': photo_form,
        'contact_form': contact_form,
        'business_form': business_form,
        'interests_form': interests_form,
        
        'intereses_actuales_codigos': [c for c in intereses_actuales_codigos if c],
        'intereses_choices_dict': intereses_choices_dict,
    }
    
    return render(request, 'usuarios/perfil.html', context)


# --- VISTA DE BENEFICIOS ---

def beneficios_view(request):
    global current_logged_in_user

    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a los beneficios.')
        return redirect('login') 
        
    comerciante = current_logged_in_user
    
    # 1. Calcular el nivel y progreso basado en los puntos del modelo
    progreso = calcular_nivel_y_progreso(comerciante.puntos)
    
    # 2. Obtener parámetros de la URL para filtrar y ordenar
    category_filter = request.GET.get('category', 'TODOS')
    sort_by = request.GET.get('sort_by', '-fecha_creacion') 
    
    # 3. Obtener beneficios y aplicar filtros
    beneficios_queryset = Beneficio.objects.all()
    
    if category_filter and category_filter != 'TODOS':
        beneficios_queryset = beneficios_queryset.filter(categoria=category_filter)
        
    valid_sort_fields = ['vence', '-vence', 'puntos_requeridos', '-puntos_requeridos', '-fecha_creacion']
    if sort_by in valid_sort_fields:
        beneficios_queryset = beneficios_queryset.order_by(sort_by)
    else:
        sort_by = '-fecha_creacion'
        beneficios_queryset = beneficios_queryset.order_by(sort_by)

    # 4. Checkear si hay beneficios (para el mensaje "No hay beneficios")
    no_beneficios_disponibles = not beneficios_queryset.exists()
    
    context = {
        'comerciante': comerciante,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'), 
        
        # CONTEXTO DE PUNTOS CALCULADO
        'puntos_actuales': comerciante.puntos,
        'nivel_actual': dict(NIVELES).get(progreso['nivel_codigo'], 'Bronce'),
        'puntos_restantes': progreso['puntos_restantes'],
        'puntos_siguiente_nivel': progreso['puntos_siguiente_nivel'],
        'progreso_porcentaje': progreso['progreso_porcentaje'],
        'proximo_nivel': progreso['proximo_nivel'],
        
        # CONTEXTO DE BENEFICIOS
        'beneficios': beneficios_queryset,
        'no_beneficios_disponibles': no_beneficios_disponibles,
        'CATEGORIAS': CATEGORIAS, 
        'current_category': category_filter, 
        'current_sort': sort_by, 
    }
    
    return render(request, 'usuarios/beneficios.html', context)


# --- VISTAS DE DETALLE DE POST Y ACCIONES ---

def post_detail_view(request, post_id):
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Debes iniciar sesión para ver los detalles.')
        return redirect('login') 
        
    post = get_object_or_404(Post.objects.select_related('comerciante').annotate(
        comentarios_count=Count('comentarios', distinct=True),
        likes_count=Count('likes', distinct=True),
        is_liked=Count('likes', filter=Q(likes__comerciante=current_logged_in_user))
    ), pk=post_id)
        
    comentarios = post.comentarios.select_related('comerciante').all().order_by('fecha_creacion')
    
    context = {
        'comerciante': current_logged_in_user,
        'post': post,
        'comentarios': comentarios,
        'comentario_form': ComentarioForm(),
    }
    
    return render(request, 'usuarios/post_detail.html', context)


def add_comment_view(request, post_id):
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
            return redirect('plataforma_comerciante') 
        else:
            messages.error(request, 'Error al publicar el comentario. Asegúrate de que el contenido no esté vacío.')
            return redirect('plataforma_comerciante') 
            
    return redirect('plataforma_comerciante')


def like_post_view(request, post_id):
    global current_logged_in_user

    if not current_logged_in_user:
        messages.error(request, 'Debes iniciar sesión para dar like.')
        return redirect('login')

    post = get_object_or_404(Post, pk=post_id)

    if request.method == 'POST':
        like, created = Like.objects.get_or_create(
            post=post,
            comerciante=current_logged_in_user
        )
        
        if not created:
            like.delete()
            messages.success(request, 'Dislike registrado.')
        else:
            messages.success(request, '¡Like registrado!')

    return redirect('plataforma_comerciante')