import json

# FUNCIÓN DE REGISTRO PÚBLICO DESHABILITADA
# Los socios ahora se crean desde el panel de administración
# def register_view(request):
#     if request.method == "POST":
#         identificacion = request.POST.get("identificacion", "").strip()
#         full_name = request.POST.get("full_name", "").strip()
#         phone = request.POST.get("phone", "").strip()
#         email = request.POST.get("email", "").strip()
#         birthdate = request.POST.get("birthdate", "").strip()
#         consent_raw = request.POST.get("consent")
#         consent = True if consent_raw is not None else False
#         password = request.POST.get("password", "")
#         confirm_password = request.POST.get("confirm_password", "")
#         health_status = request.POST.get("health_status", "").strip()
#         follow_up_note = request.POST.get("follow_up_note", "").strip()
#
#         if password != confirm_password:
#             messages.error(request, "Las contraseñas no coinciden.")
#             return render(request, "socio/register.html", request.POST)
#
#         if not consent:
#             messages.error(request, "Debes aceptar el tratamiento de datos personales.")
#             return render(request, "socio/register.html", request.POST)
#
#         data = {
#             "identificacion": identificacion,
#             "full_name": full_name,
#             "phone": phone,
#             "email": email,
#             "birthdate": birthdate,
#             "consent": consent,
#             "password": password,
#             "health_status": health_status,
#             "follow_up_note": follow_up_note,
#         }
#
#         try:
#             socio = create_socio_from_dict(data)
#             crear_usuario_para_socio(socio, password)
#             messages.success(
#                 request, "Cuenta creada correctamente. Puedes iniciar sesión."
#             )
#             return redirect("login")
#
#         except ValidationError as e:
#             messages.error(request, str(e))
#             return render(request, "socio/register.html", request.POST)
#
#         except IntegrityError:
#             messages.error(
#                 request, "Ya existe un socio con esa identificación o correo."
#             )
#             return render(request, "socio/register.html", request.POST)
#
#         except Exception as e:
#             messages.error(request, f"Ocurrió un error inesperado: {str(e)}")
#             return render(request, "socio/register.html", request.POST)
#
#     return render(request, "socio/register.html")
# Interfaz Inicio (beta)
from datetime import datetime

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.control_acceso.models import (
    Asistencia,
    CompletionTracking,
    DiaComida,
    DiaRutinaEjercicio,
    Ejercicio,
    EjercicioSesionCompletado,
    PlanNutricional,
    RutinaSemanal,
    SesionEntrenamiento,
)
from apps.pagos.models import AlertaPago, Pago, PlanMembresia, SocioMembresia
from apps.seguridad.decoradores import login_requerido
from apps.seguridad.models import Usuario
from apps.seguridad.servicios.registro_usuario import crear_usuario_para_socio
from apps.socios.forms import PerfilSocioForm
from apps.socios.models import Medicion, Socio
from apps.socios.servicios.rutinas import obtener_o_crear_rutina_base

from .models import Medicion, RegistroComidaDiaria, Socio
from .servicios.registro_db import ValidationError, create_socio_from_dict

# ... (keep existing imports and register_view)


