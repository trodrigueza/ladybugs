from django.contrib import admin

from .models import RegistroComidaDiaria, Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ("NombreCompleto", "Identificacion", "Email", "Telefono")
    search_fields = ("NombreCompleto", "Identificacion", "Email")


@admin.register(RegistroComidaDiaria)
class RegistroComidaDiariaAdmin(admin.ModelAdmin):
    list_display = ("SocioID", "DiaComidaID", "Fecha", "Completado", "HoraCompletado")
    list_filter = ("Completado", "Fecha", "DiaComidaID__DiaSemana")
    search_fields = ("SocioID__NombreCompleto", "DiaComidaID__TipoComida")
