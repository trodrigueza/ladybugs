# seguridad/admin.py
from django.contrib import admin
from .models import Rol, Usuario, RegistroAuditoria


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "NombreRol")
    search_fields = ("NombreRol",)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "NombreUsuario", "RolID", "UltimoAcceso")
    search_fields = ("NombreUsuario",)
    list_filter = ("RolID",)
    readonly_fields = ("UltimoAcceso",)


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "FechaHora", "TipoAccion", "UsuarioID")
    list_filter = ("TipoAccion", "FechaHora")
    search_fields = ("Detalle",)
