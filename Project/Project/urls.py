from apps.seguridad import views as seguridad_views
from apps.seguridad.views import login_view, logout_view
from apps.socios import views as socios_views
from django.contrib import admin
from django.urls import path

from apps.control_acceso import views_entrenador

from apps.control_acceso.views_entrenador import planificador_rutina_view





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

    # ENTRENADOR
    path('entrenador/panel/', views_entrenador.entrenador_panel, name='entrenador_panel'),

    path('entrenador/rutinas/nueva/', views_entrenador.crear_rutina_entrenador_view, name='crear_rutina_entrenador'),

    path('entrenador/rutinas/<int:rutina_id>/editar/', views_entrenador.editar_rutina_entrenador_view, name='editar_rutina_entrenador'),

    # AJAX
    path('entrenador/rutinas/<int:rutina_id>/agregar/', views_entrenador.ajax_agregar_ejercicio, name='ajax_agregar_ejercicio'),
    path('entrenador/rutinas/<int:rutina_id>/eliminar/', views_entrenador.ajax_eliminar_ejercicio, name='ajax_eliminar_ejercicio'),
    path('entrenador/rutinas/<int:rutina_id>/limpiar/', views_entrenador.ajax_limpiar_dia, name='ajax_limpiar_dia'),
    path('entrenador/rutinas/<int:rutina_id>/asignar/', views_entrenador.ajax_asignar_rutina, name='ajax_asignar_rutina'),
    path("entrenador/rutina/planificar/", planificador_rutina_view, name="planificador_rutina"),


    path("entrenador/rutina/<int:rutina_id>/editar/", views_entrenador.editar_rutina_entrenador_view, name="editar_rutina_entrenador"),


    path("entrenador/rutina/<int:rutina_id>/dia/<int:dia>/ejercicios/",
     views_entrenador.obtener_ejercicios_dia_ajax,
     name="ajax_ejercicios_dia"),

    path("entrenador/rutina/<int:rutina_id>/add/",
     views_entrenador.agregar_ejercicio_ajax,
     name="ajax_agregar_ejercicio"),

    path("entrenador/ejercicio/<int:asignacion_id>/delete/",
     views_entrenador.eliminar_ejercicio_ajax,
     name="ajax_eliminar_ejercicio"),

    path("entrenador/ejercicio/<int:asignacion_id>/update/",
     views_entrenador.actualizar_ejercicio_ajax,
     name="ajax_actualizar_ejercicio"),


    path("ajax/agregar-ejercicio/<int:rutina_id>/",
        views_entrenador.ajax_agregar_ejercicio,
        name="ajax_agregar_ejercicio_alt"),

    path("ajax/eliminar-ejercicio/<int:rutina_id>/",
        views_entrenador.ajax_eliminar_ejercicio,
        name="ajax_eliminar_ejercicio_alt"),

    path("ajax/obtener-ejercicios-dia/<int:rutina_id>/<int:dia>/",
        views_entrenador.obtener_ejercicios_dia_ajax,
        name="ajax_obtener_ejercicios_dia_alt"),





]