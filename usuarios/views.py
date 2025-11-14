# usuarios/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError 
from django.contrib.auth.hashers import make_password, check_password
from django.core.files.storage import default_storage 
from django.utils import timezone
from .models import Comerciante, Post, CATEGORIA_POST_CHOICES 
from .forms import RegistroComercianteForm, LoginForm, PostForm 

# Diccionario de Roles Global para usar en las vistas
ROLES = {
    'SUPER_ADMIN': 'Dueño de la plataforma',
    'ADMIN_PAIS': 'Administrador por país',
    'ADMIN_AGRUPACION': 'Administrador por agrupación',
    'ADMIN_TECNICO': 'Administrador técnico',
    'COMERCIANTE': 'Comerciante',
    'PROVEEDOR': 'Proveedor',
}

# --- Vistas de Autenticación y Registro (se mantienen) ---

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
                # Simulación de asignación de rol por defecto (Comerciante)
                # En la DB el modelo Comerciante NO tiene campo 'rol', lo simulamos por ahora.
                # Para fines de la plataforma, asumiremos que un Comerciante registrado tiene este rol.
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


# Nota: Usamos una variable global para simular el usuario logueado en la plataforma.
# En un proyecto real, esto usaría el sistema de autenticación de Django.
current_logged_in_user = None

def login_view(request):
    """
    Vista para manejar el inicio de sesión de comerciantes registrados.
    """
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
        # Si la vista se carga por GET, limpiamos la simulación de sesión.
        current_logged_in_user = None 

    context = {
        'form': form
    }
    return render(request, 'usuarios/cuenta.html', context)

# --- Vistas de Plataforma y Foro (se mantienen, pero con ajuste de usuario) ---

def crear_publicacion_view(request):
    """
    Vista para crear publicaciones en el foro, manejando la subida de archivos.
    """
    global current_logged_in_user
    
    if request.method == 'POST':
        # Aseguramos que haya un usuario "logueado" (simulado)
        if not current_logged_in_user:
            messages.error(request, 'Debes iniciar sesión para publicar.')
            return redirect('login') 
            
        try:
            form = PostForm(request.POST, request.FILES) 
            
            if form.is_valid():
                nuevo_post = form.save(commit=False)
                nuevo_post.comerciante = current_logged_in_user # Usar el usuario simulado
                
                # --- Manejo de Archivos Subidos ---
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
            print(f"ERROR AL CREAR POST: {e}")
            
    return redirect('plataforma_comerciante')


def plataforma_comerciante_view(request):
    """
    Vista principal de la plataforma, que maneja el filtro de selección múltiple.
    """
    global current_logged_in_user

    # Verificación de "sesión" simulada
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
    # NOTA: Simulamos que el Comerciante siempre tiene el rol 'COMERCIANTE'
    # En un proyecto real, esto vendría de un campo del modelo de usuario.
    context = {
        'comerciante': current_logged_in_user,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'), # Simulamos el rol
        'post_form': post_form,
        'posts': posts,
        'CATEGORIA_POST_CHOICES': CATEGORIA_POST_CHOICES, 
        'categoria_seleccionada': categoria_filtros, 
        'message': f'Bienvenido a la plataforma, {current_logged_in_user.nombre_apellido.split()[0]}.'
    }
    
    return render(request, 'usuarios/plataforma_comerciante.html', context)


# --- NUEVA VISTA DE PERFIL ---

def perfil_view(request):
    """
    Vista para mostrar la información detallada del perfil del comerciante.
    """
    global current_logged_in_user
    
    if not current_logged_in_user:
        messages.warning(request, 'Por favor, inicia sesión para acceder a tu perfil.')
        return redirect('login') 

    # Datos simulados para el perfil, ya que no están en el modelo Comerciante:
    simulacion_intereses = [
        'Marketing Digital', 'Gestión de Inventario', 'Proveedores Locales', 
        'Finanzas', 'Atención al Cliente'
    ]
    
    context = {
        'comerciante': current_logged_in_user,
        'rol_usuario': ROLES.get('COMERCIANTE', 'Usuario'),
        'intereses': simulacion_intereses,
    }
    
    return render(request, 'usuarios/perfil.html', context)