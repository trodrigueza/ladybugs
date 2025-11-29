from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def login_requerido(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if "usuario_id" not in request.session:
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_requerido(view_func):
    """Decorador para verificar que el usuario sea Administrativo"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if "usuario_id" not in request.session:
            messages.error(request, "Debes iniciar sesión para acceder a esta página.")
            return redirect("login")
        
        usuario_rol = request.session.get("usuario_rol", "").lower()
        if usuario_rol != "administrativo":
            messages.error(request, "No tienes permisos para acceder a esta página.")
            return redirect("login")
        
        return view_func(request, *args, **kwargs)
    return wrapper

