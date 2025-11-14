from django.urls import path
from . import views

urlpatterns = [
    # CORREGIDO: La vista de registro ahora se llama 'registro_view'
    path('', views.registro_view, name='registro'),

    # URL para la vista de login
    path('login/', views.login_view, name='login'), 
    
    # URL para cerrar sesión
    path('logout/', views.logout_view, name='logout'),

    path('plataforma/', views.plataforma_comerciante_view, name='plataforma_comerciante'),
    
    # CORREGIDO: URL para crear publicaciones (ahora publicar_post_view)
    path('publicar/', views.publicar_post_view, name='crear_publicacion'),
    
    # URL para el perfil
    path('perfil/', views.perfil_view, name='perfil'),
]