from django.shortcuts import render, redirect
from django.contrib import messages

from apps.seguridad.models import Usuario
from apps.seguridad.servicios.autenticacion import (
    autenticar_usuario,
    registrar_logout,
)


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        rol_seleccionado = request.POST.get("role", "").strip()

        if not email or not password:
            messages.error(request, "Debes ingresar correo y contraseña.")
            return render(request, "seguridad/login.html", {"email": email})

        if not rol_seleccionado:
            messages.error(request, "Debes seleccionar un rol.")
            return render(request, "seguridad/login.html", {"email": email})

        usuario = autenticar_usuario(email, password)

        if usuario is None:
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(request, "seguridad/login.html", {"email": email})

        rol_real = usuario.RolID.NombreRol.lower()

        if rol_seleccionado != rol_real:
            messages.error(request, "No tienes permisos para iniciar sesión como ese rol.")
            return render(request, "seguridad/login.html", {"email": email})
        
        request.session["usuario_id"] = usuario.id
        request.session["usuario_email"] = usuario.Email
        request.session["usuario_rol"] = rol_real

        messages.success(request, f"Bienvenido, {usuario.Email}.")

        if rol_real == "socio":
            return redirect("socio_panel")

        elif rol_real == "entrenador":
            return redirect("panel_entrenador")  
        elif rol_real == "administrativo":
            return redirect("panel_admin")  

        return redirect("socio_panel")

    return render(request, "seguridad/login.html")



def logout_view(request):
    usuario_id = request.session.get("usuario_id")

    if usuario_id:
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            registrar_logout(usuario)
        except Usuario.DoesNotExist:
            pass

    request.session.flush()

    messages.success(request, "Has cerrado sesión correctamente.")

    return redirect("login")
