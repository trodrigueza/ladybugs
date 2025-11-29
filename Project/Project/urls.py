from django.contrib import admin
from django.urls import path
from apps.socios import views as socios_views
from apps.seguridad.views import login_view, logout_view
from apps.seguridad import views as seguridad_views
urlpatterns = [
    path('admin/', admin.site.urls),
    # LOGIN / LOGOUT
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # REGISTRO
    path('register/', socios_views.register_view, name='register'),
    # HOME apunta al login
    path('', login_view, name='home'),
    # PANEL SEGÚN ROL
    path('socio/panel/', socios_views.panel_de_control_view, name='socio_panel'),
    path('socio/mi-rutina/', socios_views.mi_rutina_view, name='mi_rutina'),
    path('socio/mi-rutina/iniciar_sesion/', socios_views.iniciar_sesion_view, name='iniciar_sesion'),
    path('socio/mi-rutina/terminar_sesion/', socios_views.terminar_sesion_view, name='terminar_sesion'),
    path('socio/mi-rutina/toggle_ejercicio/', socios_views.toggle_ejercicio_view, name='toggle_ejercicio'),
    path('socio/mi-rutina/sesion/<int:sesion_id>/', socios_views.detalle_sesion_view, name='detalle_sesion'),
    path('Administrativo/panel/', socios_views.panel_admin_view, name='panel_admin'),
    
    path('Administrativo/gestionar-usuarios/', seguridad_views.gestionar_usuarios_view, name='gestionar_usuarios'),
    path('Administrativo/gestionar-usuarios/agregar-usuario/', seguridad_views.seleccionar_tipo_usuario_view, name='agregar_usuario'),
    path('Administrativo/gestionar-usuarios/crear-usuario/<str:tipo_rol>/', seguridad_views.crear_usuario_view, name='crear_usuario'),
    path('Administrativo/gestionar-usuarios/editar-socio/<int:socio_id>/', seguridad_views.editar_socio_view, name='editar_socio'),
    path('Administrativo/gestionar-usuarios/editar-usuario/<int:usuario_id>/', seguridad_views.editar_usuario_view, name='editar_usuario'),
    path('Administrativo/gestionar-usuarios/eliminar-socio/<int:socio_id>/', seguridad_views.eliminar_socio_view, name='eliminar_socio'),
    path('Administrativo/gestionar-usuarios/eliminar/<str:tipo>/<int:entidad_id>/', seguridad_views.eliminar_entidad_view, name='eliminar_entidad'),
    path('entrenador/panel/', socios_views.planel_inicio_entrenador_view, name='entrenador_panel'),

    path("Administrativo/gestionar-usuarios/crear-socio/", seguridad_views.crear_socio_view, name="crear_socio"),
    path("Administrativo/gestionar-usuarios/crear-membresia/<int:socio_id>/", seguridad_views.crear_membresia_view, name="crear_membresia"),
]
