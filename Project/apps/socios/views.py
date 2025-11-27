from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime
import json

from .servicios.registro_db import create_socio_from_dict, ValidationError
from apps.seguridad.servicios.registro_usuario import crear_usuario_para_socio
from apps.seguridad.decoradores import login_requerido
from .models import Socio, Medicion
from apps.pagos.models import SocioMembresia, PlanMembresia, Pago, AlertaPago
from apps.control_acceso.models import (
    RutinaSemanal, DiaRutinaEjercicio, Ejercicio, 
    SesionEntrenamiento, EjercicioSesionCompletado, CompletionTracking
)


def register_view(request):
    if request.method == 'POST':

        identificacion = request.POST.get('identificacion', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        birthdate = request.POST.get('birthdate', '').strip()
        consent_raw = request.POST.get('consent') 
        consent = True if consent_raw is not None else False
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        health_status = request.POST.get('health_status', '').strip()
        follow_up_note = request.POST.get('follow_up_note', '').strip()

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'socio/register.html', request.POST)

        if not consent:
            messages.error(request, "Debes aceptar el tratamiento de datos personales.")
            return render(request, 'socio/register.html', request.POST)

        data = {
            'identificacion': identificacion,
            'full_name': full_name,
            'phone': phone,
            'email': email,
            'birthdate': birthdate,
            'consent': consent,
            'password': password,
            'health_status': health_status,
            'follow_up_note': follow_up_note,
        }

        try:
            socio = create_socio_from_dict(data)

            crear_usuario_para_socio(socio, password)

            messages.success(request, "Cuenta creada correctamente. Puedes iniciar sesión.")
            return redirect('login')
        
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'socio/register.html', request.POST)

        except IntegrityError:
            messages.error(request, "Ya existe un socio con esa identificación o correo.")
            return render(request, 'socio/register.html', request.POST)

        except Exception as e:
            messages.error(request, f"Ocurrió un error inesperado: {str(e)}")
            return render(request, 'socio/register.html', request.POST)

    return render(request, 'socio/register.html')


#Interfaz Inicio (beta)

from datetime import datetime
from django.utils import timezone
from apps.seguridad.models import Usuario
from apps.socios.models import Socio, Medicion
from apps.control_acceso.models import (
    RutinaSemanal, DiaRutinaEjercicio, PlanNutricional, DiaComida, Asistencia
)
from apps.pagos.models import SocioMembresia, AlertaPago

# ... (keep existing imports and register_view)

