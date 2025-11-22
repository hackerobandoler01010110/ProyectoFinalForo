from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    Proveedor, 
    SolicitudContacto, 
    ProductoServicio, 
    Promocion,
    CategoriaProveedor,
    Pais,   
    Region,
    Comuna
)
from .forms import (
    ProveedorForm, 
    ProductoServicioForm, 
    PromocionForm,
    SolicitudContactoForm,
    ConfiguracionForm
)




# ==================== VISTAS PÚBLICAS ====================

def directorio_proveedores(request):
    """
    Vista del directorio público de proveedores con filtros
    """
    proveedores = Proveedor.objects.filter(activo=True).select_related(
        'pais', 'region', 'comuna'
    ).prefetch_related('categorias')
    
    # Filtros
    categoria_id = request.GET.get('categoria')
    region_id = request.GET.get('region')
    comuna_id = request.GET.get('comuna')
    cobertura = request.GET.get('cobertura')
    busqueda = request.GET.get('q')
    
    if categoria_id:
        proveedores = proveedores.filter(categorias__id=categoria_id)
    
    if region_id:
        proveedores = proveedores.filter(region_id=region_id)
    
    if comuna_id:
        proveedores = proveedores.filter(comuna_id=comuna_id)
    
    if cobertura:
        proveedores = proveedores.filter(cobertura=cobertura)
    
    if busqueda:
        proveedores = proveedores.filter(
            Q(nombre_empresa__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    
    # Ordenar: destacados primero, luego por fecha
    proveedores = proveedores.order_by('-destacado', '-fecha_registro')
    
    # Paginación
    paginator = Paginator(proveedores, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    categorias = CategoriaProveedor.objects.filter(activo=True)
    regiones = Region.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'regiones': regiones,
        'categoria_seleccionada': categoria_id,
        'region_seleccionada': region_id,
        'comuna_seleccionada': comuna_id,
        'cobertura_seleccionada': cobertura,
        'busqueda': busqueda,
    }
    
    return render(request, 'proveedores/directorio.html', context)


def detalle_proveedor(request, proveedor_id):
    """
    Vista del perfil público del proveedor
    """
    proveedor = get_object_or_404(
        Proveedor.objects.select_related('pais', 'region', 'comuna').prefetch_related('categorias'),
        id=proveedor_id,
        activo=True
    )
    
    # Incrementar visitas
    proveedor.incrementar_visitas()
    
    # Productos y servicios del proveedor
    productos = ProductoServicio.objects.filter(
        proveedor=proveedor, 
        activo=True
    ).order_by('-destacado', '-fecha_creacion')
    
    # Promociones vigentes
    hoy = timezone.now().date()
    promociones = Promocion.objects.filter(
        proveedor=proveedor,
        activo=True,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy
    ).order_by('-fecha_inicio')
    
    context = {
        'proveedor': proveedor,
        'productos': productos,
        'promociones': promociones,
    }
    
    return render(request, 'proveedores/detalle.html', context)


# ==================== VISTAS DEL PERFIL DEL PROVEEDOR ====================


@login_required
def perfil_proveedor(request):
    """
    Vista del panel de control del proveedor.
    Redirige a la creación de perfil si el objeto Proveedor no existe.
    """
    
    # request.user es ahora el objeto Comerciante autenticado
    comerciante = request.user 
    
    try:
        # Intenta acceder al perfil de Proveedor. 
        # Esto funciona porque en models.py se definió related_name='proveedor'
        proveedor = comerciante.proveedor
        
    except Proveedor.DoesNotExist:
        # Si el usuario NO tiene un perfil de proveedor creado, lo redirigimos a crearlo.
        messages.warning(request, 'Aún no tienes un perfil de proveedor. Por favor, créalo para acceder al panel.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    # ----------------------------------------------------
    # LÓGICA DE ESTADÍSTICAS (Solo si el perfil existe)
    # ----------------------------------------------------
    
    # Total de productos y servicios
    total_productos = ProductoServicio.objects.filter(proveedor=proveedor).count()
    
    # Promociones activas (usando el proveedor encontrado)
    hoy = timezone.now().date()
    promociones_activas = Promocion.objects.filter(
        proveedor=proveedor,
        activo=True,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy
    ).count()
    
    # Solicitudes de contacto pendientes
    solicitudes_pendientes = SolicitudContacto.objects.filter(
        proveedor=proveedor,
        estado='pendiente'
    ).count()
    
    context = {
        'proveedor': proveedor,
        'total_productos': total_productos,
        'promociones_activas': promociones_activas,
        'solicitudes_pendientes': solicitudes_pendientes,
    }
    
    return render(request, 'proveedores/perfil.html', context)


@login_required
def crear_perfil_proveedor(request):
    """
    Vista para crear el perfil de proveedor
    """
    # Verificar si ya tiene perfil
    if hasattr(request.user, 'proveedor'):
        messages.info(request, 'Ya tienes un perfil de proveedor.')
        return redirect('proveedores:perfil_proveedor')
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.usuario = request.user
            proveedor.email = request.user.email
            proveedor.save()
            form.save_m2m()  # Para guardar las relaciones ManyToMany (categorías)
            
            messages.success(request, '¡Perfil de proveedor creado exitosamente!')
            return redirect('proveedores:perfil_proveedor')
    else:
        form = ProveedorForm()
    
    context = {'form': form}
    return render(request, 'proveedores/crear_perfil.html', context)


@login_required
def editar_perfil_proveedor(request):
    """
    Vista para editar el perfil del proveedor
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('proveedores:perfil_proveedor')
    else:
        form = ProveedorForm(instance=proveedor)
    
    context = {'form': form, 'proveedor': proveedor}
    return render(request, 'proveedores/editar_perfil.html', context)


# ==================== GESTIÓN DE PRODUCTOS/SERVICIOS ====================


@login_required
def lista_productos(request):
    """
    Lista de productos del proveedor con filtros funcionales
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    # 1. INICIAR LA CONSULTA BASE: Obtener TODOS los productos del proveedor
    # ESTO ES CRUCIAL: No aplicar ningún filtro de 'activo' aquí.
    productos = ProductoServicio.objects.filter(proveedor=proveedor)
    
    # Obtener CHOICES para el template (solo para referencia, no afecta la consulta)
    categoria_choices = ProductoServicio.CATEGORIA_CHOICES 
    
    # 2. ✅ FILTRO POR CATEGORÍA
    # El valor del GET puede ser 'comida', 'bebida', o vacío si seleccionó "Todas las categorías"
    categoria_actual = request.GET.get('categoria', '')
    if categoria_actual:
        productos = productos.filter(categoria=categoria_actual)
    
    # 3. ✅ FILTRO POR ESTADO (activo/inactivo)
    # El valor del GET debe ser 'activo', 'inactivo', o 'todos' (si es tu opción por defecto)
    estado_actual = request.GET.get('estado', '') # 'todos' o vacío si no se selecciona
    if estado_actual == 'activo':
        productos = productos.filter(activo=True)
    elif estado_actual == 'inactivo':
        productos = productos.filter(activo=False)
    # Si estado_actual es 'todos' o está vacío, no se aplica ningún filtro de activo/inactivo, mostrando ambos.
    
    # 4. ✅ FILTRO POR BÚSQUEDA
    buscar_actual = request.GET.get('buscar', '')
    if buscar_actual:
        from django.db.models import Q
        productos = productos.filter(
            Q(nombre__icontains=buscar_actual) | 
            Q(descripcion__icontains=buscar_actual)
        )
    
    # 5. Ordenar por más reciente
    productos = productos.order_by('-id')
    
    # 6. Preparar el contexto
    context = {
        'proveedor': proveedor,
        'productos': productos,
        'categoria_actual': categoria_actual, # Usar el nombre limpio
        'estado_actual': estado_actual, # Usar el nombre limpio
        'buscar_actual': buscar_actual, # Usar el nombre limpio
        'opciones_categoria': categoria_choices, # Renombrado para coincidir con la sugerencia anterior
    }
    
    return render(request, 'proveedores/productos/lista.html', context)

@login_required
def crear_producto(request):
    """
    Crear nuevo producto/servicio
    """
    # Verificar que el usuario tenga un perfil de proveedor
    if not hasattr(request.user, 'proveedor'):
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    proveedor = request.user.proveedor
    
    if request.method == 'POST':
        form = ProductoServicioForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.proveedor = proveedor
            producto.save()
            messages.success(request, '✅ Producto/servicio creado exitosamente.')
            return redirect('proveedores:lista_productos')
    else:
        form = ProductoServicioForm()
    
    context = {
        'form': form,
        'proveedor': proveedor
    }
    return render(request, 'proveedores/productos/crear.html', context)

@login_required
def editar_producto(request, producto_id):
    proveedor = get_object_or_404(Proveedor, usuario=request.user)  # ✅
    producto = get_object_or_404(
        ProductoServicio, 
        id=producto_id, 
        proveedor=proveedor
    )
    
    if request.method == 'POST':
        form = ProductoServicioForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto/servicio actualizado exitosamente.')
            return redirect('proveedores:lista_productos')
    else:
        form = ProductoServicioForm(instance=producto)
    
    context = {'form': form, 'producto': producto}
    return render(request, 'proveedores/productos/editar.html', context)


@login_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(
        ProductoServicio, 
        id=producto_id, 
        proveedor__usuario=request.user
    )
    
    if request.method == 'POST':
        nombre_producto = producto.nombre  # Guardar el nombre antes de eliminar
        producto.delete()  # 👈 ELIMINAR PERMANENTEMENTE
        messages.success(request, f'✅ Producto "{nombre_producto}" eliminado permanentemente.')
        return redirect('proveedores:lista_productos')
    
    context = {'producto': producto}
    return render(request, 'proveedores/productos/eliminar.html', context)

# ==================== GESTIÓN DE PROMOCIONES ====================


@login_required
def lista_promociones(request):
    """
    Lista de promociones del proveedor con filtros funcionales
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    # Obtener TODAS las promociones del proveedor
    promociones = Promocion.objects.filter(proveedor=proveedor)
    
    # ✅ FILTRO POR ESTADO
    estado = request.GET.get('estado', '')
    if estado == 'activas':
        promociones = promociones.filter(activo=True)
    elif estado == 'inactivas':
        promociones = promociones.filter(activo=False)
    # Si estado está vacío, muestra todas
    
    # ✅ FILTRO POR VIGENCIA
    vigencia = request.GET.get('vigencia', '')
    hoy = timezone.now().date()
    
    if vigencia == 'vigentes':
        promociones = promociones.filter(
            activo=True,
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
    elif vigencia == 'programadas':
        promociones = promociones.filter(
            activo=True,
            fecha_inicio__gt=hoy
        )
    elif vigencia == 'vencidas':
        promociones = promociones.filter(fecha_fin__lt=hoy)
    
    # ✅ FILTRO POR BÚSQUEDA (título y descripción)
    buscar = request.GET.get('buscar', '')
    if buscar:
        from django.db.models import Q
        promociones = promociones.filter(
            Q(titulo__icontains=buscar) | 
            Q(descripcion__icontains=buscar)
        )
    
    # ✅ FILTRO POR FECHAS
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    if fecha_desde:
        promociones = promociones.filter(fecha_inicio__gte=fecha_desde)
    
    if fecha_hasta:
        promociones = promociones.filter(fecha_fin__lte=fecha_hasta)
    
    # Ordenar por más reciente
    promociones = promociones.order_by('-fecha_inicio')
    
    context = {
        'promociones': promociones,
        'proveedor': proveedor,
        'estado_actual': estado,
        'vigencia_actual': vigencia,
        'buscar_actual': buscar,
        'fecha_desde_actual': fecha_desde,
        'fecha_hasta_actual': fecha_hasta,
    }
    
    return render(request, 'proveedores/promociones/lista.html', context)


@login_required
def crear_promocion(request):
    """
    Crear nueva promoción
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    if request.method == 'POST':
        form = PromocionForm(request.POST, request.FILES)
        if form.is_valid():
            promocion = form.save(commit=False)
            promocion.proveedor = proveedor
            promocion.save()
            messages.success(request, 'Promoción creada exitosamente.')
            return redirect('proveedores:lista_promociones')
    else:
        form = PromocionForm()
    
    context = {'form': form}
    return render(request, 'proveedores/promociones/crear.html', context)


@login_required
def editar_promocion(request, promocion_id):
    """
    Editar promoción existente
    """
    promocion = get_object_or_404(
        Promocion, 
        id=promocion_id, 
        proveedor__usuario=request.user
    )
    
    if request.method == 'POST':
        form = PromocionForm(request.POST, request.FILES, instance=promocion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promoción actualizada exitosamente.')
            return redirect('proveedores:lista_promociones')
    else:
        form = PromocionForm(instance=promocion)
    
    context = {'form': form, 'promocion': promocion}
    return render(request, 'proveedores/promociones/editar.html', context)


@login_required
def eliminar_promocion(request, promocion_id):
    """
    Eliminar permanentemente la promoción
    """
    promocion = get_object_or_404(
        Promocion, 
        id=promocion_id, 
        proveedor__usuario=request.user
    )
    
    if request.method == 'POST':
        titulo_promocion = promocion.titulo  # Guardar el título antes de eliminar
        promocion.delete()  # 👈 ELIMINAR PERMANENTEMENTE
        messages.success(request, f'✅ Promoción "{titulo_promocion}" eliminada permanentemente.')
        return redirect('proveedores:lista_promociones')
    
    context = {'promocion': promocion}
    return render(request, 'proveedores/promociones/eliminar.html', context)


# ==================== SOLICITUDES DE CONTACTO ====================

@login_required
def enviar_solicitud_contacto(request, comercio_id):
    """
    Enviar solicitud de contacto a un comercio
    (Requiere modelo Comercio implementado)
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    # comercio = get_object_or_404(Comercio, id=comercio_id, activo=True)
    
    # Verificar si ya existe una solicitud pendiente
    # solicitud_existente = SolicitudContacto.objects.filter(
    #     proveedor=proveedor,
    #     comercio=comercio,
    #     estado='pendiente'
    # ).exists()
    
    # if solicitud_existente:
    #     messages.warning(request, 'Ya tienes una solicitud pendiente con este comercio.')
    #     return redirect('detalle_comercio', comercio_id=comercio_id)
    
    if request.method == 'POST':
        form = SolicitudContactoForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.proveedor = proveedor
            # solicitud.comercio = comercio
            solicitud.save()
            
            # Actualizar contador del proveedor
            proveedor.contactos_enviados += 1
            proveedor.save(update_fields=['contactos_enviados'])
            
            messages.success(request, 'Solicitud de contacto enviada exitosamente.')
            return redirect('mis_solicitudes')
    else:
        form = SolicitudContactoForm()
    
    context = {
        'form': form,
        # 'comercio': comercio,
        'proveedor': proveedor
    }
    return render(request, 'proveedores/solicitudes/enviar.html', context)


@login_required
def mis_solicitudes(request):
    """
    Lista de solicitudes de contacto enviadas por el proveedor
    """
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    solicitudes = SolicitudContacto.objects.filter(
        proveedor=proveedor
    ).order_by('-fecha_solicitud')
    
    # Filtrar por estado
    estado = request.GET.get('estado')
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    context = {
        'solicitudes': solicitudes,
        'estado_seleccionado': estado
    }
    return render(request, 'proveedores/solicitudes/mis_solicitudes.html', context)


# ==================== VISTAS AJAX ====================

@login_required
def get_comunas_ajax(request):
    """
    Obtener comunas de una región (para filtros dinámicos)
    """
    region_id = request.GET.get('region_id')
    comunas = Comuna.objects.filter(region_id=region_id).values('id', 'nombre')
    return JsonResponse(list(comunas), safe=False)


@login_required
def toggle_destacado_producto(request, producto_id):
    """
    Activar/desactivar producto destacado
    """
    producto = get_object_or_404(
        ProductoServicio, 
        id=producto_id, 
        proveedor__usuario=request.user
    )
    
    producto.destacado = not producto.destacado
    producto.save()
    
    return JsonResponse({
        'success': True, 
        'destacado': producto.destacado
    })

# ==================== La configuracion ====================

@login_required
def configuracion_proveedor(request):
    """Vista de configuración completa"""
    try:
        proveedor = request.user.proveedor
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil_proveedor')
    
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Configuración guardada correctamente.')
            return redirect('proveedores:directorio_proveedores')
        else:
            messages.error(request, '❌ Error al guardar la configuración.')
    else:
        form = ConfiguracionForm(instance=proveedor)
    
    context = {
        'form': form, 
        'proveedor': proveedor,
        'user': request.user
    }
    return render(request, 'proveedores/configuracion.html', context)


@login_required
def eliminar_foto_perfil(request):
    """Eliminar foto de perfil del proveedor"""
    try:
        proveedor = request.user.proveedor
        if proveedor.foto_perfil:
            proveedor.foto_perfil.delete(save=True)
            messages.success(request, '✓ Foto de perfil eliminada.')
        else:
            messages.info(request, 'No tienes foto de perfil.')
    except Proveedor.DoesNotExist:
        messages.error(request, 'Debes crear primero un perfil de proveedor.')
        return redirect('proveedores:crear_perfil')
    
    return redirect('proveedores:configuracion')