@login_requerido
def panel_de_control_view(request):
    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        # Asumimos que el email es el vínculo entre Usuario y Socio
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    # --- Estadísticas ---
    # 1. Racha (Consecutive training days with 1-day grace period)
    membresias = SocioMembresia.objects.filter(SocioID=socio)

    # Get all completed sessions ordered by date (newest first)
    sesiones_completadas = (
        SesionEntrenamiento.objects.filter(
            SocioMembresiaID__in=membresias, FechaFin__isnull=False
        )
        .order_by("-FechaInicio")
        .values_list("FechaInicio", flat=True)
    )

    # Calculate streak
    racha_dias = 0
    racha_en_peligro = False
    mensaje_racha = ""

    if sesiones_completadas:
        hoy = timezone.now().date()
        dias_unicos = set(dt.date() for dt in sesiones_completadas)
        dias_unicos = sorted(dias_unicos, reverse=True)

        entreno_hoy = hoy in dias_unicos
        ayer = hoy - timezone.timedelta(days=1)
        entreno_ayer = ayer in dias_unicos
        es_fin_de_semana = hoy.weekday() in [5, 6]

        ultimo_dia_entreno = dias_unicos[0] if dias_unicos else None
        weekend_gap = False
        if not entreno_hoy and not entreno_ayer and ultimo_dia_entreno:
            dias_desde_ultimo = (hoy - ultimo_dia_entreno).days
            if dias_desde_ultimo > 1:
                dias_intermedios = [
                    ultimo_dia_entreno + timezone.timedelta(days=i)
                    for i in range(1, dias_desde_ultimo + 1)
                ]
                if dias_intermedios:
                    dias_previos = dias_intermedios[:-1]
                    if dias_previos and all(
                        d.weekday() in [5, 6] for d in dias_previos
                    ):
                        weekend_gap = True

        fecha_actual = None
        if entreno_hoy:
            fecha_actual = hoy
        elif entreno_ayer:
            fecha_actual = ayer
        elif weekend_gap and ultimo_dia_entreno:
            fecha_actual = ultimo_dia_entreno

        if fecha_actual:
            racha_dias = 1
            dias_sin_entrenar = 0

            for i in range(1, 365):
                fecha_anterior = fecha_actual - timezone.timedelta(days=i)
                dia_semana = fecha_anterior.weekday()

                if fecha_anterior in dias_unicos:
                    racha_dias += 1
                    dias_sin_entrenar = 0
                else:
                    if dia_semana not in [5, 6]:
                        dias_sin_entrenar += 1
                        if dias_sin_entrenar > 1:
                            break

            if entreno_hoy:
                mensaje_racha = f"¡Genial! Llevas {racha_dias} {'día' if racha_dias == 1 else 'días'} seguidos"
            elif entreno_ayer:
                if es_fin_de_semana:
                    mensaje_racha = f"🌴 Es fin de semana, está bien si descansas :) No perderás tu racha de {racha_dias} días"
                else:
                    racha_en_peligro = True
                    mensaje_racha = (
                        f"⚠️ ¡Si hoy no entrenas perderás tu racha de {racha_dias} días!"
                    )
            elif weekend_gap:
                racha_en_peligro = True
                mensaje_racha = f"⚠️ Tu racha de {racha_dias} días sigue tras el fin de semana. Retoma hoy para mantenerla."
            elif es_fin_de_semana:
                mensaje_racha = f"🌴 Es fin de semana, está bien si descansas :) Tienes {racha_dias} {'día' if racha_dias == 1 else 'días'} de racha"
        else:
            mensaje_racha = "Comienza tu racha entrenando hoy"
    else:
        mensaje_racha = "Comienza tu racha entrenando hoy"

    # 2. Peso Actual
    ultima_medicion = Medicion.objects.filter(SocioID=socio).order_by("-Fecha").first()
    peso_actual = ultima_medicion.PesoCorporal if ultima_medicion else 0
    fecha_peso = ultima_medicion.Fecha if ultima_medicion else None

    # 3. IMC (Índice de Masa Corporal)
    imc_actual = 0
    estado_imc = "Desconocido"
    if socio.Altura and peso_actual:
        altura_m = float(socio.Altura)
        peso_kg = float(peso_actual)
        if altura_m > 0:
            imc_actual = round(peso_kg / (altura_m**2), 1)

            if imc_actual < 18.5:
                estado_imc = "Bajo peso"
            elif 18.5 <= imc_actual < 25:
                estado_imc = "Peso normal"
            elif 25 <= imc_actual < 30:
                estado_imc = "Sobrepeso"
            else:
                estado_imc = "Obesidad"

    # --- Gráfica de Peso e IMC (Últimos 30 días) ---
    historial_peso = Medicion.objects.filter(SocioID=socio).order_by("Fecha")[:30]

    # Preparar datos para Chart.js
    import json

    chart_labels = []
    chart_peso = []
    chart_imc = []

    for medicion in historial_peso:
        chart_labels.append(medicion.Fecha.strftime("%d %b"))
        chart_peso.append(float(medicion.PesoCorporal) if medicion.PesoCorporal else 0)

        # Calcular IMC para cada medición
        if socio.Altura and medicion.PesoCorporal:
            altura_m = float(socio.Altura)
            peso_kg = float(medicion.PesoCorporal)
            imc = round(peso_kg / (altura_m**2), 1) if altura_m > 0 else 0
            chart_imc.append(imc)
        else:
            chart_imc.append(0)

    chart_data = {"labels": chart_labels, "peso": chart_peso, "imc": chart_imc}

    # Calcular tendencia de peso (comparar últimas 2 mediciones)
    tendencia_peso = "estable"
    mensaje_peso = "Mantén tu rutina"
    ultimas_2 = Medicion.objects.filter(SocioID=socio).order_by("-Fecha")[:2]

    if len(ultimas_2) == 2:
        peso_anterior = float(ultimas_2[1].PesoCorporal)
        peso_reciente = float(ultimas_2[0].PesoCorporal)
        diferencia = peso_reciente - peso_anterior

        if abs(diferencia) < 0.5:
            tendencia_peso = "estable"
        elif diferencia > 0:
            tendencia_peso = "subiendo"
        else:
            tendencia_peso = "bajando"

        # Mensaje contextual según IMC y tendencia
        if estado_imc == "Bajo peso":
            if tendencia_peso == "bajando":
                mensaje_peso = "⚠️ Considera ganar peso saludablemente"
            elif tendencia_peso == "subiendo":
                mensaje_peso = "¡Excelente! Progreso positivo"
            else:
                mensaje_peso = "Mantén una nutrición balanceada"
        elif estado_imc == "Peso normal":
            if tendencia_peso == "bajando":
                mensaje_peso = "Cuidado, no bajes demasiado"
            elif tendencia_peso == "subiendo":
                mensaje_peso = "Vigila tu progreso"
            else:
                mensaje_peso = "¡Perfecto! Peso estable"
        elif estado_imc in ["Sobrepeso", "Obesidad"]:
            if tendencia_peso == "bajando":
                mensaje_peso = "¡Excelente progreso! Sigue así"
            elif tendencia_peso == "subiendo":
                mensaje_peso = "⚠️ Ajusta tu rutina y dieta"
            else:
                mensaje_peso = "Mantén el esfuerzo constante"

    # --- Rutina de Hoy ---
    dia_semana_actual = datetime.now().weekday()  # 0=Lunes
    rutina_hoy = []
    rutina_obj = RutinaSemanal.objects.filter(SocioID=socio).first()
    if rutina_obj:
        rutina_hoy = DiaRutinaEjercicio.objects.filter(
            RutinaID=rutina_obj, DiaSemana=dia_semana_actual
        ).select_related("EjercicioID")

    # --- Plan Nutricional de Hoy ---
    plan_nutricional_hoy = []
    plan_nutri_obj = PlanNutricional.objects.filter(SocioID=socio).first()
    if plan_nutri_obj:
        dias_comida = DiaComida.objects.filter(
            PlanNutricionalID=plan_nutri_obj, DiaSemana=dia_semana_actual
        ).prefetch_related("alimentos__AlimentoID")
        plan_nutricional_hoy = dias_comida

    # --- Notificaciones ---
    notificaciones = AlertaPago.objects.filter(
        SocioMembresiaID__in=membresias, VistaEnPanel=False
    )

    context = {
        "socio": socio,
        "racha_dias": racha_dias,
        "racha_en_peligro": racha_en_peligro,
        "peso_actual": peso_actual,
        "fecha_peso": fecha_peso,
        "imc_actual": imc_actual,
        "estado_imc": estado_imc,
        "mensaje_peso": mensaje_peso,
        "mensaje_racha": mensaje_racha,
        "rutina_hoy": rutina_hoy,
        "plan_nutricional_hoy": plan_nutricional_hoy,
        "notificaciones": notificaciones,
        "historial_peso": historial_peso,
        "chart_data_json": json.dumps(chart_data),
    }

    return render(request, "socio/PanelDeControl.html", context)


