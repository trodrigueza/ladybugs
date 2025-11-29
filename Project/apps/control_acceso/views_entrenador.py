from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.seguridad.decoradores import login_requerido

from apps.control_acceso.models import (
    Ejercicio,
    RutinaSemanal,
    DiaRutinaEjercicio,
)

from apps.socios.models import Socio

from apps.control_acceso.servicios.rutinas_service import (
    crear_rutina_semanal,
    asignar_ejercicio_a_rutina,
    obtener_ejercicios_por_dia,
    ValidationError,
)

from apps.control_acceso.models import Ejercicio



from django.http import JsonResponse
from apps.control_acceso.models import DiaRutinaEjercicio, Ejercicio, RutinaSemanal
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@login_requerido
def obtener_ejercicios_dia_ajax(request, rutina_id, dia):
    asignaciones = DiaRutinaEjercicio.objects.filter(
        RutinaID_id=rutina_id, DiaSemana=dia
    ).select_related("EjercicioID")

    data = []
    for a in asignaciones:
        data.append({
            "id": a.id,
            "nombre": a.EjercicioID.Nombre,
            "series": a.Series,
            "reps": a.Repeticiones,
            "peso": str(a.PesoObjetivo) if a.PesoObjetivo else "0",
            "tempo": a.Tempo or "",
        })

    return JsonResponse({"ok": True, "ejercicios": data})



@login_requerido
def agregar_ejercicio_ajax(request, rutina_id):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Solo POST permitido"})

    ejercicio_id = request.POST.get("ejercicio_id")
    dia = int(request.POST.get("dia"))

    try:
        asignacion = asignar_ejercicio_a_rutina(
            rutina_id=rutina_id,
            ejercicio_id=ejercicio_id,
            dia_semana=dia,
            series=4,
            repeticiones=10,
            peso_objetivo=0,
            tempo="2-0-2",
        )
    except ValidationError as e:
        return JsonResponse({"ok": False, "error": str(e)})

    return JsonResponse({
        "ok": True,
        "id": asignacion.id,
        "nombre": asignacion.EjercicioID.Nombre,
    })


@login_requerido
def eliminar_ejercicio_ajax(request, asignacion_id):
    try:
        DiaRutinaEjercicio.objects.get(id=asignacion_id).delete()
        return JsonResponse({"ok": True})
    except:
        return JsonResponse({"ok": False, "error": "No existe asignación"})




@login_requerido
def actualizar_ejercicio_ajax(request, asignacion_id):
    if request.method != "POST":
        return JsonResponse({"ok": False})

    a = DiaRutinaEjercicio.objects.get(id=asignacion_id)
    a.Series = request.POST.get("series")
    a.Repeticiones = request.POST.get("reps")
    a.PesoObjetivo = request.POST.get("peso")
    a.Tempo = request.POST.get("tempo")
    a.save()

    return JsonResponse({"ok": True})




def planificador_rutina_view(request):
    ejercicios = Ejercicio.objects.all().order_by("Nombre")

    context = {
        "ejercicios": ejercicios,
        "ejercicios_dia": [],  # Todavía no hay asignados
    }

    return render(request, "Entrenador/PlanificadorRutina.html", context)







# ============================================================
# PANEL PRINCIPAL DEL ENTRENADOR
# ============================================================

@login_requerido
def entrenador_panel(request):
    """Pantalla inicial del entrenador"""
    return render(request, "Entrenador/PaneldeInicio.html")


# ============================================================
# CREAR RUTINA NUEVA
# ============================================================

@login_requerido
def crear_rutina_entrenador_view(request):
    """
    Renderiza el planificador de rutinas y permite crear una rutina nueva.
    """
    ejercicios = Ejercicio.objects.all()
    socios = Socio.objects.all()

    if request.method == "POST":
        nombre = request.POST.get("nombre_rutina")
        dias = request.POST.get("dias_entrenamiento")
        socio_id = request.POST.get("socio_id")

        try:
            rutina = crear_rutina_semanal(
                socio_id=socio_id,
                nombre=nombre,
                dias_entrenamiento=dias,
                es_plantilla=False
            )
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, "Entrenador/PlanificadorRutina.html", {
                "ejercicios": ejercicios,
                "socios": socios,
                "rutina": None
            })

        return redirect("editar_rutina_entrenador", rutina_id=rutina.id)

    return render(request, "Entrenador/PlanificadorRutina.html", {
        "ejercicios": ejercicios,
        "socios": socios,
        "rutina": None
    })


# ============================================================
# EDITAR RUTINA EXISTENTE
# ============================================================

@login_requerido
def editar_rutina_entrenador_view(request, rutina_id):
    rutina = RutinaSemanal.objects.get(id=rutina_id)
    ejercicios = Ejercicio.objects.all()

    # Para mostrar el día por defecto (lunes = 0)
    ejercicios_dia = DiaRutinaEjercicio.objects.filter(RutinaID=rutina, DiaSemana=0)

    return render(request, "Entrenador/PlanificadorRutina.html", {
        "rutina": rutina,
        "ejercicios": ejercicios,
        "ejercicios_dia": ejercicios_dia,
        "socios": Socio.objects.all(),
    })



# ============================================================
# ENDPOINTS AJAX (Guardar, Eliminar, Limpiar)
# ============================================================

@login_requerido
@require_POST
def ajax_agregar_ejercicio(request, rutina_id):
    """Agrega un ejercicio a un día de la rutina"""
    ejercicio_id = request.POST.get("ejercicio_id")
    dia = int(request.POST.get("dia"))
    series = request.POST.get("series") or None
    reps = request.POST.get("reps") or None
    tempo = request.POST.get("tempo") or ""
    peso = request.POST.get("peso") or None

    try:
        asignacion = asignar_ejercicio_a_rutina(
            rutina_id=rutina_id,
            ejercicio_id=ejercicio_id,
            dia_semana=dia,
            series=int(series) if series else None,
            repeticiones=int(reps) if reps else None,
            tempo=tempo,
            peso_objetivo=float(peso) if peso else None,
        )
        return JsonResponse({"ok": True, "id": asignacion.id})

    except ValidationError as e:
        return JsonResponse({"ok": False, "error": str(e)})


@login_requerido
@require_POST
def ajax_eliminar_ejercicio(request, rutina_id):
    asignacion_id = request.POST.get("id")
    asignacion = get_object_or_404(DiaRutinaEjercicio, id=asignacion_id)
    asignacion.delete()

    return JsonResponse({"ok": True})


@login_requerido
@require_POST
def ajax_limpiar_dia(request, rutina_id):
    dia = int(request.POST.get("dia"))

    DiaRutinaEjercicio.objects.filter(
        RutinaID_id=rutina_id,
        DiaSemana=dia
    ).delete()

    return JsonResponse({"ok": True})


@login_requerido
@require_POST
def ajax_asignar_rutina(request, rutina_id):
    """Asociar una rutina a un socio"""
    socio_id = request.POST.get("socio_id")
    rutina = get_object_or_404(RutinaSemanal, id=rutina_id)
    socio = get_object_or_404(Socio, id=socio_id)

    rutina.SocioID = socio
    rutina.save()

    return JsonResponse({"ok": True})