@login_requerido
def panel_de_control_view(request):
    usuario_id = request.session.get('usuario_id')
    
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        # Asumimos que el email es el vínculo entre Usuario y Socio
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect('login')

    # --- Estadísticas ---
    # 1. Racha (Consecutive training days with 1-day grace period)
    membresias = SocioMembresia.objects.filter(SocioID=socio)
    
    # Get all completed sessions ordered by date (newest first)
    sesiones_completadas = SesionEntrenamiento.objects.filter(
        SocioMembresiaID__in=membresias,
        FechaFin__isnull=False
    ).order_by('-FechaInicio').values_list('FechaInicio', flat=True)
    
    # Calculate streak
    racha_dias = 0
    racha_en_peligro = False
    mensaje_racha = ""
    
    if sesiones_completadas:
        hoy = timezone.now().date()
        dias_unicos = set()
        
        # Get unique training days
        for dt in sesiones_completadas:
            dias_unicos.add(dt.date())
        
        dias_unicos = sorted(dias_unicos, reverse=True)
        
        # Check if trained today
        entreno_hoy = hoy in dias_unicos
        
        # Check if trained yesterday
        ayer = hoy - timezone.timedelta(days=1)
        entreno_ayer = ayer in dias_unicos
        
        # Check if today is weekend
        es_fin_de_semana = hoy.weekday() in [5, 6]  # Saturday=5, Sunday=6
        
        # Calculate consecutive days
        if entreno_hoy or entreno_ayer:
            fecha_actual = hoy if entreno_hoy else ayer
            racha_dias = 1
            dias_sin_entrenar = 0
            
            for i in range(1, 365):  # Max 1 year lookback
                fecha_anterior = fecha_actual - timezone.timedelta(days=i)
                dia_semana = fecha_anterior.weekday()
                
                if fecha_anterior in dias_unicos:
                    racha_dias += 1
                    dias_sin_entrenar = 0
                else:
                    # Skip weekends in the count
                    if dia_semana not in [5, 6]:  # Not Saturday or Sunday
                        dias_sin_entrenar += 1
                        if dias_sin_entrenar > 1:  # Grace period of 1 weekday
                            break
            
            # Check if streak is at risk
            if not entreno_hoy and entreno_ayer:
                if es_fin_de_semana:
                    mensaje_racha = f"🌴 Es fin de semana, está bien si descansas :) No perderás tu racha de {racha_dias} días"
                else:
                    racha_en_peligro = True
                    mensaje_racha = f"⚠️ ¡Si hoy no entrenas perderás tu racha de {racha_dias} días!"
            elif entreno_hoy:
                mensaje_racha = f"¡Genial! Llevas {racha_dias} {'día' if racha_dias == 1 else 'días'} seguidos"
            elif es_fin_de_semana and not entreno_hoy:
                mensaje_racha = f"🌴 Es fin de semana, está bien si descansas :) Tienes {racha_dias} {'día' if racha_dias == 1 else 'días'} de racha"
        else:
            # No recent activity
            mensaje_racha = "Comienza tu racha entrenando hoy"
    else:
        mensaje_racha = "Comienza tu racha entrenando hoy"

    # 2. Peso Actual
    ultima_medicion = Medicion.objects.filter(SocioID=socio).order_by('-Fecha').first()
    peso_actual = ultima_medicion.PesoCorporal if ultima_medicion else 0
    fecha_peso = ultima_medicion.Fecha if ultima_medicion else None
    
    # 3. IMC (Índice de Masa Corporal)
    imc_actual = 0
    estado_imc = "Desconocido"
    if socio.Altura and peso_actual:
        altura_m = float(socio.Altura)
        peso_kg = float(peso_actual)
        if altura_m > 0:
            imc_actual = round(peso_kg / (altura_m ** 2), 1)
            
            if imc_actual < 18.5: estado_imc = "Bajo peso"
            elif 18.5 <= imc_actual < 25: estado_imc = "Peso normal"
            elif 25 <= imc_actual < 30: estado_imc = "Sobrepeso"
            else: estado_imc = "Obesidad"

    # 4. Logros (Placeholder)
    logros_count = 5 

    # --- Gráfica de Peso e IMC (Últimos 30 días) ---
    historial_peso = Medicion.objects.filter(
        SocioID=socio
    ).order_by('Fecha')[:30]
    
    # Preparar datos para Chart.js
    import json
    chart_labels = []
    chart_peso = []
    chart_imc = []
    
    for medicion in historial_peso:
        chart_labels.append(medicion.Fecha.strftime('%d %b'))
        chart_peso.append(float(medicion.PesoCorporal) if medicion.PesoCorporal else 0)
        
        # Calcular IMC para cada medición
        if socio.Altura and medicion.PesoCorporal:
            altura_m = float(socio.Altura)
            peso_kg = float(medicion.PesoCorporal)
            imc = round(peso_kg / (altura_m ** 2), 1) if altura_m > 0 else 0
            chart_imc.append(imc)
        else:
            chart_imc.append(0)
    
    chart_data = {
        'labels': chart_labels,
        'peso': chart_peso,
        'imc': chart_imc
    }
    
    # Calcular tendencia de peso (comparar últimas 2 mediciones)
    tendencia_peso = "estable"
    mensaje_peso = "Mantén tu rutina"
    ultimas_2 = Medicion.objects.filter(SocioID=socio).order_by('-Fecha')[:2]
    
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
    dia_semana_actual = datetime.now().weekday() # 0=Lunes
    rutina_hoy = []
    rutina_obj = RutinaSemanal.objects.filter(SocioID=socio).first()
    if rutina_obj:
        rutina_hoy = DiaRutinaEjercicio.objects.filter(
            RutinaID=rutina_obj,
            DiaSemana=dia_semana_actual
        ).select_related('EjercicioID')

    # --- Plan Nutricional de Hoy ---
    plan_nutricional_hoy = []
    plan_nutri_obj = PlanNutricional.objects.filter(SocioID=socio).first()
    if plan_nutri_obj:
        dias_comida = DiaComida.objects.filter(
            PlanNutricionalID=plan_nutri_obj,
            DiaSemana=dia_semana_actual
        ).prefetch_related('alimentos__AlimentoID')
        plan_nutricional_hoy = dias_comida

    # --- Notificaciones ---
    notificaciones = AlertaPago.objects.filter(
        SocioMembresiaID__in=membresias,
        VistaEnPanel=False
    )

    context = {
        'socio': socio,
        'racha_dias': racha_dias,
        'racha_en_peligro': racha_en_peligro,
        'peso_actual': peso_actual,
        'fecha_peso': fecha_peso,
        'imc_actual': imc_actual,
        'estado_imc': estado_imc,
        'mensaje_peso': mensaje_peso,
        'mensaje_racha': mensaje_racha,
        'logros_count': logros_count,
        'rutina_hoy': rutina_hoy,
        'plan_nutricional_hoy': plan_nutricional_hoy,
        'notificaciones': notificaciones,
        'historial_peso': historial_peso,
        'chart_data_json': json.dumps(chart_data),
    }

    return render(request, "socio/PanelDeControl.html", context)

