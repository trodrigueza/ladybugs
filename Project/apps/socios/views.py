from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse

from .servicios.registro_db import create_socio_from_dict, ValidationError
from apps.seguridad.servicios.registro_usuario import crear_usuario_para_socio
from apps.seguridad.decoradores import login_requerido


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
    # 1. Racha (Simulada por ahora, o cálculo complejo de Asistencia)
    # Para MVP: Contar asistencias de los últimos 7 días
    membresias = SocioMembresia.objects.filter(SocioID=socio)
    asistencias_recientes = Asistencia.objects.filter(
        SocioMembresiaID__in=membresias,
        FechaHoraEntrada__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    racha_dias = asistencias_recientes # Simplificación

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
    
    # Mensaje dinámico para racha
    mensaje_racha = "¡Comienza tu racha hoy!"
    if racha_dias == 0:
        mensaje_racha = "¡Comienza tu racha hoy!"
    elif 1 <= racha_dias <= 5:
        mensaje_racha = "¡Bien! Sigue así"
    elif 6 <= racha_dias <= 14:
        mensaje_racha = "¡Excelente racha!"
    else:
        mensaje_racha = "¡Increíble dedicación!"

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
def planel_inicio_entrenador_view(request):
    return render(request, "Entrenador/PaneldeInicio.html")

@login_requerido
def panel_admin_view(request):
    return render(request, "Administrador/PaneldeInicio.html")