@login_requerido
def clientes_list_view(request):
    """Lista de clientes para entrenadores/administrativos con tarjeta resumen.

    Muestra peso (última medición), IMC (si está), restricciones médicas (SaludBasica),
    y datos de contacto.
    """
    # Traer todos los socios y su última medición
    socios = Socio.objects.all().order_by('NombreCompleto')
    resultados = []
    for s in socios:
        ultima = Medicion.objects.filter(SocioID=s).order_by('-Fecha').first()
        peso = None
        imc = None
        fecha_med = None
        if ultima and ultima.PesoCorporal is not None:
            peso = float(ultima.PesoCorporal)
            fecha_med = ultima.Fecha
            try:
                if s.Altura:
                    altura = float(s.Altura)
                    if altura > 0:
                        imc = round(peso / (altura * altura), 1)
            except Exception:
                imc = None

        # Indicar si el socio ya tiene alguna rutina (esto se usa para el botón "Ver rutina"
        # y evitar navegaciones innecesarias si no existe rutina).
        try:
            has_rutina = RutinaSemanal.objects.filter(SocioID=s).exists()
        except Exception:
            has_rutina = False

        resultados.append({
            'socio': s,
            'peso': peso,
            'imc': imc,
            'fecha_medicion': fecha_med,
            'restricciones': s.SaludBasica,
            'telefono': s.Telefono,
            'email': s.Email,
            'has_rutina': has_rutina,
        })

    return render(request, 'Entrenador/ClientesList.html', {'resultados': resultados})


@login_requerido
def mi_rutina_view(request):
    from apps.control_acceso.models import (
        EjercicioSesionCompletado,
        SesionEntrenamiento,
    )

    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    # Obtener todas las rutinas del socio
    rutinas_qs = RutinaSemanal.objects.filter(SocioID=socio).prefetch_related(
        "dias_ejercicios__EjercicioID"
    )

    rutina_id = request.GET.get("rutina_id")
    rutina_activa = None
    es_modo_libre = False

    ultima_rutina_id = request.session.get("ultima_rutina_id")
    modo_libre_guardado = request.session.get("modo_libre_activo", False)

    if rutina_id == "free":
        es_modo_libre = True
        request.session["modo_libre_activo"] = True
        request.session.pop("ultima_rutina_id", None)
    elif rutina_id:
        rutina_activa = rutinas_qs.filter(id=rutina_id).first()
        if rutina_activa:
            request.session["ultima_rutina_id"] = rutina_activa.id
            request.session["modo_libre_activo"] = False
    elif modo_libre_guardado:
        es_modo_libre = True
    elif ultima_rutina_id:
        rutina_activa = rutinas_qs.filter(id=ultima_rutina_id).first()

    if not rutina_activa and not es_modo_libre:
        rutina_activa = (
            rutinas_qs.filter(EsPlantilla=False).first() or rutinas_qs.first()
        )
        if rutina_activa:
            request.session["ultima_rutina_id"] = rutina_activa.id
            request.session["modo_libre_activo"] = False
    elif es_modo_libre:
        request.session["modo_libre_activo"] = True
        request.session.pop("ultima_rutina_id", None)

    rutinas = list(rutinas_qs)

    # Convert query to list and add selected attribute for template
    for r in rutinas:
        r.selected_attr = "selected" if r == rutina_activa else ""
        r.icon_name = "check_circle" if r == rutina_activa else "arrow_forward_ios"

    membresias = SocioMembresia.objects.filter(SocioID=socio)
    sesion_activa = (
        SesionEntrenamiento.objects.filter(
            SocioMembresiaID__in=membresias, FechaFin__isnull=True
        )
        .select_related("RutinaID")
        .first()
    )

    if sesion_activa:
        if sesion_activa.EsEntrenamientoLibre or not sesion_activa.RutinaID:
            es_modo_libre = True
            rutina_activa = None
            request.session["modo_libre_activo"] = True
            request.session.pop("ultima_rutina_id", None)
        else:
            rutina_activa = sesion_activa.RutinaID
            es_modo_libre = False
            request.session["ultima_rutina_id"] = rutina_activa.id
            request.session["modo_libre_activo"] = False

    # Obtener ejercicios SOLO del día actual
    ejercicios_hoy = []
    dia_actual = datetime.now().weekday()
    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    dia_nombre = dias_semana[dia_actual]

    if rutina_activa:
        ejercicios_hoy = list(
            rutina_activa.dias_ejercicios.filter(DiaSemana=dia_actual).select_related(
                "EjercicioID"
            )
        )

    # Verificar si ya completó la rutina de hoy
    ya_completado_hoy = False
    if rutina_activa:
        semana_actual = datetime.now().strftime("%Y-%W")
        ya_completado_hoy = CompletionTracking.objects.filter(
            SocioMembresiaID__in=membresias,
            RutinaID=rutina_activa,
            Semana=semana_actual,
            DiaSemana=dia_actual,
            Completado=True,
        ).exists()

    # Obtener ejercicios completados en la sesión activa
    ejercicios_completados_ids = []
    if sesion_activa:
        ejercicios_completados_ids = list(
            sesion_activa.ejercicios_completados.filter(Completado=True).values_list(
                "DiaRutinaEjercicioID", flat=True
            )
        )

    # Add is_completed attribute to each exercise
    for ejercicio in ejercicios_hoy:
        ejercicio.is_completed = ejercicio.id in ejercicios_completados_ids
        ejercicio.can_check = sesion_activa is not None
        # Pre-calculate peso display
        if ejercicio.PesoObjetivo:
            ejercicio.peso_display = f"{ejercicio.PesoObjetivo} kg"
        else:
            ejercicio.peso_display = "-"

        # Pre-render checkbox HTML
        if ejercicio.can_check:
            checked = "checked" if ejercicio.is_completed else ""
            ejercicio.checkbox_html = (
                f'<input class="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer" '
                f'type="checkbox" data-ejercicio-id="{ejercicio.id}" data-initial-state="{checked}" {checked} '
                f'onchange="toggleEjercicio(this)" />'
            )
        else:
            ejercicio.checkbox_html = '<input class="h-5 w-5 rounded border-gray-300 text-gray-400 cursor-not-allowed" type="checkbox" disabled />'

    # Historial de sesiones (limit to 3)
    historial_sesiones = (
        SesionEntrenamiento.objects.filter(
            SocioMembresiaID__in=membresias, FechaFin__isnull=False
        )
        .select_related("RutinaID")
        .order_by("-FechaInicio")[:3]
    )

    # Pre-calculate display name to avoid template formatting issues
    historial_sesiones = list(historial_sesiones)
    for s in historial_sesiones:
        if s.EsEntrenamientoLibre:
            s.nombre_display = "Entrenamiento Libre"
        elif s.RutinaID:
            s.nombre_display = s.RutinaID.Nombre
        else:
            s.nombre_display = "Sesión sin nombre"

    context = {
        "socio": socio,
        "rutinas": rutinas,
        "rutina_activa": rutina_activa,
        "ejercicios_hoy": ejercicios_hoy,
        "dia_actual": dia_nombre,
        "sesion_activa": sesion_activa,
        "ya_completado_hoy": ya_completado_hoy,
        "historial_sesiones": historial_sesiones,
        "es_modo_libre": es_modo_libre,
    }

    return render(request, "socio/MiRutina.html", context)