@login_requerido
def mi_rutina_view(request):
    from apps.control_acceso.models import SesionEntrenamiento, EjercicioSesionCompletado
    
    usuario_id = request.session.get('usuario_id')
    
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect('login')
    
    # Obtener todas las rutinas del socio
    rutinas = RutinaSemanal.objects.filter(SocioID=socio).prefetch_related('dias_ejercicios__EjercicioID')
    
    # Rutina activa (la primera no plantilla, o la primera en general)
    rutina_id = request.GET.get('rutina_id')
    rutina_activa = None
    es_modo_libre = False
    
    if rutina_id == 'free':
        es_modo_libre = True
        rutina_activa = None
    elif rutina_id:
        rutina_activa = rutinas.filter(id=rutina_id).first()
    
    if not rutina_activa and not es_modo_libre:
        rutina_activa = rutinas.filter(EsPlantilla=False).first() or rutinas.first()
    
    # Convert query to list and add selected attribute for template
    rutinas = list(rutinas)
    for r in rutinas:
        r.selected_attr = 'selected' if r == rutina_activa else ''
        r.icon_name = 'check_circle' if r == rutina_activa else 'arrow_forward_ios'
    
    # Obtener ejercicios SOLO del día actual
    ejercicios_hoy = []
    dia_actual = datetime.now().weekday()
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_nombre = dias_semana[dia_actual]
    
    if rutina_activa:
        ejercicios_hoy = list(rutina_activa.dias_ejercicios.filter(DiaSemana=dia_actual).select_related('EjercicioID'))
    
    # Verificar si ya completó la rutina de hoy
    ya_completado_hoy = False
    if rutina_activa:
        # Check CompletionTracking
        semana_actual = datetime.now().strftime("%Y-%W")
        membresias = SocioMembresia.objects.filter(SocioID=socio)
        ya_completado_hoy = CompletionTracking.objects.filter(
            SocioMembresiaID__in=membresias,
            RutinaID=rutina_activa,
            Semana=semana_actual,
            DiaSemana=dia_actual,
            Completado=True
        ).exists()
    
    # Detectar sesión activa
    membresias = SocioMembresia.objects.filter(SocioID=socio)
    sesion_activa = SesionEntrenamiento.objects.filter(
        SocioMembresiaID__in=membresias,
        FechaFin__isnull=True
    ).first()
    
    # Obtener ejercicios completados en la sesión activa
    ejercicios_completados_ids = []
    if sesion_activa:
        ejercicios_completados_ids = list(sesion_activa.ejercicios_completados.values_list('DiaRutinaEjercicioID', flat=True))
    
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
            checked = 'checked' if ejercicio.is_completed else ''
            ejercicio.checkbox_html = f'<input class="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer" type="checkbox" data-ejercicio-id="{ejercicio.id}" {checked} onchange="toggleEjercicio(this)" />'
        else:
            ejercicio.checkbox_html = '<input class="h-5 w-5 rounded border-gray-300 text-gray-400 cursor-not-allowed" type="checkbox" disabled />'
    
    # Historial de sesiones (limit to 3)
    historial_sesiones = SesionEntrenamiento.objects.filter(
        SocioMembresiaID__in=membresias,
        FechaFin__isnull=False
    ).select_related('RutinaID').order_by('-FechaInicio')[:3]
    
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
        'socio': socio,
        'rutinas': rutinas,
        'rutina_activa': rutina_activa,
        'ejercicios_hoy': ejercicios_hoy,
        'dia_actual': dia_nombre,
        'sesion_activa': sesion_activa,
        'ya_completado_hoy': ya_completado_hoy,
        'historial_sesiones': historial_sesiones,
        'es_modo_libre': es_modo_libre,
    }
    
    return render(request, "socio/MiRutina.html", context)

