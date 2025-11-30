from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.seguridad.decoradores import login_requerido

from apps.control_acceso.models import (
    Ejercicio,
    RutinaSemanal,
    DiaRutinaEjercicio,
    PlanNutricional,
    DiaComida,
    ComidaAlimento,
    Alimento,
)

from apps.socios.models import Socio
from apps.control_acceso.models import SesionEntrenamiento
from apps.seguridad.servicios.FormularioSocio_Membresia import SocioForm
from apps.seguridad.models import Usuario
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.control_acceso.servicios.rutinas_service import (
    crear_rutina_semanal,
    asignar_ejercicio_a_rutina,
    obtener_ejercicios_por_dia,
    ValidationError,
)

from apps.control_acceso.servicios.nutricion_service import (
    asignar_plan_desde_plantilla,
    get_nutrition_templates,
    aplicar_plan_desde_template_db,
)


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
    # Parse and sanitize numeric inputs
    series_raw = request.POST.get("series")
    reps_raw = request.POST.get("reps")
    peso_raw = request.POST.get("peso")
    tempo_raw = request.POST.get("tempo")

    # Series and reps: try to convert to int, allow null
    try:
        a.Series = int(series_raw) if series_raw not in (None, "") else None
    except (ValueError, TypeError):
        a.Series = None

    try:
        a.Repeticiones = int(reps_raw) if reps_raw not in (None, "") else None
    except (ValueError, TypeError):
        a.Repeticiones = None

    # PesoObjetivo: convert to Decimal, accept comma or dot as decimal separator, clamp to >= 0
    from decimal import Decimal, InvalidOperation
    if peso_raw in (None, ""):
        a.PesoObjetivo = None
    else:
        # Normalize comma decimal separator
        peso_norm = str(peso_raw).replace(',', '.')
        try:
            p = Decimal(peso_norm)
            if p < 0:
                p = Decimal('0.00')
            a.PesoObjetivo = p
        except (InvalidOperation, ValueError):
            a.PesoObjetivo = None

    a.Tempo = tempo_raw or None
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



@login_requerido
def entrenador_editar_socio_view(request, socio_id):
    """Permite al entrenador editar datos básicos del socio (nombre, email, telefono, altura, saludbasica).

    Nota: esta vista está pensada para uso del Entrenador; no requiere rol 'administrativo'.
    """
    # Permitir también a administrativos si es necesario
    usuario_rol = request.session.get("usuario_rol", "").lower()
    if usuario_rol not in ("entrenador", "administrativo"):
        from django.contrib import messages
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    socio = get_object_or_404(Socio, id=socio_id)

    if request.method == "POST":
        form = SocioForm(request.POST, instance=socio)
        if form.is_valid():
            form.save()
            messages.success(request, f"Socio {socio.NombreCompleto} actualizado correctamente.")
            return redirect("clientes_list")
    else:
        form = SocioForm(instance=socio)

    return render(request, "Administrador/editarSocio.html", {"form": form, "socio": socio, "is_entrenador_view": True})