#  ----------------- ENTRENADOR ---------------------


@login_requerido
def planel_inicio_entrenador_view(request):
    return render(request, "Entrenador/PaneldeInicio.html")


@login_requerido
def crear_rutina_entrenador_view(request):
    # Modificaciones en logica
    return render(request, "Entrenador/PlanificadorRutina.html")


@login_requerido
def panel_admin_view(request):
    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("login")

    rol = ""
    try:
        rol = (
            usuario.RolID.NombreRol.strip().lower()
            if usuario.RolID and usuario.RolID.NombreRol
            else ""
        )
    except Exception:
        rol = ""

    if rol != "administrativo":
        messages.error(
            request, "No tienes permisos para acceder al panel administrativo."
        )
        if rol == "entrenador":
            return redirect("entrenador_panel")
        if rol == "socio":
            return redirect("socio_panel")
        return redirect("login")

    return render(request, "Administrador/PaneldeInicio.html")


# === SESSION TRACKING VIEWS ===


@login_requerido
def iniciar_sesion_view(request):
    from django.http import JsonResponse

    from apps.control_acceso.models import (
        EjercicioSesionCompletado,
        SesionEntrenamiento,
    )

    if request.method == "POST":
        usuario_id = request.session.get("usuario_id")

        try:
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)

            # Check for free training mode
            entrenamiento_libre = request.POST.get("entrenamiento_libre") == "on"
            rutina_id = request.POST.get("rutina_id")

            # Get selected routine (or None for free training)
            rutina = None
            if not entrenamiento_libre:
                if rutina_id:
                    try:
                        rutina = RutinaSemanal.objects.get(id=rutina_id, SocioID=socio)
                    except RutinaSemanal.DoesNotExist:
                        messages.error(request, "Rutina no encontrada.")
                        return redirect("mi_rutina")
                else:
                    rutina = RutinaSemanal.objects.filter(
                        SocioID=socio, EsPlantilla=False
                    ).first()

                if not rutina:
                    messages.error(request, "No tienes una rutina asignada.")
                    return redirect("mi_rutina")

            # Verificar que no haya sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias, FechaFin__isnull=True
            ).first()

            if sesion_activa:
                messages.warning(request, "Ya tienes una sesión activa.")
                return redirect("mi_rutina")

            # Crear nueva sesión
            membresia = membresias.first()
            if not membresia:
                messages.error(request, "No tienes una membresía activa.")
                return redirect("mi_rutina")

            dia_semana = datetime.now().weekday()
            sesion = SesionEntrenamiento.objects.create(
                RutinaID=rutina,
                SocioMembresiaID=membresia,
                FechaInicio=timezone.now(),
                DiaSemana=dia_semana,
                EsEntrenamientoLibre=entrenamiento_libre,
            )

            # Crear registros de ejercicios solo si NO es entrenamiento libre
            if not entrenamiento_libre and rutina:
                ejercicios_dia = DiaRutinaEjercicio.objects.filter(
                    RutinaID=rutina, DiaSemana=dia_semana
                )

                for ejercicio in ejercicios_dia:
                    EjercicioSesionCompletado.objects.create(
                        SesionID=sesion,
                        DiaRutinaEjercicioID=ejercicio,
                        Completado=False,
                    )

            modo = "libre" if entrenamiento_libre else rutina.Nombre
            messages.success(request, f"¡Sesión iniciada ({modo})! Buena suerte.")
            return redirect("mi_rutina")

        except (Usuario.DoesNotExist, Socio.DoesNotExist):
            messages.error(request, "Error al iniciar sesión.")
            return redirect("mi_rutina")

    return redirect("mi_rutina")


@login_requerido
def detalle_sesion_view(request, sesion_id):
    """View to show details of a completed session"""
    from apps.control_acceso.models import SesionEntrenamiento

    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)

        # Get session and verify it belongs to this socio
        membresias = SocioMembresia.objects.filter(SocioID=socio)
        sesion = SesionEntrenamiento.objects.filter(
            id=sesion_id, SocioMembresiaID__in=membresias
        ).first()

        if not sesion:
            messages.error(request, "Sesión no encontrada.")
            return redirect("mi_rutina")

        # Get exercises for this session
        ejercicios = []
        completados_count = 0
        total_count = 0
        pendientes_count = 0

        if not sesion.EsEntrenamientoLibre:
            ejercicios = list(
                sesion.ejercicios_completados.all().select_related(
                    "DiaRutinaEjercicioID__EjercicioID"
                )
            )

            # Pre-calculate exercise names to avoid template formatting issues
            for ej in ejercicios:
                ej.nombre_ejercicio = ej.DiaRutinaEjercicioID.EjercicioID.Nombre
                series = ej.DiaRutinaEjercicioID.Series or "-"
                reps = ej.DiaRutinaEjercicioID.Repeticiones or "-"
                detalle = f"{series} series × {reps} reps"
                if ej.DiaRutinaEjercicioID.PesoObjetivo:
                    detalle += f" | {ej.DiaRutinaEjercicioID.PesoObjetivo} kg"
                ej.detalle_texto = detalle

            total_count = len(ejercicios)
            completados_count = sum(1 for ej in ejercicios if ej.Completado)
            pendientes_count = total_count - completados_count

        context = {
            "sesion": sesion,
            "ejercicios": ejercicios,
            "total_count": total_count,
            "completados_count": completados_count,
            "pendientes_count": pendientes_count,
        }

        return render(request, "socio/DetalleSesion.html", context)

    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "Error al cargar sesión.")
        return redirect("mi_rutina")