@login_requerido
def planel_inicio_entrenador_view(request):
    return render(request, "Entrenador/PaneldeInicio.html")

@login_requerido
def panel_admin_view(request):
    usuario_id = request.session.get('usuario_id')

    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('login')

    rol = ''
    try:
        rol = usuario.RolID.NombreRol.strip().lower() if usuario.RolID and usuario.RolID.NombreRol else ''
    except Exception:
        rol = ''

    if rol != 'administrativo':
        messages.error(request, "No tienes permisos para acceder al panel administrativo.")
        if rol == 'entrenador':
            return redirect('panel_entrenador')
        if rol == 'socio':
            return redirect('socio_panel')
        return redirect('login')

    return render(request, "Administrador/PaneldeInicio.html")

# === SESSION TRACKING VIEWS ===

@login_requerido
def iniciar_sesion_view(request):
    from apps.control_acceso.models import SesionEntrenamiento, EjercicioSesionCompletado
    from django.http import JsonResponse
    
    if request.method == "POST":
        usuario_id = request.session.get('usuario_id')
        
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)
            
            # Check for free training mode
            entrenamiento_libre = request.POST.get('entrenamiento_libre') == 'on'
            rutina_id = request.POST.get('rutina_id')
            
            # Get selected routine (or None for free training)
            rutina = None
            if not entrenamiento_libre:
                if rutina_id:
                    try:
                        rutina = RutinaSemanal.objects.get(id=rutina_id, SocioID=socio)
                    except RutinaSemanal.DoesNotExist:
                        messages.error(request, "Rutina no encontrada.")
                        return redirect('mi_rutina')
                else:
                    rutina = RutinaSemanal.objects.filter(SocioID=socio, EsPlantilla=False).first()
                
                if not rutina:
                    messages.error(request, "No tienes una rutina asignada.")
                    return redirect('mi_rutina')
            
            # Verificar que no haya sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias,
                FechaFin__isnull=True
            ).first()
            
            if sesion_activa:
                messages.warning(request, "Ya tienes una sesión activa.")
                return redirect('mi_rutina')
            
            # Crear nueva sesión
            membresia = membresias.first()
            if not membresia:
                messages.error(request, "No tienes una membresía activa.")
                return redirect('mi_rutina')
            
            dia_semana = datetime.now().weekday()
            sesion = SesionEntrenamiento.objects.create(
                RutinaID=rutina,
                SocioMembresiaID=membresia,
                FechaInicio=timezone.now(),
                DiaSemana=dia_semana,
                EsEntrenamientoLibre=entrenamiento_libre
            )
            
            # Crear registros de ejercicios solo si NO es entrenamiento libre
            if not entrenamiento_libre and rutina:
                ejercicios_dia = DiaRutinaEjercicio.objects.filter(
                    RutinaID=rutina,
                    DiaSemana=dia_semana
                )
                
                for ejercicio in ejercicios_dia:
                    EjercicioSesionCompletado.objects.create(
                        SesionID=sesion,
                        DiaRutinaEjercicioID=ejercicio,
                        Completado=False
                    )
            
            modo = "libre" if entrenamiento_libre else rutina.Nombre
            messages.success(request, f"¡Sesión iniciada ({modo})! Buena suerte.")
            return redirect('mi_rutina')
            
        except (Usuario.DoesNotExist, Socio.DoesNotExist):
            messages.error(request, "Error al iniciar sesión.")
            return redirect('mi_rutina')
    
    return redirect('mi_rutina')


