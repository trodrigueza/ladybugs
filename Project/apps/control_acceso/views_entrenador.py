from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

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
        "dias_abbr": ["LU", "MA", "MI", "JU", "VI", "SA", "DO"],
    }

    return render(request, "Entrenador/PlanificadorRutina.html", context)







# ============================================================
# PANEL PRINCIPAL DEL ENTRENADOR
# ============================================================

@login_requerido
def entrenador_panel(request):
    """Pantalla inicial del entrenador"""
    # Conteos para el panel
    from apps.socios.models import Socio
    from apps.control_acceso.models import RutinaSemanal

    total_clientes = Socio.objects.count()
    rutinas_asignadas = RutinaSemanal.objects.count()
    socios_sin_rutina = Socio.objects.filter(rutinas__isnull=True).count()

    context = {
        "total_clientes": total_clientes,
        "rutinas_asignadas": rutinas_asignadas,
        "socios_sin_rutina": socios_sin_rutina,
    }

    return render(request, "Entrenador/PaneldeInicio.html", context)


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
        ejercicios_temp_json = request.POST.get("ejercicios_temp")

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
                "rutina": None,
                "dias_abbr": ["LU", "MA", "MI", "JU", "VI", "SA", "DO"],
            })

        # Persistir ejercicios temporales que el entrenador pudo haber arrastrado
        # antes de crear la rutina (cliente envía JSON en el input oculto).
        if ejercicios_temp_json:
            try:
                ejercicios_temp = json.loads(ejercicios_temp_json)
            except Exception:
                ejercicios_temp = []

            for item in ejercicios_temp:
                try:
                    asignar_ejercicio_a_rutina(
                        rutina_id=rutina.id,
                        ejercicio_id=item.get("ejercicio_id"),
                        dia_semana=int(item.get("dia")),
                        series=int(item.get("series")) if item.get("series") is not None else None,
                        repeticiones=int(item.get("reps") or item.get("repeticiones")) if (item.get("reps") or item.get("repeticiones")) else None,
                        tempo=item.get("tempo") or item.get("Tempo") or "",
                        peso_objetivo=float(item.get("peso")) if item.get("peso") is not None else None,
                    )
                except ValidationError as ve:
                    messages.warning(request, f"No se pudo agregar ejercicio: {ve}")
                except Exception:
                    messages.warning(request, "Algunos ejercicios temporales no pudieron guardarse.")

        # Mensaje de confirmación incluyendo el nombre del socio (siempre mostrar)
        try:
            socio_nombre = rutina.SocioID.NombreCompleto if hasattr(rutina.SocioID, 'NombreCompleto') else str(rutina.SocioID)
        except Exception:
            socio_nombre = str(rutina.SocioID_id)

        messages.success(request, f"Rutina '{rutina.Nombre}' creada correctamente para {socio_nombre}.")

        # En lugar de redirigir automáticamente, renderizamos de nuevo el planificador
        # con la rutina recién creada en el contexto. El entrenador puede decidir
        # después si navegar a la lista o al detalle/edición.
        ejercicios_dia = DiaRutinaEjercicio.objects.filter(RutinaID=rutina, DiaSemana=0)

        return render(request, "Entrenador/PlanificadorRutina.html", {
            "rutina": rutina,
            "ejercicios": ejercicios,
            "socios": socios,
            "ejercicios_dia": ejercicios_dia,
            "dias_abbr": ["LU", "MA", "MI", "JU", "VI", "SA", "DO"],
        })

    # GET - render del planificador para crear una nueva rutina
    return render(request, "Entrenador/PlanificadorRutina.html", {
        "ejercicios": ejercicios,
        "socios": socios,
        "rutina": None,
        "dias_abbr": ["LU", "MA", "MI", "JU", "VI", "SA", "DO"],
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
        "dias_abbr": ["LU", "MA", "MI", "JU", "VI", "SA", "DO"],
    })


# ============================================================
# LISTA Y DETALLE DE RUTINAS
# ============================================================


@login_requerido
def rutinas_list_view(request):
    """Lista todas las rutinas (con su socio si está asignada)."""
    # Limpiar rutinas vacías (sin ejercicios asociados en ningún día)
    # Esto evita que el entrenador vea rutinas sin contenido. Se realiza al momento
    # de listar para mantener la operación local y predecible.
    posibles_vacias = RutinaSemanal.objects.all()
    for r in posibles_vacias:
        # `dias_ejercicios` es la relación reverse desde DiaRutinaEjercicio hacia RutinaSemanal
        if not r.dias_ejercicios.exists():
            # eliminar rutina vacía
            r.delete()

    # Re-consultar rutinas limpias para renderizar
    rutinas = RutinaSemanal.objects.select_related('SocioID').prefetch_related('dias_ejercicios__EjercicioID').all()

    return render(request, 'Entrenador/RutinasList.html', {
        'rutinas': rutinas,
    })


@login_requerido
def rutina_detalle_view(request, rutina_id):
    """Muestra una rutina con sus ejercicios agrupados por día."""
    rutina = get_object_or_404(RutinaSemanal.objects.select_related('SocioID').prefetch_related('dias_ejercicios__EjercicioID'), id=rutina_id)

    # Agrupar ejercicios por día 0..6
    dias = {i: [] for i in range(7)}
    for dr in rutina.dias_ejercicios.all():
        dias[dr.DiaSemana].append(dr)

    nombres = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']

    dias_pares = [(nombres[i], dias[i]) for i in range(7)]

    return render(request, 'Entrenador/RutinaDetalle.html', {
        'rutina': rutina,
        'dias': dias,
        'dias_pares': dias_pares,
        'nombres_dias': nombres,
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
def ajax_crear_ejercicio(request):
    """Crear un nuevo ejercicio (AJAX). Devuelve JSON con el nuevo id y nombre."""
    nombre = request.POST.get('nombre')
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio.'})

    grupo = request.POST.get('grupo') or ''
    equipo = request.POST.get('equipo') or ''
    descripcion = request.POST.get('descripcion') or ''
    variantes = request.POST.get('variantes') or ''

    try:
        e = Ejercicio.objects.create(
            Nombre=nombre,
            GrupoMuscular=grupo,
            Equipo=equipo,
            Descripcion=descripcion,
            Variantes=variantes
        )
        return JsonResponse({'ok': True, 'id': e.id, 'nombre': e.Nombre})
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)})


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
def borrar_rutina_view(request, rutina_id):
    """Elimina una rutina completa. Responde JSON para peticiones AJAX o redirige a la lista."""
    rutina = get_object_or_404(RutinaSemanal, id=rutina_id)

    try:
        rutina.delete()
        messages.success(request, f"Rutina '{rutina.Nombre}' eliminada correctamente.")
        # Si es AJAX, devolver JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('CONTENT_TYPE','').startswith('application/json'):
            return JsonResponse({'ok': True})
        return redirect('rutinas_list')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('CONTENT_TYPE','').startswith('application/json'):
            return JsonResponse({'ok': False, 'error': str(e)})
        messages.error(request, 'No se pudo eliminar la rutina.')
        return redirect('rutinas_list')


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
