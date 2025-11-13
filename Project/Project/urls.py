# Project/urls.py
from django.contrib import admin
from django.urls import path
from apps.socios.views import register_view
from apps.seguridad.views import login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('', login_view, name='home'),
]