@login_requerido
def toggle_ejercicio_view(request):
    from apps.control_acceso.models import SesionEntrenamiento, EjercicioSesionCompletado
    from django.http import JsonResponse
    import json
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ejercicio_id = data.get('ejercicio_id')
            
            usuario_id = request.session.get('usuario_id')
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)
            
            # Buscar sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias,
                FechaFin__isnull=True
            ).first()
            
            if not sesion_activa:
                return JsonResponse({'error': 'No hay sesión activa'}, status=400)
            
            # Toggle ejercicio
            ejercicio_sesion = EjercicioSesionCompletado.objects.get(
                SesionID=sesion_activa,
                DiaRutinaEjercicioID_id=ejercicio_id
            )
            
            ejercicio_sesion.Completado = not ejercicio_sesion.Completado
            ejercicio_sesion.save()
            
            # Verificar si todos están completados
            total = sesion_activa.ejercicios_completados.count()
            completados = sesion_activa.ejercicios_completados.filter(Completado=True).count()
            
            return JsonResponse({
                'success': True,
                'completado': ejercicio_sesion.Completado,
                'progreso': f'{completados}/{total}',
                'todos_completados': completados == total
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_requerido
def detalle_sesion_view(request, sesion_id):
    """View to show details of a completed session"""
    from apps.control_acceso.models import SesionEntrenamiento
    
    usuario_id = request.session.get('usuario_id')
    
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
        
        # Get session and verify it belongs to this socio
        membresias = SocioMembresia.objects.filter(SocioID=socio)
        sesion = SesionEntrenamiento.objects.filter(
            id=sesion_id,
            SocioMembresiaID__in=membresias
        ).first()
        
        if not sesion:
            messages.error(request, "Sesión no encontrada.")
            return redirect('mi_rutina')
        
        # Get exercises for this session
        ejercicios = []
        completados_count = 0
        total_count = 0
        pendientes_count = 0
        
        if not sesion.EsEntrenamientoLibre:
            ejercicios = list(sesion.ejercicios_completados.all().select_related(
                'DiaRutinaEjercicioID__EjercicioID'
            ))
            
            # Pre-calculate exercise names to avoid template formatting issues
            for ej in ejercicios:
                ej.nombre_ejercicio = ej.DiaRutinaEjercicioID.EjercicioID.Nombre
            
            total_count = len(ejercicios)
            completados_count = sum(1 for ej in ejercicios if ej.Completado)
            pendientes_count = total_count - completados_count
        
        context = {
            'sesion': sesion,
            'ejercicios': ejercicios,
            'total_count': total_count,
            'completados_count': completados_count,
            'pendientes_count': pendientes_count,
        }
        
        return render(request, "socio/DetalleSesion.html", context)
        
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "Error al cargar sesión.")
        return redirect('mi_rutina')


@login_requerido
def terminar_sesion_view(request):
    from apps.control_acceso.models import SesionEntrenamiento
    from django.http import JsonResponse
    
    if request.method == "POST":
        usuario_id = request.session.get('usuario_id')
        
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)
            
            # Buscar sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias,
                FechaFin__isnull=True
            ).first()
            
            if not sesion_activa:
                messages.warning(request, "No tienes una sesión activa.")
                return redirect('mi_rutina')
            
            # Save notes if provided
            notas = request.POST.get('notas', '').strip()
            if notas:
                sesion_activa.NotasSesion = notas
            
            # Terminar sesión
            sesion_activa.FechaFin = timezone.now()
            duracion = (sesion_activa.FechaFin - sesion_activa.FechaInicio).total_seconds() / 60
            sesion_activa.DuracionMinutos = int(duracion)
            sesion_activa.save()
            
            # Check for weekly completion (only for non-free training)
            if not sesion_activa.EsEntrenamientoLibre and sesion_activa.RutinaID:
                from apps.control_acceso.models import CompletionTracking
                
                # Check if all exercises were completed
                total_ejercicios = sesion_activa.ejercicios_completados.count()
                ejercicios_completados = sesion_activa.ejercicios_completados.filter(Completado=True).count()
                
                if total_ejercicios > 0 and ejercicios_completados == total_ejercicios:
                    # Calculate current week (ISO week format: YYYY-WW)
                    now = timezone.now()
                    semana = now.strftime('%Y-%W')
                    
                    # Create or update completion record
                    CompletionTracking.objects.update_or_create(
                        SocioMembresiaID=sesion_activa.SocioMembresiaID,
                        RutinaID=sesion_activa.RutinaID,
                        DiaSemana=sesion_activa.DiaSemana,
                        Semana=semana,
                        defaults={'Completado': True}
                    )
                    
                    messages.success(request, f"🎉 ¡Sesión completada! Todos los ejercicios de hoy finalizados. Duración: {int(duracion)} min.")
                else:
                    messages.success(request, f"Sesión terminada. Duración: {int(duracion)} minutos.")
            else:
                messages.success(request, f"Sesión terminada. Duración: {int(duracion)} minutos.")
            return redirect('mi_rutina')
            
        except (Usuario.DoesNotExist, Socio.DoesNotExist):
            messages.error(request, "Error al terminar sesión.")
            return redirect('mi_rutina')
    
    return redirect('mi_rutina')


