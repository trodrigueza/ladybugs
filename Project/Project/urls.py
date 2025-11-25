from django.contrib import admin
from django.urls import path

from apps.socios.views import (
    register_view,
    panel_de_control_view,
    planel_inicio_entrenador_view,
    panel_admin_view,

)

from apps.seguridad.views import login_view, logout_view


urlpatterns = [
    path('admin/', admin.site.urls),

    # LOGIN / LOGOUT
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # REGISTRO
    path('register/', register_view, name='register'),

    # HOME apunta al login
    path('', login_view, name='home'),

    # PANEL SEGÚN ROL
    path('socio/panel/', panel_de_control_view, name='panel_control'),
    path('administrativo/panel/', panel_admin_view, name='panel_admin'),
    path('entrenador/panel/', planel_inicio_entrenador_view, name='panel_entrenador')
]
