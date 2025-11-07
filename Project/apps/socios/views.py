from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError
from .servicios.registro_db import create_socio_from_dict

def register_view(request):
    if request.method == 'POST':
        # leer datos del formulario
        identificacion = request.POST.get('identificacion', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        birthdate = request.POST.get('birthdate', '').strip()
        consent_raw = request.POST.get('consent')  # checkbox: 'on' o None
        consent = True if consent_raw is not None else False
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        health_status = request.POST.get('health_status', '').strip()
        follow_up_note = request.POST.get('follow_up_note', '').strip()

        # validaciones básicas
        if not identificacion or not full_name or not password or not email or not birthdate:
            messages.error(request, "Por favor completa todos los campos obligatorios.")
            return render(request, 'socio/register.html', request.POST)

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'socio/register.html', request.POST)

        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
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
            create_socio_from_dict(data)
            messages.success(request, "Cuenta creada correctamente. Puedes iniciar sesión.")
            return redirect('login')
        except IntegrityError:
            messages.error(request, "Ya existe un socio con esa identificación o correo.")
            return render(request, 'socio/register.html', request.POST)
        except Exception as e:
            messages.error(request, f"Ocurrió un error: {str(e)}")
            return render(request, 'socio/register.html', request.POST)


    return render(request, 'socio/register.html')