@login_requerido
def terminar_sesion_view(request):
    from django.http import JsonResponse

    from apps.control_acceso.models import SesionEntrenamiento

    if request.method == "POST":
        usuario_id = request.session.get("usuario_id")

        try:
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)

            # Buscar sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias, FechaFin__isnull=True
            ).first()

            if not sesion_activa:
                messages.warning(request, "No tienes una sesión activa.")
                return redirect("mi_rutina")

            # Save notes if provided
            notas = request.POST.get("notas", "").strip()
            if notas:
                sesion_activa.NotasSesion = notas

            # Terminar sesión
            sesion_activa.FechaFin = timezone.now()
            duracion = (
                sesion_activa.FechaFin - sesion_activa.FechaInicio
            ).total_seconds() / 60
            sesion_activa.DuracionMinutos = int(duracion)
            sesion_activa.save()

            # Check for weekly completion (only for non-free training)
            if not sesion_activa.EsEntrenamientoLibre and sesion_activa.RutinaID:
                from apps.control_acceso.models import CompletionTracking

                # Check if all exercises were completed
                total_ejercicios = sesion_activa.ejercicios_completados.count()
                ejercicios_completados = sesion_activa.ejercicios_completados.filter(
                    Completado=True
                ).count()

                if total_ejercicios > 0 and ejercicios_completados == total_ejercicios:
                    # Calculate current week (ISO week format: YYYY-WW)
                    now = timezone.now()
                    semana = now.strftime("%Y-%W")

                    # Create or update completion record
                    CompletionTracking.objects.update_or_create(
                        SocioMembresiaID=sesion_activa.SocioMembresiaID,
                        RutinaID=sesion_activa.RutinaID,
                        DiaSemana=sesion_activa.DiaSemana,
                        Semana=semana,
                        defaults={"Completado": True},
                    )

                    messages.success(
                        request,
                        f"🎉 ¡Sesión completada! Todos los ejercicios de hoy finalizados. Duración: {int(duracion)} min.",
                    )
                else:
                    messages.success(
                        request, f"Sesión terminada. Duración: {int(duracion)} minutos."
                    )
            else:
                messages.success(
                    request, f"Sesión terminada. Duración: {int(duracion)} minutos."
                )
            return redirect("mi_rutina")

        except (Usuario.DoesNotExist, Socio.DoesNotExist):
            messages.error(request, "Error al terminar sesión.")
            return redirect("mi_rutina")

    return redirect("mi_rutina")


@login_requerido
def toggle_ejercicio_view(request):
    import json

    from django.http import JsonResponse

    from apps.control_acceso.models import (
        EjercicioSesionCompletado,
        SesionEntrenamiento,
    )

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ejercicio_id = data.get("ejercicio_id")

            usuario_id = request.session.get("usuario_id")
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)

            # Buscar sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias, FechaFin__isnull=True
            ).first()

            if not sesion_activa:
                return JsonResponse({"error": "No hay sesión activa"}, status=400)

            # Toggle ejercicio
            ejercicio_sesion = EjercicioSesionCompletado.objects.get(
                SesionID=sesion_activa, DiaRutinaEjercicioID_id=ejercicio_id
            )

            ejercicio_sesion.Completado = not ejercicio_sesion.Completado
            ejercicio_sesion.save()

            # Verificar si todos están completados
            total = sesion_activa.ejercicios_completados.count()
            completados = sesion_activa.ejercicios_completados.filter(
                Completado=True
            ).count()

            respuesta = {
                "success": True,
                "completado": ejercicio_sesion.Completado,
                "progreso": f"{completados}/{total}",
                "todos_completados": completados == total,
            }

            # Terminar sesión automáticamente cuando todos los ejercicios se completan
            if completados == total and total > 0:
                sesion_activa.FechaFin = timezone.now()
                duracion = (
                    sesion_activa.FechaFin - sesion_activa.FechaInicio
                ).total_seconds() / 60
                sesion_activa.DuracionMinutos = int(duracion)
                sesion_activa.save()

                if not sesion_activa.EsEntrenamientoLibre and sesion_activa.RutinaID:
                    total_ejercicios = total
                    if total_ejercicios == completados:
                        semana = timezone.now().strftime("%Y-%W")
                        CompletionTracking.objects.update_or_create(
                            SocioMembresiaID=sesion_activa.SocioMembresiaID,
                            RutinaID=sesion_activa.RutinaID,
                            DiaSemana=sesion_activa.DiaSemana,
                            Semana=semana,
                            defaults={"Completado": True},
                        )

                respuesta["sesion_finalizada"] = True

            return JsonResponse(respuesta)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_requerido
def historial_sesiones_view(request):
    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    membresias = SocioMembresia.objects.filter(SocioID=socio)

    historial_sesiones = (
        SesionEntrenamiento.objects.filter(
            SocioMembresiaID__in=membresias, FechaFin__isnull=False
        )
        .select_related("RutinaID")
        .order_by("-FechaInicio")
    )

    # Pre-calculate display name
    historial_sesiones = list(historial_sesiones)
    for s in historial_sesiones:
        if s.EsEntrenamientoLibre:
            s.nombre_display = "Entrenamiento Libre"
        elif s.RutinaID:
            s.nombre_display = s.RutinaID.Nombre
        else:
            s.nombre_display = "Sesión sin nombre"

    context = {"historial_sesiones": historial_sesiones}
    return render(request, "socio/HistorialSesiones.html", context)


