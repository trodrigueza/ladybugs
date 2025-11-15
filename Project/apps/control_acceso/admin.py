from django.contrib import admin

from .models import (
    Alimento,
    Asistencia,
    ComidaAlimento,
    DiaComida,
    DiaRutinaEjercicio,
    EjecucionSesion,
    Ejercicio,
    PlanNutricional,
    RutinaSemanal,
)


@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    list_display = ["Nombre", "GrupoMuscular", "Equipo", "Version"]
    search_fields = ["Nombre", "GrupoMuscular"]
    list_filter = ["GrupoMuscular", "Equipo"]


@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = ["Nombre", "Kcal", "PorcionBase", "Version"]
    search_fields = ["Nombre"]
    list_filter = ["Kcal"]


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_socio_nombre",
        "FechaHoraEntrada",
        "FechaHoraSalida",
        "TerminalAcceso",
    ]
    list_filter = ["FechaHoraEntrada", "TerminalAcceso"]
    search_fields = ["SocioMembresiaID__SocioID__NombreCompleto"]
    date_hierarchy = "FechaHoraEntrada"

    def get_socio_nombre(self, obj):
        return obj.SocioMembresiaID.SocioID.NombreCompleto

    get_socio_nombre.short_description = "Socio"


@admin.register(RutinaSemanal)
class RutinaSemanalAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_socio_nombre",
        "Nombre",
        "DiasEntrenamiento",
        "EsPlantilla",
    ]
    list_filter = ["EsPlantilla"]
    search_fields = ["Nombre", "SocioID__NombreCompleto"]

    def get_socio_nombre(self, obj):
        return obj.SocioID.NombreCompleto

    get_socio_nombre.short_description = "Socio"


@admin.register(DiaRutinaEjercicio)
class DiaRutinaEjercicioAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_rutina",
        "get_ejercicio",
        "DiaSemana",
        "Series",
        "Repeticiones",
        "PesoObjetivo",
    ]
    list_filter = ["DiaSemana"]
    search_fields = ["RutinaID__Nombre", "EjercicioID__Nombre"]

    def get_rutina(self, obj):
        return obj.RutinaID.Nombre

    get_rutina.short_description = "Rutina"

    def get_ejercicio(self, obj):
        return obj.EjercicioID.Nombre

    get_ejercicio.short_description = "Ejercicio"


@admin.register(EjecucionSesion)
class EjecucionSesionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_ejercicio",
        "FechaEjecucion",
        "PesoEfectivo",
        "SeriesEfectivas",
        "RPE",
    ]
    list_filter = ["FechaEjecucion", "RPE"]
    date_hierarchy = "FechaEjecucion"

    def get_ejercicio(self, obj):
        return obj.DiaRutinaEjercicioID.EjercicioID.Nombre

    get_ejercicio.short_description = "Ejercicio"


@admin.register(PlanNutricional)
class PlanNutricionalAdmin(admin.ModelAdmin):
    list_display = ["id", "get_socio_nombre", "ObjetivoCaloricoDiario"]
    search_fields = ["SocioID__NombreCompleto"]

    def get_socio_nombre(self, obj):
        return obj.SocioID.NombreCompleto

    get_socio_nombre.short_description = "Socio"


@admin.register(DiaComida)
class DiaComidaAdmin(admin.ModelAdmin):
    list_display = ["id", "get_plan", "DiaSemana", "TipoComida"]
    list_filter = ["DiaSemana", "TipoComida"]

    def get_plan(self, obj):
        return f"Plan {obj.PlanNutricionalID.id}"

    get_plan.short_description = "Plan"


@admin.register(ComidaAlimento)
class ComidaAlimentoAdmin(admin.ModelAdmin):
    list_display = ["id", "get_alimento", "Porcion", "Cantidad"]
    search_fields = ["AlimentoID__Nombre"]

    def get_alimento(self, obj):
        return obj.AlimentoID.Nombre

    get_alimento.short_description = "Alimento"