@login_requerido
def entrenador_ver_rutina_view(request, socio_id):
    """Muestra la rutina principal de un socio desde la perspectiva del entrenador.

    Si el socio tiene al menos una rutina, redirige al detalle de la primera rutina.
    Si no tiene rutina, muestra un mensaje y vuelve a la lista de clientes.
    """
    usuario_rol = request.session.get("usuario_rol", "").lower()
    if usuario_rol not in ("entrenador", "administrativo"):
        from django.contrib import messages
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    socio = get_object_or_404(Socio, id=socio_id)

    rutina = RutinaSemanal.objects.filter(SocioID=socio).first()
    if rutina:
        return redirect("rutina_detalle", rutina_id=rutina.id)
    else:
        messages.info(request, "Este socio no tiene una rutina asignada.")
        return redirect("clientes_list")







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
    # Lista de socios sin rutina (limitada) con su última medición para mostrar en el panel
    from apps.socios.models import Medicion
    socios_wo_qs = Socio.objects.filter(rutinas__isnull=True).order_by('NombreCompleto')[:8]
    socios_sin_rutina_list = []
    for s in socios_wo_qs:
        ultima = Medicion.objects.filter(SocioID=s).order_by('-Fecha').first()
        socios_sin_rutina_list.append({
            "socio": s,
            "ultima_medicion": ultima,
        })
    # (sin KPI temporal en este panel) — mantenemos solo conteos básicos
    context = {
        "total_clientes": total_clientes,
        "rutinas_asignadas": rutinas_asignadas,
        "socios_sin_rutina": socios_sin_rutina,
        "socios_sin_rutina_list": socios_sin_rutina_list,
    }
    # --- Calcular rachas actuales (top N) basadas en SesionEntrenamiento por día ---
    import datetime
    from django.utils import timezone as dj_timezone

    hoy = dj_timezone.localdate()
    # obtener ids de socios que tienen sesiones
    socio_ids_with_sessions = (
        SesionEntrenamiento.objects.values_list("SocioMembresiaID__SocioID", flat=True).distinct()
    )
    socios_with_sessions = Socio.objects.filter(id__in=socio_ids_with_sessions)

    def compute_current_streak(socio):
        # obtener fechas (date) de sesiones para el socio
        fechas = list(
            SesionEntrenamiento.objects.filter(SocioMembresiaID__SocioID=socio)
            .values_list("FechaInicio", flat=True)
        )
        fechas_converted = set([f.date() for f in fechas if f is not None])
        if not fechas_converted:
            return 0, None

        streak = 0
        dia = hoy
        while dia in fechas_converted:
            streak += 1
            dia = dia - datetime.timedelta(days=1)

        ultima = max(fechas_converted)
        return streak, ultima

    streaks = []
    for s in socios_with_sessions:
        st, last = compute_current_streak(s)
        if st > 0:
            streaks.append({"socio": s, "streak": st, "last_date": last})

    # ordenar y cortar top 5
    top_n = 5
    top_rachas = sorted(streaks, key=lambda x: (x["streak"], x["last_date"]), reverse=True)[:top_n]
    context["top_rachas"] = top_rachas
    # Agregar nombre del entrenador al contexto si está disponible en sesión
    entrenador_nombre = None
    usuario_id = request.session.get("usuario_id")
    if usuario_id:
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            entrenador_nombre = getattr(usuario, 'NombreUsuario', None) or getattr(usuario, 'Email', None)
        except Usuario.DoesNotExist:
            entrenador_nombre = None

    context['entrenador_nombre'] = entrenador_nombre or 'Entrenador'
    # Notificaciones: sesiones completadas recientemente (última hora)
    try:
        from django.utils import timezone as dj_timezone
        ahora = dj_timezone.now()
        window = ahora - dj_timezone.timedelta(minutes=60)
        recientes_qs = (
            SesionEntrenamiento.objects.filter(FechaFin__isnull=False, FechaFin__gte=window)
            .order_by("-FechaFin")[:8]
        )
        recent_completions = []
        for s in recientes_qs:
            socio_nombre = None
            try:
                socio_nombre = s.SocioMembresiaID.SocioID.NombreCompleto
            except Exception:
                socio_nombre = str(s.SocioMembresiaID_id)

            rutina_nombre = None
            try:
                rutina_nombre = s.RutinaID.Nombre if s.RutinaID else ("Sesión libre" if s.EsEntrenamientoLibre else "Rutina")
            except Exception:
                rutina_nombre = "Rutina"

            recent_completions.append({
                "nombre": socio_nombre,
                "rutina": rutina_nombre,
                "fecha": s.FechaFin,
            })

        context["recent_completions"] = recent_completions
    except Exception:
        context["recent_completions"] = []
    return render(request, "Entrenador/PaneldeInicio.html", context)