@login_requerido
def mi_nutricion_view(request):
    """View for nutrition page with daily meal plan"""
    import json

    from apps.control_acceso.models import (
        Alimento,
        ComidaAlimento,
        DiaComida,
        PlanNutricional,
    )

    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    # Get nutrition plan
    plan_nutricional = PlanNutricional.objects.filter(SocioID=socio).first()

    if not plan_nutricional:
        context = {
            "socio": socio,
            "tiene_plan": False,
        }
        return render(request, "socio/MiNutrición.html", context)

    # Get current day
    dia_actual = datetime.now().weekday()
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

    fecha_actual = timezone.localdate()

    # Get meals for today
    comidas_hoy = list(
        DiaComida.objects.filter(
            PlanNutricionalID=plan_nutricional, DiaSemana=dia_actual
        )
        .prefetch_related("alimentos__AlimentoID")
        .order_by("id")
    )

    registros_hoy = {
        registro.DiaComidaID_id: registro
        for registro in RegistroComidaDiaria.objects.filter(
            SocioID=socio,
            Fecha=fecha_actual,
            DiaComidaID__in=[c.id for c in comidas_hoy],
        )
    }

    boton_estilos = {
        True: {
            "icono": "task_alt",
            "texto": "Comida completada",
            "clase": "bg-green-50 text-green-700 border border-green-500",
        },
        False: {
            "icono": "check_circle",
            "texto": "Marcar como completado",
            "clase": "bg-primary text-white",
        },
    }

    # Pre-calculate totals
    calorias_total = 0
    proteinas_total = 0
    carbohidratos_total = 0
    grasas_total = 0

    # Pre-calculate meal data to avoid formatter issues
    for comida in comidas_hoy:
        comida.tipo_display = comida.TipoComida or "Comida"
        comida.alimentos_list = []

        for ca in comida.alimentos.all():
            alimento = ca.AlimentoID

            # Pre-calculate display name and quantity string
            cantidad_str = ""
            if ca.Porcion:
                cantidad_str = f"{int(ca.Porcion)}g"  # Assuming porcion is in grams
            elif ca.Cantidad:
                cantidad_str = f"{ca.Cantidad} un."

            ca.nombre_display = (
                f"{alimento.Nombre} ({cantidad_str})"
                if cantidad_str
                else alimento.Nombre
            )

            # Parse macros from TextField
            ca.calorias_valor = 0
            ca.proteinas_valor = 0
            ca.carbohidratos_valor = 0
            ca.grasas_valor = 0

            if alimento.Kcal:
                ca.calorias_valor = float(alimento.Kcal)

            if alimento.Macros:
                try:
                    macros_dict = {
                        p.split(":")[0].strip().upper(): float(
                            p.split(":")[1].replace("g", "").strip()
                        )
                        for p in alimento.Macros.split(",")
                        if ":" in p
                    }
                    ca.proteinas_valor = macros_dict.get("P", 0)
                    ca.carbohidratos_valor = macros_dict.get("C", 0)
                    ca.grasas_valor = macros_dict.get("G", 0)
                except (ValueError, IndexError):
                    pass  # Ignore parsing errors

            # Calculate totals based on portion
            porcion_ratio = float(ca.Porcion or 100) / 100.0
            ca.cal_total = int(ca.calorias_valor * porcion_ratio)
            ca.prot_total = round(ca.proteinas_valor * porcion_ratio, 1)
            ca.carb_total = round(ca.carbohidratos_valor * porcion_ratio, 1)
            ca.gras_total = round(ca.grasas_valor * porcion_ratio, 1)

            ca.macros_text = f"{ca.cal_total} kcal | P: {ca.prot_total}g, C: {ca.carb_total}g, G: {ca.gras_total}g"

            comida.alimentos_list.append(ca)

            # Sum totals
            calorias_total += ca.cal_total
            proteinas_total += ca.prot_total
            carbohidratos_total += ca.carb_total
            grasas_total += ca.gras_total

        registro = registros_hoy.get(comida.id)
        if registro:
            comida.completado = registro.Completado
            comida.completado_hora = (
                timezone.localtime(registro.HoraCompletado).strftime("%H:%M")
                if registro.HoraCompletado
                else ""
            )
        else:
            comida.completado = False
            comida.completado_hora = ""

        config_actual = boton_estilos[comida.completado]
        comida.boton_icono = config_actual["icono"]
        comida.boton_texto = config_actual["texto"]
        comida.boton_clase = config_actual["clase"]

        comida.boton_icono_completado = boton_estilos[True]["icono"]
        comida.boton_texto_completado = boton_estilos[True]["texto"]
        comida.boton_clase_completado = boton_estilos[True]["clase"]

        comida.boton_icono_pendiente = boton_estilos[False]["icono"]
        comida.boton_texto_pendiente = boton_estilos[False]["texto"]
        comida.boton_clase_pendiente = boton_estilos[False]["clase"]

        if comida.completado:
            if comida.completado_hora:
                comida.estado_registro = f"Registrada a las {comida.completado_hora}"
            else:
                comida.estado_registro = "Registrada hoy"
        else:
            comida.estado_registro = ""

        if comida.completado:
            comida.boton_icono = "task_alt"
            comida.boton_texto = "Comida completada"
            comida.boton_clase = "bg-green-50 text-green-700 border border-green-500"
        else:
            comida.boton_icono = "check_circle"
            comida.boton_texto = "Marcar como completado"
            comida.boton_clase = "bg-primary text-white"

    # --- Weight data for chart and stats ---
    hace_30_dias = timezone.now() - timezone.timedelta(days=30)
    mediciones = Medicion.objects.filter(
        SocioID=socio, Fecha__gte=hace_30_dias
    ).order_by("Fecha")

    chart_labels = [m.Fecha.strftime("%d %b") for m in mediciones]
    chart_peso = [
        float(m.PesoCorporal) for m in mediciones if m.PesoCorporal is not None
    ]
    chart_data = {"labels": chart_labels, "peso": chart_peso}

    peso_actual = float(mediciones.last().PesoCorporal) if mediciones.exists() else 0
    peso_inicial = (
        float(mediciones.first().PesoCorporal) if mediciones.exists() else peso_actual
    )
    cambio_peso = peso_actual - peso_inicial

    if cambio_peso > 0:
        cambio_peso_display, cambio_peso_color = f"+{round(cambio_peso, 1)} kg", "red"
    elif cambio_peso < 0:
        cambio_peso_display, cambio_peso_color = f"{round(cambio_peso, 1)} kg", "green"
    else:
        cambio_peso_display, cambio_peso_color = "0.0 kg", "gray"

    # --- Daily Tip ---
    tips = [
        "Bebe al menos 8 vasos de agua al día para mantenerte hidratado.",
        "Un puñado de almendras es un snack saludable y lleno de energía.",
        "Intenta incluir una fuente de proteína en cada comida principal.",
        "El té verde es un excelente antioxidante. ¡Pruébalo!",
        "No te saltes el desayuno, es la comida más importante para empezar el día.",
        "Aumenta tu consumo de fibra con frutas, verduras y granos enteros.",
        "Limita el consumo de azúcares procesados y bebidas azucaradas.",
        "Dormir entre 7 y 8 horas es crucial para la recuperación muscular.",
        "El aguacate es una fuente excelente de grasas saludables.",
        "Planifica tus comidas de la semana para evitar decisiones poco saludables.",
        "Una ensalada colorida te aporta una gran variedad de vitaminas y minerales.",
        "El pescado, como el salmón, es rico en Omega-3, beneficioso para el corazón.",
        "Modera el consumo de sal para cuidar tu presión arterial.",
        "El yogur griego es una fantástica fuente de proteínas y probióticos.",
        "Escucha a tu cuerpo: come cuando tengas hambre y para cuando estés satisfecho.",
        "Las legumbres (lentejas, garbanzos) son una gran fuente de proteína vegetal.",
        "Un batido de proteína post-entreno ayuda a la recuperación muscular.",
        "Incorpora verduras de hoja verde oscuro en tu dieta, como espinacas o kale.",
        "La avena es un carbohidrato de liberación lenta, ideal para el desayuno.",
        "No temas a los carbohidratos, elige opciones complejas como la batata o la quinoa.",
        "Cocina al vapor, a la plancha o al horno en lugar de freír.",
        "La fruta es el postre más saludable. ¡Disfrútala!",
        "Controla las porciones para mantener un balance calórico adecuado.",
        "Un café antes de entrenar puede darte un impulso de energía.",
        "Las semillas de chía son una excelente fuente de fibra y Omega-3.",
        "Mantén un registro de lo que comes para ser más consciente de tu dieta.",
        "Permítete un capricho de vez en cuando sin sentirte culpable.",
        "La vitamina D es importante. Toma un poco de sol de forma segura.",
        "Reduce el consumo de alcohol, ya que aporta calorías vacías.",
        "La consistencia es más importante que la perfección. ¡Sigue adelante!",
    ]
    daily_tip = tips[timezone.now().timetuple().tm_yday % len(tips)]

    context = {
        "socio": socio,
        "tiene_plan": True,
        "plan_nombre": "Plan de Nutrición",
        "dia_actual_nombre": dia_actual_nombre,
        "comidas_hoy": comidas_hoy,
        "calorias_total": int(calorias_total),
        "proteinas_total": round(proteinas_total, 1),
        "carbohidratos_total": round(carbohidratos_total, 1),
        "grasas_total": round(grasas_total, 1),
        "calorias_objetivo": plan_nutricional.ObjetivoCaloricoDiario or 2000,
        "peso_actual": round(peso_actual, 1),
        "peso_inicial": round(peso_inicial, 1),
        "cambio_peso_display": cambio_peso_display,
        "cambio_peso_color": cambio_peso_color,
        "chart_data_json": json.dumps(chart_data),
        "daily_tip": daily_tip,
        "boton_base_clase": "mark-meal-button inline-flex items-center gap-2 text-sm font-semibold rounded-lg px-3 py-2 transition-colors",
    }

    return render(request, "socio/MiNutrición.html", context)


