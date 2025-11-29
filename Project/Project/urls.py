from django.contrib import admin
from django.urls import path
from apps.socios import views as socios_views
from apps.seguridad.views import login_view, logout_view, panel_admin_view
from apps.seguridad import views as seguridad_views
from apps.pagos import views as pagos_views
from apps.control_acceso import views_entrenador
from apps.control_acceso.views_entrenador import planificador_rutina_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # LOGIN / LOGOUT
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # HOME apunta al login
    path('', login_view, name='home'),
    # PANEL SEGÚN ROL
    path('socio/panel/', socios_views.panel_de_control_view, name='socio_panel'),
    path('socio/mi-rutina/', socios_views.mi_rutina_view, name='mi_rutina'),
    path('socio/mi-rutina/iniciar_sesion/', socios_views.iniciar_sesion_view, name='iniciar_sesion'),
    path('socio/mi-rutina/terminar_sesion/', socios_views.terminar_sesion_view, name='terminar_sesion'),
    path('socio/mi-rutina/toggle_ejercicio/', socios_views.toggle_ejercicio_view, name='toggle_ejercicio'),
    path('socio/mi-rutina/sesion/<int:sesion_id>/', socios_views.detalle_sesion_view, name='detalle_sesion'),
    path('socio/mi-rutina/historial/', socios_views.historial_sesiones_view, name='historial_sesiones'),
    path('socio/mi-nutricion/', socios_views.mi_nutricion_view, name='mi_nutricion'),
    path('socio/mi-nutricion/toggle-comida/', socios_views.toggle_comida_view, name='toggle_comida'),
    path('socio/mi-nutricion/historial/', socios_views.historial_comidas_view, name='historial_comidas'),
    
    # ADMINISTRATIVO
    path('Administrativo/panel/', panel_admin_view, name='panel_admin'),
    path('Administrativo/gestionar-usuarios/', seguridad_views.gestionar_usuarios_view, name='gestionar_usuarios'),
    path('Administrativo/gestionar-usuarios/agregar-usuario/', seguridad_views.seleccionar_tipo_usuario_view, name='agregar_usuario'),
    path('Administrativo/gestionar-usuarios/crear-usuario/<str:tipo_rol>/', seguridad_views.crear_usuario_view, name='crear_usuario'),
    path('Administrativo/gestionar-usuarios/crear-socio/', seguridad_views.crear_socio_view, name='crear_socio'),
    path('Administrativo/gestionar-usuarios/crear-membresia/<int:socio_id>/', seguridad_views.crear_membresia_view, name='crear_membresia'),
    path('Administrativo/gestionar-usuarios/editar-socio/<int:socio_id>/', seguridad_views.editar_socio_view, name='editar_socio'),
    path('Administrativo/gestionar-usuarios/editar-usuario/<int:usuario_id>/', seguridad_views.editar_usuario_view, name='editar_usuario'),
    path('Administrativo/gestionar-usuarios/eliminar/<str:tipo>/<int:entidad_id>/', seguridad_views.eliminar_entidad_view, name='eliminar_entidad'),
    path('Administrativo/gestionar-usuarios/eliminar-socio/<int:socio_id>/', seguridad_views.eliminar_socio_view, name='eliminar_socio'),
    
    # GESTIÓN DE PAGOS
    path('Administrativo/gestion-pagos/', pagos_views.gestion_pagos_view, name='gestion_pagos'),
    path('Administrativo/gestion-pagos/registrar/', pagos_views.registrar_pago_view, name='registrar_pago'),

    # ENTRENADOR
    path('entrenador/panel/', views_entrenador.entrenador_panel, name='entrenador_panel'),
    path('entrenador/rutinas/nueva/', views_entrenador.crear_rutina_entrenador_view, name='crear_rutina_entrenador'),
    path('entrenador/rutinas/<int:rutina_id>/editar/', views_entrenador.editar_rutina_entrenador_view, name='editar_rutina_entrenador'),
    path('entrenador/rutina/planificar/', planificador_rutina_view, name='planificador_rutina'),
    path('entrenador/rutina/<int:rutina_id>/editar/', views_entrenador.editar_rutina_entrenador_view, name='editar_rutina_entrenador'),
    path('entrenador/rutina/<int:rutina_id>/dia/<int:dia>/ejercicios/', views_entrenador.obtener_ejercicios_dia_ajax, name='ajax_ejercicios_dia'),
    path('entrenador/rutina/<int:rutina_id>/add/', views_entrenador.agregar_ejercicio_ajax, name='ajax_agregar_ejercicio'),
    path('entrenador/ejercicio/<int:asignacion_id>/delete/', views_entrenador.eliminar_ejercicio_ajax, name='ajax_eliminar_ejercicio'),
    path('entrenador/ejercicio/<int:asignacion_id>/update/', views_entrenador.actualizar_ejercicio_ajax, name='ajax_actualizar_ejercicio'),
    
    # AJAX adicionales
    path('ajax/agregar-ejercicio/<int:rutina_id>/', views_entrenador.ajax_agregar_ejercicio, name='ajax_agregar_ejercicio_alt'),
    path('ajax/eliminar-ejercicio/<int:rutina_id>/', views_entrenador.ajax_eliminar_ejercicio, name='ajax_eliminar_ejercicio_alt'),
    path('ajax/obtener-ejercicios-dia/<int:rutina_id>/<int:dia>/', views_entrenador.obtener_ejercicios_dia_ajax, name='ajax_obtener_ejercicios_dia_alt'),
    path('entrenador/rutinas/<int:rutina_id>/limpiar/', views_entrenador.ajax_limpiar_dia, name='ajax_limpiar_dia'),
    path('entrenador/rutinas/<int:rutina_id>/asignar/', views_entrenador.ajax_asignar_rutina, name='ajax_asignar_rutina'),
]
