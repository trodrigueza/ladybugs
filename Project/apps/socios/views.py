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

def panel_de_control_view(request):
    return render(request, "socio/PanelDeControl.html")

#Acceso solo con registro previo

@login_requerido
def panel_de_control_view(request):
    return render(request, "socio/PanelDeControl.html")

@login_requerido
def panel_entrenador_view(request):
    return HttpResponse("PANEL DEL ENTRENADOR — OK")

@login_requerido
def panel_admin_view(request):
    return HttpResponse("PANEL ADMINISTRATIVO — OK")