@login_requerido
def mi_perfil_view(request):
    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    ultima_medicion = Medicion.objects.filter(SocioID=socio).order_by("-Fecha").first()
    peso_actual = ultima_medicion.PesoCorporal if ultima_medicion else None

    miembro_desde = (
        SocioMembresia.objects.filter(SocioID=socio)
        .order_by("FechaInicio")
        .values_list("FechaInicio", flat=True)
        .first()
    )

    membresia_actual = (
        SocioMembresia.objects.filter(SocioID=socio)
        .select_related("PlanID")
        .order_by("-FechaFin")
        .first()
    )
    membresia_estado = None
    membresia_dias_restantes = None
    membresia_dias_texto = None
    if membresia_actual:
        if membresia_actual.FechaFin:
            dias_restantes = (membresia_actual.FechaFin - timezone.now().date()).days
            membresia_dias_restantes = dias_restantes
            if dias_restantes >= 0:
                membresia_dias_texto = (
                    f"{dias_restantes} día{'s' if dias_restantes != 1 else ''}"
                )
            else:
                dias_abs = abs(dias_restantes)
                membresia_dias_texto = (
                    f"Vencida hace {dias_abs} día{'s' if dias_abs != 1 else ''}"
                )
        estado = (membresia_actual.Estado or "").lower()
        if estado == "activa" and (
            membresia_dias_restantes is None or membresia_dias_restantes >= 0
        ):
            membresia_estado = "activa"
        elif membresia_dias_restantes is not None and membresia_dias_restantes < 0:
            membresia_estado = "vencida"
        else:
            membresia_estado = estado or "pendiente"

    if request.method == "POST":
        form = PerfilSocioForm(request.POST, instance=socio, peso_inicial=peso_actual)
        if form.is_valid():
            socio = form.save()
            peso = form.cleaned_data.get("peso_actual")
            if peso:
                altura = float(socio.Altura) if socio.Altura else None
                imc = None
                if altura and altura > 0:
                    imc = round(float(peso) / (altura**2), 2)

                Medicion.objects.update_or_create(
                    SocioID=socio,
                    Fecha=timezone.now().date(),
                    defaults={
                        "PesoCorporal": peso,
                        "IMC": imc,
                    },
                )

            messages.success(request, "Tu perfil se actualizó correctamente.")
            return redirect("mi_perfil")
        else:
            messages.error(request, "Por favor revisa los datos ingresados.")
    else:
        form = PerfilSocioForm(instance=socio, peso_inicial=peso_actual)

    context = {
        "socio": socio,
        "form": form,
        "ultima_medicion": ultima_medicion,
        "miembro_desde": miembro_desde,
        "membresia_actual": membresia_actual,
        "membresia_estado": membresia_estado,
        "membresia_dias_restantes": membresia_dias_restantes,
        "membresia_dias_texto": membresia_dias_texto,
    }
    return render(request, "socio/MiPerfil.html", context)