@login_requerido
def entrenador_nutricion_view(request):
    """Listado de planes nutricionales por socio y acción para asignarlos."""
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    if request.method == "POST":
        socio_id = request.POST.get("socio_id")
        plantilla_value = request.POST.get("plantilla")
        objetivo = request.POST.get("objetivo_calorico")
        try:
            socio = Socio.objects.get(id=socio_id)
        except Socio.DoesNotExist:
            messages.error(request, "El socio seleccionado no existe.")
            return redirect("entrenador_nutricion")

        try:
            objetivo_valor = int(objetivo) if objetivo else None
        except (TypeError, ValueError):
            messages.error(request, "El objetivo calórico debe ser un número válido.")
            return redirect("entrenador_nutricion")

        if not plantilla_value:
            messages.error(request, "Selecciona una plantilla.")
            return redirect("entrenador_nutricion")

        try:
            if plantilla_value.startswith("db:"):
                plantilla_id = int(plantilla_value.split(":", 1)[1])
                plantilla_db = PlanNutricional.objects.filter(
                    id=plantilla_id, EsPlantilla=True, SocioID__isnull=True
                ).first()
                if not plantilla_db:
                    raise ValueError("La plantilla seleccionada no existe.")
                aplicar_plan_desde_template_db(plantilla_db, socio, objetivo_valor)
            else:
                slug = plantilla_value.split(":", 1)[-1]
                asignar_plan_desde_plantilla(socio, slug, objetivo_valor)
            messages.success(
                request,
                f"Plan nutricional asignado a {socio.NombreCompleto}.",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("entrenador_nutricion")

    socios = Socio.objects.all().order_by("NombreCompleto")
    planes = (
        PlanNutricional.objects.filter(SocioID__in=socios, EsPlantilla=False)
        .prefetch_related("dias_comida")
    )
    planes_map = {plan.SocioID_id: plan for plan in planes}

    dia_actual = timezone.localdate().weekday()
    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    dia_actual_nombre = dias_semana[dia_actual]

    socios_data = []
    for socio in socios:
        plan = planes_map.get(socio.id)
        comida_preview = []
        comidas_por_dia = 0
        objetivo = None

        if plan:
            objetivo = plan.ObjetivoCaloricoDiario
            dias_comida = list(plan.dias_comida.all())
            dia_comidas = [d for d in dias_comida if d.DiaSemana == dia_actual]
            if not dia_comidas:
                dia_comidas = [d for d in dias_comida if d.DiaSemana == 0]
            comidas_por_dia = len(dia_comidas)
            comida_preview = [d.TipoComida or "Comida" for d in dia_comidas][:4]

        socios_data.append(
            {
                "socio": socio,
                "plan": plan,
                "objetivo": objetivo,
                "comidas_por_dia": comidas_por_dia,
                "comida_preview": comida_preview,
            }
        )

    plantillas_db = PlanNutricional.objects.filter(
        EsPlantilla=True, SocioID__isnull=True
    ).order_by("Nombre")

    alimentos_catalogo = Alimento.objects.all().order_by("Nombre")

    context = {
        "socios_data": socios_data,
        "plantillas": get_nutrition_templates(),
        "dia_actual_nombre": dia_actual_nombre,
        "plantillas_db": plantillas_db,
        "alimentos_catalogo": alimentos_catalogo,
    }
    return render(request, "Entrenador/NutricionList.html", context)


@login_requerido
def entrenador_plan_nutricion_detalle(request, socio_id):
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    socio = get_object_or_404(Socio, id=socio_id)
    plan = (
        PlanNutricional.objects.filter(SocioID=socio, EsPlantilla=False)
        .prefetch_related("dias_comida__alimentos__AlimentoID")
        .first()
    )
    if not plan:
        messages.info(request, "Este socio aún no tiene un plan nutricional asignado.")
        return redirect("entrenador_nutricion")

    dias_semana = [
        {"indice": 0, "nombre": "Lunes", "comidas": []},
        {"indice": 1, "nombre": "Martes", "comidas": []},
        {"indice": 2, "nombre": "Miércoles", "comidas": []},
        {"indice": 3, "nombre": "Jueves", "comidas": []},
        {"indice": 4, "nombre": "Viernes", "comidas": []},
        {"indice": 5, "nombre": "Sábado", "comidas": []},
        {"indice": 6, "nombre": "Domingo", "comidas": []},
    ]

    for dia_comida in plan.dias_comida.all().order_by("DiaSemana", "id"):
        dia_info = dias_semana[dia_comida.DiaSemana]
        alimentos = []
        for alimento_rel in dia_comida.alimentos.all():
            alimento = alimento_rel.AlimentoID
            porcion = alimento_rel.Porcion
            porcion_display = f"{porcion.normalize()} g" if porcion else ""
            calorias = 0
            if alimento.Kcal:
                ratio = float(porcion or 100) / 100.0
                calorias = int(float(alimento.Kcal) * ratio)
            alimentos.append(
                {
                    "obj": alimento_rel,
                    "nombre": alimento.Nombre,
                    "porcion": porcion_display,
                    "porcion_valor": porcion,
                    "calorias": calorias,
                    "macros": alimento.Macros,
                }
            )
        dia_info["comidas"].append(
            {
                "obj": dia_comida,
                "tipo": dia_comida.TipoComida or "Comida",
                "alimentos": alimentos,
            }
        )

    context = {
        "socio": socio,
        "plan": plan,
        "dias": dias_semana,
        "alimentos_catalogo": Alimento.objects.all().order_by("Nombre"),
        "es_template": False,
    }
    return render(request, "Entrenador/NutricionDetalle.html", context)


@login_requerido
def entrenador_plantilla_nutricion_detalle(request, plan_id):
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    plan = get_object_or_404(
        PlanNutricional,
        id=plan_id,
        EsPlantilla=True,
        SocioID__isnull=True,
    )

    dias_semana = [
        {"indice": 0, "nombre": "Lunes", "comidas": []},
        {"indice": 1, "nombre": "Martes", "comidas": []},
        {"indice": 2, "nombre": "Miércoles", "comidas": []},
        {"indice": 3, "nombre": "Jueves", "comidas": []},
        {"indice": 4, "nombre": "Viernes", "comidas": []},
        {"indice": 5, "nombre": "Sábado", "comidas": []},
        {"indice": 6, "nombre": "Domingo", "comidas": []},
    ]

    for dia_comida in plan.dias_comida.all().order_by("DiaSemana", "id"):
        dia_info = dias_semana[dia_comida.DiaSemana]
        alimentos = []
        for alimento_rel in dia_comida.alimentos.all():
            alimento = alimento_rel.AlimentoID
            porcion = alimento_rel.Porcion
            porcion_display = f"{porcion.normalize()} g" if porcion else ""
            calorias = 0
            if alimento.Kcal:
                ratio = float(porcion or 100) / 100.0
                calorias = int(float(alimento.Kcal) * ratio)
            alimentos.append(
                {
                    "obj": alimento_rel,
                    "nombre": alimento.Nombre,
                    "porcion": porcion_display,
                    "porcion_valor": porcion,
                    "calorias": calorias,
                    "macros": alimento.Macros,
                }
            )
        dia_info["comidas"].append(
            {
                "obj": dia_comida,
                "tipo": dia_comida.TipoComida or "Comida",
                "alimentos": alimentos,
            }
        )

    context = {
        "socio": None,
        "plan": plan,
        "dias": dias_semana,
        "alimentos_catalogo": Alimento.objects.all().order_by("Nombre"),
        "es_template": True,
    }
    return render(request, "Entrenador/NutricionDetalle.html", context)


@login_requerido
@require_POST
def entrenador_crear_plantilla_nutricional(request):
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("login")

    nombre = (request.POST.get("nombre") or "Plantilla sin nombre").strip()
    objetivo_raw = request.POST.get("objetivo_calorico")
    objetivo = None
    if objetivo_raw:
        try:
            objetivo = int(objetivo_raw)
        except (TypeError, ValueError):
            objetivo = None

    plan = PlanNutricional.objects.create(
        Nombre=nombre,
        ObjetivoCaloricoDiario=objetivo,
        EsPlantilla=True,
    )
    messages.success(request, f"Plantilla '{plan.Nombre}' creada.")
    return redirect("entrenador_plantilla_nutricion", plan_id=plan.id)


@login_requerido
def entrenador_crear_plan_manual(request, socio_id):
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return redirect("login")

    socio = get_object_or_404(Socio, id=socio_id)
    plan, created = PlanNutricional.objects.get_or_create(
        SocioID=socio,
        EsPlantilla=False,
    )
    if created:
        messages.success(request, f"Plan nutricional creado para {socio.NombreCompleto}.")
    return redirect("entrenador_plan_nutricion", socio_id=socio.id)


@login_requerido
@require_POST
def entrenador_nutricion_actualizar_plan(request, plan_id):
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return redirect("login")

    plan = get_object_or_404(PlanNutricional, id=plan_id)
    objetivo_raw = request.POST.get("objetivo_calorico")
    objetivo = None
    if objetivo_raw:
        try:
            objetivo = int(objetivo_raw)
        except (TypeError, ValueError):
            objetivo = plan.ObjetivoCaloricoDiario
    plan.ObjetivoCaloricoDiario = objetivo
    if plan.EsPlantilla:
        nombre = (request.POST.get("nombre") or "").strip()
        if nombre:
            plan.Nombre = nombre
    plan.save()
    messages.success(request, "Plan actualizado correctamente.")
    if plan.EsPlantilla:
        return redirect("entrenador_plantilla_nutricion", plan_id=plan.id)
    return redirect("entrenador_plan_nutricion", socio_id=plan.SocioID_id)


def _redirect_plan(plan):
    if plan.EsPlantilla:
        return redirect("entrenador_plantilla_nutricion", plan_id=plan.id)
    return redirect("entrenador_plan_nutricion", socio_id=plan.SocioID_id)


@login_requerido
@require_POST
def entrenador_nutricion_agregar_comida(request, plan_id):
    plan = get_object_or_404(PlanNutricional, id=plan_id)
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return _redirect_plan(plan)

    try:
        dia = int(request.POST.get("dia", 0))
    except (TypeError, ValueError):
        dia = 0
    tipo = (request.POST.get("tipo") or "").strip() or "Comida"
    DiaComida.objects.create(
        PlanNutricionalID=plan,
        DiaSemana=max(0, min(6, dia)),
        TipoComida=tipo,
    )
    messages.success(request, "Comida agregada.")
    return _redirect_plan(plan)


@login_requerido
@require_POST
def entrenador_nutricion_eliminar_comida(request, dia_id):
    dia = get_object_or_404(DiaComida, id=dia_id)
    plan = dia.PlanNutricionalID
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return _redirect_plan(plan)

    dia.delete()
    messages.success(request, "Comida eliminada.")
    return _redirect_plan(plan)


@login_requerido
@require_POST
def entrenador_nutricion_agregar_alimento(request, dia_id):
    dia = get_object_or_404(DiaComida, id=dia_id)
    plan = dia.PlanNutricionalID
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return _redirect_plan(plan)

    alimento_id = request.POST.get("alimento_id")
    porcion_raw = request.POST.get("porcion")
    if not alimento_id:
        messages.error(request, "Selecciona un alimento.")
        return _redirect_plan(plan)
    alimento = get_object_or_404(Alimento, id=alimento_id)
    porcion = None
    if porcion_raw:
        try:
            porcion = Decimal(str(porcion_raw))
        except (ValueError, ArithmeticError):
            porcion = None
    ComidaAlimento.objects.create(
        DiaComidaID=dia,
        AlimentoID=alimento,
        Porcion=porcion,
    )
    messages.success(request, "Alimento agregado.")
    return _redirect_plan(plan)


def _resolve_next_url(request, fallback_name="entrenador_nutricion"):
    """Best-effort redirection target limited to rutas internas."""
    allowed_hosts = {request.get_host()} if hasattr(request, "get_host") else None
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts, request.is_secure()):
        return next_url
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts, request.is_secure()):
        return referer
    return reverse(fallback_name)