@login_requerido
def toggle_ejercicio_view(request):
    from apps.control_acceso.models import SesionEntrenamiento, EjercicioSesionCompletado
    from django.http import JsonResponse
    import json
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ejercicio_id = data.get('ejercicio_id')
            
            usuario_id = request.session.get('usuario_id')
            usuario = Usuario.objects.get(id=usuario_id)
            socio = Socio.objects.get(Email=usuario.Email)
            
            # Buscar sesión activa
            membresias = SocioMembresia.objects.filter(SocioID=socio)
            sesion_activa = SesionEntrenamiento.objects.filter(
                SocioMembresiaID__in=membresias,
                FechaFin__isnull=True
            ).first()
            
            if not sesion_activa:
                return JsonResponse({'error': 'No hay sesión activa'}, status=400)
            
            # Toggle ejercicio
            ejercicio_sesion = EjercicioSesionCompletado.objects.get(
                SesionID=sesion_activa,
                DiaRutinaEjercicioID_id=ejercicio_id
            )
            
            ejercicio_sesion.Completado = not ejercicio_sesion.Completado
            ejercicio_sesion.save()
            
            # Verificar si todos están completados
            total = sesion_activa.ejercicios_completados.count()
            completados = sesion_activa.ejercicios_completados.filter(Completado=True).count()
            
            return JsonResponse({
                'success': True,
                'completado': ejercicio_sesion.Completado,
                'progreso': f'{completados}/{total}',
                'todos_completados': completados == total
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_requerido
def historial_sesiones_view(request):
    usuario_id = request.session.get('usuario_id')
    
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        socio = Socio.objects.get(Email=usuario.Email)
    except (Usuario.DoesNotExist, Socio.DoesNotExist):
        messages.error(request, "No se encontró el perfil de socio asociado.")
        return redirect('login')
    
    membresias = SocioMembresia.objects.filter(SocioID=socio)
    
    historial_sesiones = SesionEntrenamiento.objects.filter(
        SocioMembresiaID__in=membresias,
        FechaFin__isnull=False
    ).select_related('RutinaID').order_by('-FechaInicio')
    
    # Pre-calculate display name
    historial_sesiones = list(historial_sesiones)
    for s in historial_sesiones:
        if s.EsEntrenamientoLibre:
            s.nombre_display = "Entrenamiento Libre"
        elif s.RutinaID:
            s.nombre_display = s.RutinaID.Nombre
        else:
            s.nombre_display = "Sesión sin nombre"
            
    context = {
        'historial_sesiones': historial_sesiones
    }
    return render(request, "socio/HistorialSesiones.html", context)
