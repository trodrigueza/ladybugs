from apps.seguridad import views as seguridad_views
from apps.seguridad.views import login_view, logout_view
from apps.socios import views as socios_views
from django.contrib import admin
from django.urls import path

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
    path('socio/mi-rutina/historial/', socios_views.historial_sesiones_view, name='historial_sesiones'),
    path('socio/mi-rutina/sesion/<int:sesion_id>/', socios_views.detalle_sesion_view, name='detalle_sesion'),
    path('socio/mi-nutricion/', socios_views.mi_nutricion_view, name='mi_nutricion'),
    path('socio/mi-nutricion/toggle-comida/', socios_views.toggle_comida_view, name='toggle_comida'),
    path('socio/mi-nutricion/historial/', socios_views.historial_comidas_view, name='historial_comidas'),

    path('administrativo/panel/', socios_views.panel_admin_view, name='panel_admin'),
    path('administrativo/gestionar-usuarios/', seguridad_views.gestionar_usuarios_view, name='gestionar_usuarios'),

    path('entrenador/panel/', socios_views.planel_inicio_entrenador_view, name='entrenador_panel'),

    path('entrenador/routines/nueva/', socios_views.crear_rutina_entrenador_view, name='crear_rutina_entrenador'),
]