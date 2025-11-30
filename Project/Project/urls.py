from apps.control_acceso import views_entrenador
from apps.control_acceso.views_entrenador import planificador_rutina_view
from apps.pagos import views as pagos_views
from apps.seguridad import views as seguridad_views
from apps.socios import views as socios_views
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # LOGIN / LOGOUT
    path("login/", seguridad_views.login_view, name="login"),
    path("logout/", seguridad_views.logout_view, name="logout"),
    # HOME apunta al login
    path("", seguridad_views.login_view, name="home"),
    # PANEL SOCIO
    path("socio/panel/", socios_views.panel_de_control_view, name="socio_panel"),
    path("socio/mi-rutina/", socios_views.mi_rutina_view, name="mi_rutina"),
    path(
        "socio/mi-rutina/iniciar_sesion/",
        socios_views.iniciar_sesion_view,
        name="iniciar_sesion",
    ),
    path(
        "socio/mi-rutina/terminar_sesion/",
        socios_views.terminar_sesion_view,
        name="terminar_sesion",
    ),
    path(
        "socio/mi-rutina/toggle_ejercicio/",
        socios_views.toggle_ejercicio_view,
        name="toggle_ejercicio",
    ),
    path(
        "socio/mi-rutina/sesion/<int:sesion_id>/",
        socios_views.detalle_sesion_view,
        name="detalle_sesion",
    ),
    path(
        "socio/mi-rutina/historial/",
        socios_views.historial_sesiones_view,
        name="historial_sesiones",
    ),
    path("socio/mi-nutricion/", socios_views.mi_nutricion_view, name="mi_nutricion"),
    path(
        "socio/mi-nutricion/toggle-comida/",
        socios_views.toggle_comida_view,
        name="toggle_comida",
    ),
    path(
        "socio/mi-nutricion/historial/",
        socios_views.historial_comidas_view,
        name="historial_comidas",
    ),
    path("socio/mi-perfil/", socios_views.mi_perfil_view, name="mi_perfil"),
    # ADMINISTRATIVO (panel/gestion de usuarios y pagos)
    path('administrativo/panel/', socios_views.panel_admin_view, name='panel_admin'),
    path('administrativo/gestionar-usuarios/', seguridad_views.gestionar_usuarios_view, name='gestionar_usuarios'),
    path('administrativo/gestion-pagos/', pagos_views.gestion_pagos_view, name='gestion_pagos'),
    path('administrativo/gestion-pagos/registrar/', pagos_views.registrar_pago_view, name='registrar_pago'),
    path('administrativo/crear-plan-membresia/', pagos_views.crear_plan_membresia_view, name='crear_plan_membresia'),
    path('administrativo/eliminar-plan-membresia/<int:plan_id>/', pagos_views.eliminar_plan_membresia_view, name='eliminar_plan_membresia'),
    path('administrativo/editar-plan-membresia/<int:plan_id>/', pagos_views.editar_plan_membresia_view, name='editar_plan_membresia'),
    # Rutas de clientes: mantener acceso administrativo y exponer ruta para entrenador
    path('administrativo/clientes/', socios_views.clientes_list_view, name='admin_clientes'),
    path('entrenador/clientes/', socios_views.clientes_list_view, name='clientes_list'),

    # ADMIN: user management routes (seleccionar/crear/editar/eliminar)
    path(
        "administrativo/agregar-usuario/",
        seguridad_views.seleccionar_tipo_usuario_view,
        name="agregar_usuario",
    ),
    path(
        "administrativo/crear-usuario/<str:tipo_rol>/",
        seguridad_views.crear_usuario_view,
        name="crear_usuario",
    ),
    path(
        "administrativo/crear-socio/",
        seguridad_views.crear_socio_view,
        name="crear_socio",
    ),
    path(
        "administrativo/crear-membresia/<int:socio_id>/",
        seguridad_views.crear_membresia_view,
        name="crear_membresia",
    ),
    path(
        "administrativo/editar-socio/<int:socio_id>/",
        seguridad_views.editar_socio_view,
        name="editar_socio",
    ),
    path(
        "administrativo/editar-usuario/<int:usuario_id>/",
        seguridad_views.editar_usuario_view,
        name="editar_usuario",
    ),
    path(
        "administrativo/gestionar-usuarios/eliminar/<str:tipo>/<int:entidad_id>/",
        seguridad_views.eliminar_entidad_view,
        name="eliminar_entidad",
    ),
    path(
        "administrativo/gestionar-usuarios/eliminar-socio/<int:socio_id>/",
        seguridad_views.eliminar_socio_view,
        name="eliminar_socio",
    ),
    # ENTRENADOR
    path(
        "entrenador/panel/", views_entrenador.entrenador_panel, name="entrenador_panel"
    ),
    path(
        "entrenador/nutricion/",
        views_entrenador.entrenador_nutricion_view,
        name="entrenador_nutricion",
    ),
    path(
        "entrenador/nutricion/<int:socio_id>/",
        views_entrenador.entrenador_plan_nutricion_detalle,
        name="entrenador_plan_nutricion",
    ),
    path(
        "entrenador/nutricion/plantilla/<int:plan_id>/",
        views_entrenador.entrenador_plantilla_nutricion_detalle,
        name="entrenador_plantilla_nutricion",
    ),
    path(
        "entrenador/nutricion/plantillas/crear/",
        views_entrenador.entrenador_crear_plantilla_nutricional,
        name="entrenador_crear_plantilla",
    ),
    path(
        "entrenador/nutricion/socio/<int:socio_id>/crear-plan/",
        views_entrenador.entrenador_crear_plan_manual,
        name="entrenador_crear_plan_socio",
    ),
    path(
        "entrenador/nutricion/plan/<int:plan_id>/actualizar/",
        views_entrenador.entrenador_nutricion_actualizar_plan,
        name="entrenador_nutricion_actualizar_plan",
    ),
    path(
        "entrenador/nutricion/plan/<int:plan_id>/agregar-comida/",
        views_entrenador.entrenador_nutricion_agregar_comida,
        name="entrenador_nutricion_agregar_comida",
    ),
    path(
        "entrenador/nutricion/comida/<int:dia_id>/eliminar/",
        views_entrenador.entrenador_nutricion_eliminar_comida,
        name="entrenador_nutricion_eliminar_comida",
    ),
    path(
        "entrenador/nutricion/comida/<int:dia_id>/agregar-alimento/",
        views_entrenador.entrenador_nutricion_agregar_alimento,
        name="entrenador_nutricion_agregar_alimento",
    ),
    path(
        "entrenador/nutricion/alimentos/crear/",
        views_entrenador.entrenador_nutricion_crear_alimento,
        name="entrenador_nutricion_crear_alimento",
    ),
    path(
        "entrenador/nutricion/alimento/<int:item_id>/actualizar/",
        views_entrenador.entrenador_nutricion_actualizar_alimento,
        name="entrenador_nutricion_actualizar_alimento",
    ),
    path(
        "entrenador/nutricion/alimento/<int:item_id>/eliminar/",
        views_entrenador.entrenador_nutricion_eliminar_alimento,
        name="entrenador_nutricion_eliminar_alimento",
    ),
    # NUEVA RUTINA
    path(
        "entrenador/rutinas/nueva/",
        views_entrenador.crear_rutina_entrenador_view,
        name="crear_rutina_entrenador",
    ),
    # LISTA Y DETALLE DE RUTINAS
    path('entrenador/rutinas/', views_entrenador.rutinas_list_view, name='rutinas_list'),
    path('entrenador/rutinas/banco/', views_entrenador.rutinas_banco_view, name='rutinas_banco'),
    path('entrenador/rutina/<int:rutina_id>/', views_entrenador.rutina_detalle_view, name='rutina_detalle'),

    # Entrenador: rutas por socio (editar/ver rutina)
    path('entrenador/socio/<int:socio_id>/editar/', views_entrenador.entrenador_editar_socio_view, name='entrenador_editar_socio'),
    path('entrenador/socio/<int:socio_id>/rutina/', views_entrenador.entrenador_ver_rutina_view, name='entrenador_ver_rutina'),

    # EDITAR RUTINA
    path(
        "entrenador/rutina/<int:rutina_id>/editar/",
        views_entrenador.editar_rutina_entrenador_view,
        name="editar_rutina_entrenador",
    ),
    # AJAX: agregar/eliminar/limpiar/asignar
    path(
        "entrenador/rutina/<int:rutina_id>/add/",
        views_entrenador.ajax_agregar_ejercicio,
        name="ajax_agregar_ejercicio",
    ),
    path(
        "entrenador/rutina/<int:rutina_id>/eliminar/",
        views_entrenador.ajax_eliminar_ejercicio,
        name="ajax_eliminar_ejercicio",
    ),
    path(
        "entrenador/rutina/<int:rutina_id>/limpiar/",
        views_entrenador.ajax_limpiar_dia,
        name="ajax_limpiar_dia",
    ),
    path(
        "entrenador/rutina/<int:rutina_id>/asignar/",
        views_entrenador.ajax_asignar_rutina,
        name="ajax_asignar_rutina",
    ),
    # Obtener ejercicios por día
    path(
        "entrenador/rutina/<int:rutina_id>/dia/<int:dia>/ejercicios/",
        views_entrenador.obtener_ejercicios_dia_ajax,
        name="ajax_ejercicios_dia",
    ),
    # Crear ejercicio desde UI del entrenador
    path(
        "entrenador/ejercicios/nuevo/",
        views_entrenador.ajax_crear_ejercicio,
        name="ajax_crear_ejercicio",
    ),
    # AJAX actualizar asignación (series/reps/peso/tempo)
    path(
        "entrenador/asignacion/<int:asignacion_id>/actualizar/",
        views_entrenador.actualizar_ejercicio_ajax,
        name="ajax_actualizar_ejercicio",
    ),
    # Borrar rutina completa
    path(
        "entrenador/rutina/<int:rutina_id>/borrar/",
        views_entrenador.borrar_rutina_view,
        name="borrar_rutina",
    ),
]