@login_requerido
@require_POST
def entrenador_nutricion_crear_alimento(request):
    rol = request.session.get("usuario_rol", "").lower()
    redirect_target = _resolve_next_url(request)
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return redirect(redirect_target)

    nombre = (request.POST.get("nombre") or "").strip()
    porcion_base = (request.POST.get("porcion_base") or "").strip() or None
    kcal_raw = request.POST.get("kcal")
    macros = (request.POST.get("macros") or "").strip() or None

    if not nombre:
        messages.error(request, "El nombre del alimento es obligatorio.")
        return redirect(redirect_target)

    if Alimento.objects.filter(Nombre__iexact=nombre).exists():
        messages.error(
            request,
            "Ya existe un alimento con ese nombre. Usa otro o selecciona el existente.",
        )
        return redirect(redirect_target)

    kcal = None
    if kcal_raw not in (None, ""):
        try:
            kcal = int(kcal_raw)
            if kcal < 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Las calorías deben ser un número entero positivo.")
            return redirect(redirect_target)

    Alimento.objects.create(
        Nombre=nombre,
        PorcionBase=porcion_base,
        Kcal=kcal,
        Macros=macros,
    )
    messages.success(request, "Alimento personalizado creado y disponible en el catálogo.")
    return redirect(redirect_target)


