# usuarios/urls.py (CONTENIDO MODIFICADO)

from django.urls import path
from . import views

urlpatterns = [
    # AUTH
    path('', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'), 
    path('logout/', views.logout_view, name='logout'),

    # PLATFORM/FORUM
    path('plataforma/', views.plataforma_comerciante_view, name='plataforma_comerciante'),
    path('publicar/', views.publicar_post_view, name='crear_publicacion'),
    
    # PERFIL
    path('perfil/', views.perfil_view, name='perfil'),
    
    # BENEFICIOS (NUEVA RUTA)
    path('beneficios/', views.beneficios_view, name='beneficios'),
    
    # RESTAURADO: Detalle del Post y Comentarios (Ver comentarios)
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    
    # RESTAURADO: Añadir Comentario (add comment, recarga página)
    path('post/<int:post_id>/comentar/', views.add_comment_view, name='add_comment'),
    
    # RESTAURADO: Liking posts (like, recarga página)
    path('post/<int:post_id>/like/', views.like_post_view, name='like_post'),
]