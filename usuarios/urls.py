from django.urls import path
from . import views

urlpatterns = [
    # Verifica que el nombre sea 'registro' para que el HTML funcione
    path('', views.registro_comerciante_view, name='registro'),

    path('plataforma/', views.plataforma_comerciante_view, name='plataforma_comerciante'),
    
    # URL para la vista de login
    path('login/', views.login_view, name='login'), 
    
    # NUEVA URL para crear publicaciones
    path('publicar/', views.crear_publicacion_view, name='crear_publicacion'),

    path('perfil/', views.perfil_view, name='perfil'),
]