@login_requerido
def toggle_comida_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        return JsonResponse({"error": "Sesión inválida"}, status=401)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Formato inválido"}, status=400)

    dia_comida_id = body.get("dia_comida_id")
    if not dia_comida_id:
        return JsonResponse(
            {"error": "Falta el identificador de la comida"}, status=400
        )

    from apps.control_acceso.models import DiaComida, PlanNutricional

    dia_comida = get_object_or_404(DiaComida, id=dia_comida_id)

    plan = PlanNutricional.objects.filter(SocioID=socio).first()
    if not plan or dia_comida.PlanNutricionalID_id != plan.id:
        return JsonResponse(
            {"error": "No estás autorizado para modificar esta comida"}, status=403
        )

    fecha_actual = timezone.localdate()
    registro, created = RegistroComidaDiaria.objects.get_or_create(
        SocioID=socio,
        DiaComidaID=dia_comida,
        Fecha=fecha_actual,
        defaults={"Completado": True, "HoraCompletado": timezone.now()},
    )

    if not created:
        registro.Completado = not registro.Completado
        registro.HoraCompletado = timezone.now() if registro.Completado else None
        registro.save()

    hora_display = (
        timezone.localtime(registro.HoraCompletado).strftime("%H:%M")
        if registro.HoraCompletado
        else ""
    )

    return JsonResponse(
        {
            "success": True,
            "completado": registro.Completado,
            "hora": hora_display,
            "dia_comida_id": dia_comida_id,
        }
    )


@login_requerido
def historial_comidas_view(request):
    dias_consulta = request.GET.get("dias", "7")
    try:
        dias_consulta = max(1, min(30, int(dias_consulta)))
    except ValueError:
        dias_consulta = 7

    usuario_id = request.session.get("usuario_id")

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect("login")

    from apps.control_acceso.models import DiaComida, PlanNutricional

    plan = PlanNutricional.objects.filter(SocioID=socio).first()
    if not plan:
        opciones_rango = [7, 14, 21, 30]
        context = {
            "socio": socio,
            "tiene_plan": False,
            "historial_dias": [],
            "dias_consulta": dias_consulta,
            "opciones_rango": [
                {"valor": opcion, "selected": dias_consulta == opcion}
                for opcion in opciones_rango
            ],
        }
        return render(request, "socio/HistorialComidas.html", context)

    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]

    dias_plan = (
        DiaComida.objects.filter(PlanNutricionalID=plan)
        .prefetch_related("alimentos__AlimentoID")
        .order_by("DiaSemana", "id")
    )
    dias_por_semana = {}
    for dia in dias_plan:
        dias_por_semana.setdefault(dia.DiaSemana, []).append(dia)

    fecha_hoy = timezone.localdate()
    fecha_inicio = fecha_hoy - timezone.timedelta(days=dias_consulta - 1)
    registros = RegistroComidaDiaria.objects.filter(
        SocioID=socio, Fecha__range=(fecha_inicio, fecha_hoy), Completado=True
    ).select_related("DiaComidaID")
    registros_map = {
        (registro.Fecha, registro.DiaComidaID_id): registro for registro in registros
    }

    historial_dias = []
    for offset in range(dias_consulta):
        fecha_dia = fecha_hoy - timezone.timedelta(days=offset)
        dia_semana_idx = fecha_dia.weekday()
        comidas_plan_dia = dias_por_semana.get(dia_semana_idx, [])

        if not comidas_plan_dia:
            continue

        comidas_render = []
        completadas = 0

        for comida in comidas_plan_dia:
            registro = registros_map.get((fecha_dia, comida.id))
            completado = registro.Completado if registro else False
            if completado:
                completadas += 1

            alimentos_nombres = ", ".join(
                ca.AlimentoID.Nombre for ca in comida.alimentos.all()
            )
            alimentos_texto = (
                alimentos_nombres if alimentos_nombres else "Sin alimentos configurados"
            )

            comidas_render.append(
                {
                    "nombre": comida.TipoComida or "Comida",
                    "completado": completado,
                    "hora": timezone.localtime(registro.HoraCompletado).strftime(
                        "%H:%M"
                    )
                    if registro and registro.HoraCompletado
                    else "",
                    "alimentos_texto": alimentos_texto,
                }
            )

        if completadas > 0:
            historial_dias.append(
                {
                    "fecha": fecha_dia,
                    "fecha_display": fecha_dia.strftime("%d %b %Y"),
                    "dia_semana": dias_semana[dia_semana_idx],
                    "total": len(comidas_plan_dia),
                    "completadas": completadas,
                    "comidas": comidas_render,
                }
            )

    opciones_rango = [7, 14, 21, 30]
    context = {
        "socio": socio,
        "tiene_plan": True,
        "historial_dias": historial_dias,
        "dias_consulta": dias_consulta,
        "opciones_rango": [
            {"valor": opcion, "selected": dias_consulta == opcion}
            for opcion in opciones_rango
        ],
    }
    return render(request, "socio/HistorialComidas.html", context)
