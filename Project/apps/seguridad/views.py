from django.shortcuts import render, redirect
from django.contrib import messages

from apps.seguridad.models import Usuario
from apps.seguridad.servicios.autenticacion import (
    autenticar_usuario,
    registrar_logout,
)


def login_view(request):
    """
    Vista de login básica:
    - GET: muestra el formulario
    - POST: procesa usuario/contraseña
    - Si es correcto: guarda info en sesión y redirige a 'home'
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Debes ingresar email y contraseña.")
            return render(
                request,
                "seguridad/login.html",
                {"email": email},
            )

        usuario = autenticar_usuario(email, password)

        if usuario is None:
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(
                request,
                "seguridad/login.html",
                {"email": email},
            )

        #Guardar datos en sesión
        request.session["usuario_id"] = usuario.id
        request.session["usuario_email"] = usuario.Email
        request.session["usuario_rol"] = usuario.RolID.NombreRol

        messages.success(request, f"Bienvenido, {usuario.Email}.")
        
        return redirect("panel_control")

    # GET
    return render(request, "seguridad/login.html")


def logout_view(request):
    """
    Cierra sesión:
    - Registra en auditoría
    - Limpia la sesión
    - Redirige a login
    """
    usuario = None
    usuario_id = request.session.get("usuario_id")

    if usuario_id:
        try:
            usuario = Usuario.objects.get(pk=usuario_id)
        except Usuario.DoesNotExist:
            usuario = None

    registrar_logout(usuario)

    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("login")