@login_requerido
@require_POST
def entrenador_nutricion_actualizar_alimento(request, item_id):
    item = get_object_or_404(ComidaAlimento, id=item_id)
    plan = item.DiaComidaID.PlanNutricionalID
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return _redirect_plan(plan)

    porcion_raw = request.POST.get("porcion")
    if porcion_raw in (None, ""):
        item.Porcion = None
    else:
        try:
            item.Porcion = Decimal(str(porcion_raw))
        except (ArithmeticError, ValueError):
            messages.error(request, "Porción inválida.")
            return _redirect_plan(plan)
    item.save()
    messages.success(request, "Alimento actualizado.")
    return _redirect_plan(plan)


@login_requerido
@require_POST
def entrenador_nutricion_eliminar_alimento(request, item_id):
    item = get_object_or_404(ComidaAlimento, id=item_id)
    plan = item.DiaComidaID.PlanNutricionalID
    rol = request.session.get("usuario_rol", "").lower()
    if rol not in ("entrenador", "administrativo"):
        messages.error(request, "No tienes permisos para esta acción.")
        return _redirect_plan(plan)

    item.delete()
    messages.success(request, "Alimento eliminado.")
    return _redirect_plan(plan)


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
        # si el entrenador pulsó en guardar en banco, marcamos la rutina como plantilla
        guardar_en_banco = True if request.POST.get("guardar_en_banco") else False

        try:
            rutina = crear_rutina_semanal(
                socio_id=(None if guardar_en_banco else socio_id),
                nombre=nombre,
                dias_entrenamiento=dias,
                es_plantilla=bool(guardar_en_banco)
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
        added = 0
        failed = []
        if ejercicios_temp_json:
            try:
                ejercicios_temp = json.loads(ejercicios_temp_json)
            except Exception:
                ejercicios_temp = []

            for idx, item in enumerate(ejercicios_temp, start=1):
                ejercicio_id = item.get("ejercicio_id") or item.get("id")
                dia_raw = item.get("dia") if item.get("dia") is not None else item.get("DiaSemana")
                try:
                    asignar_ejercicio_a_rutina(
                        rutina_id=rutina.id,
                        ejercicio_id=ejercicio_id,
                        dia_semana=int(dia_raw),
                        series=int(item.get("series")) if item.get("series") is not None else None,
                        repeticiones=int(item.get("reps") or item.get("repeticiones")) if (item.get("reps") or item.get("repeticiones")) else None,
                        tempo=item.get("tempo") or item.get("Tempo") or "",
                        peso_objetivo=float(item.get("peso")) if item.get("peso") is not None and item.get("peso") != "" else None,
                    )
                    added += 1
                except ValidationError as ve:
                    failed.append(f"item #{idx}: {ve}")
                except Exception as e:
                    failed.append(f"item #{idx}: {str(e)}")

    # Informar al entrenador cuántos ejercicios temporales se agregaron (si los hubo)
        if added > 0:
            messages.success(request, f"Se agregaron {added} ejercicio(s) a la rutina.")
        if failed:
            for f in failed:
                messages.warning(request, f"No se pudo agregar ejercicio temporal: {f}")

        # Mensaje de confirmación incluyendo el nombre del socio (siempre mostrar)
        try:
            socio_nombre = rutina.SocioID.NombreCompleto if hasattr(rutina.SocioID, 'NombreCompleto') else str(rutina.SocioID)
        except Exception:
            socio_nombre = str(rutina.SocioID_id)
        # Si guardamos como plantilla, redirigimos al banco de rutinas para que el entrenador la vea
        if guardar_en_banco:
            messages.success(request, f"Plantilla '{rutina.Nombre}' guardada en el banco de rutinas.")
            return redirect('rutinas_banco')

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
    # Nota: NO borramos rutinas vacías automáticamente al listar.
    # Antes borrábamos rutinas sin ejercicios en este punto, pero eso causaba que
    # rutinas recién creadas (por ejemplo, si el guardado de ejercicios falló) se
    # eliminaran silenciosamente y el entrenador pensara que la rutina "no existe".
    # Mantener la eliminación automática es peligroso; la limpieza debe hacerse
    # explícitamente (por ejemplo, un cron job o acción administrativa).

    # Re-consultar rutinas limpias para renderizar
    rutinas = RutinaSemanal.objects.select_related('SocioID').prefetch_related('dias_ejercicios__EjercicioID').all()

    return render(request, 'Entrenador/RutinasList.html', {
        'rutinas': rutinas,
    })


@login_requerido
def rutinas_banco_view(request):
    """Lista las rutinas plantillas (banco de rutinas) que un entrenador puede asignar a socios."""
    # Plantillas marcadas como EsPlantilla=True
    plantillas = RutinaSemanal.objects.filter(EsPlantilla=True).prefetch_related('SocioID')
    socios = Socio.objects.all().order_by('NombreCompleto')

    return render(request, 'Entrenador/RutinasBanco.html', {
        'plantillas': plantillas,
        'socios': socios,
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
