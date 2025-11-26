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

