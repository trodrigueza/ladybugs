from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.seguridad.models import Usuario, Rol
from apps.seguridad.servicios.autenticacion import (
    autenticar_usuario,
    registrar_logout,
)
from apps.socios.models import Socio
from apps.pagos.models import SocioMembresia
from django.db.models import Prefetch
from django.utils import timezone
from apps.seguridad.servicios.FormularioSocio_Membresia import SocioForm, UsuarioForm, SocioMembresiaForm
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from apps.seguridad.decoradores import login_requerido, admin_requerido


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

        if rol_seleccionado.lower() != rol_real:
            messages.error(
                request, "No tienes permisos para iniciar sesión como ese rol."
            )
            return render(request, "seguridad/login.html", {"email": email})

        request.session["usuario_id"] = usuario.id
        request.session["usuario_email"] = usuario.Email
        request.session["usuario_rol"] = rol_real

        # No agregar mensaje aquí, se mostrará en el panel correspondiente

        if rol_real == "socio":
            return redirect("socio_panel")

        elif rol_real == "entrenador":
            return redirect("entrenador_panel")
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


@admin_requerido
def panel_admin_view(request):
    """Panel de administrador - requiere rol administrativo"""
    from apps.seguridad.servicios.estadisticas_dashboard import (
        obtener_estadisticas_dashboard,
        obtener_estadisticas_pagos_dashboard,
        obtener_actividad_plataforma
    )
    
    # Obtener todas las estadísticas desde el servicio
    estadisticas = obtener_estadisticas_dashboard()
    estadisticas_pagos = obtener_estadisticas_pagos_dashboard()
    actividad = obtener_actividad_plataforma()
    
    # Combinar todos los diccionarios
    context = {**estadisticas, **estadisticas_pagos, **actividad}
    
    return render(request, "Administrador/PaneldeInicio.html", context)


@admin_requerido
@ensure_csrf_cookie
def gestionar_usuarios_view(request):
    """Gestionar Socios y Usuarios (Administrativos, Entrenadores)"""
    from apps.pagos.models import PlanMembresia
    
    # Obtener filtros del request GET
    tipo_selected = request.GET.get('tipo', 'todos')
    plan_id = request.GET.get('plan_id', 'todos')
    
    # Prefetch memberships ordered by most recent FechaInicio first
    memb_qs = SocioMembresia.objects.order_by('-FechaInicio')
    
    # Obtener todos los planes disponibles
    planes = PlanMembresia.objects.all().order_by('Nombre')
    
    # Combinar socios y usuarios en una sola lista con información de tipo
    entidades = []
    
    # Agregar socios si el filtro lo permite
    if tipo_selected == 'todos' or tipo_selected == 'Socio':
        # Filtrar socios según el plan seleccionado
        if plan_id and plan_id != 'todos':
            socios = Socio.objects.prefetch_related(
                Prefetch('membresias', queryset=memb_qs, to_attr='membresias_ordered')
            ).filter(membresias__PlanID_id=plan_id).distinct()
        else:
            socios = Socio.objects.prefetch_related(
                Prefetch('membresias', queryset=memb_qs, to_attr='membresias_ordered')
            ).all()
        
        for socio in socios:
            # Obtener la fecha de registro (FechaInicio de la membresía más antigua)
            membresias = getattr(socio, 'membresias_ordered', [])
            fecha_registro = None
            if membresias:
                fecha_registro = membresias[-1].FechaInicio
            
            entidades.append({
                'tipo': 'Socio',
                'id': socio.id,
                'nombre': socio.NombreCompleto,
                'email': socio.Email,
                'rol': socio.Rol,
                'fecha_registro': fecha_registro,
                'membresias_ordered': membresias,
                'objeto': socio
            })
    
    # Agregar usuarios si el filtro lo permite
    if tipo_selected == 'todos' or tipo_selected in ['Administrativo', 'Entrenador']:
        usuarios = Usuario.objects.select_related('RolID').all()
        
        # Filtrar por tipo específico de usuario
        if tipo_selected == 'Administrativo':
            usuarios = usuarios.filter(RolID__NombreRol='Administrativo')
        elif tipo_selected == 'Entrenador':
            usuarios = usuarios.filter(RolID__NombreRol='Entrenador')
        
        for usuario in usuarios:
            entidades.append({
                'tipo': 'Usuario',
                'id': usuario.id,
                'nombre': usuario.NombreUsuario,
                'email': usuario.Email,
                'rol': usuario.RolID.NombreRol if usuario.RolID else 'N/A',
                'fecha_registro': timezone.now(),
                'membresias_ordered': [],
                'objeto': usuario
            })
    
    return render(request, "Administrador/GestionUsuario.html", {
        "entidades": entidades,
        "planes": planes,
        "plan_id_selected": plan_id,
        "tipo_selected": tipo_selected
    })


@admin_requerido
def seleccionar_tipo_usuario_view(request):
    """Seleccionar tipo de usuario antes de crear (Socio/Administrativo/Entrenador)"""
    if request.method == 'POST':
        tipo_usuario = request.POST.get('tipo_usuario')
        
        if tipo_usuario == 'Socio':
            return redirect('crear_socio')
        elif tipo_usuario in ['Administrativo', 'Entrenador']:
            return redirect('crear_usuario', tipo_rol=tipo_usuario)
    
    return render(request, "Administrador/seleccionar_tipo_usuario.html")


@admin_requerido
def crear_usuario_view(request, tipo_rol):
    """Crear un nuevo Usuario (Administrativo o Entrenador)"""
    
    # Validar que el tipo_rol sea válido
    if tipo_rol not in ['Administrativo', 'Entrenador']:
        messages.error(request, 'Tipo de usuario no válido.')
        return redirect('gestionar_usuarios')
    
    if request.method == 'POST':
        usuario_form = UsuarioForm(request.POST)
        if usuario_form.is_valid():
            usuario = usuario_form.save()
            messages.success(request, f"Usuario {usuario.Email} creado correctamente.")
            return redirect('gestionar_usuarios')
    else:
        usuario_form = UsuarioForm()
        # Pre-establecer el rol según el tipo seleccionado
        try:
            rol = Rol.objects.get(NombreRol=tipo_rol)
            usuario_form.fields['RolID'].initial = rol.id
        except Rol.DoesNotExist:
            pass
    
    return render(request, "Administrador/crearUsuario.html", {
        "form": usuario_form,
        "tipo_rol": tipo_rol
    })


@admin_requerido
def crear_socio_view(request):
    if request.method == "POST":
        socio_form = SocioForm(request.POST)
        if socio_form.is_valid():
            password = socio_form.cleaned_data.get('password')
            if not password:
                messages.error(request, "La contraseña es obligatoria al crear un socio.")
                return render(request, "Administrador/crearSocio.html", {"form": socio_form})
            
            # Guardar el socio
            socio = socio_form.save()
            
            # Crear el Usuario asociado para que pueda iniciar sesión
            from django.contrib.auth.hashers import make_password
            
            # Obtener el rol de Socio
            rol_socio = Rol.objects.get(NombreRol='Socio')
            
            # Crear el usuario
            usuario = Usuario.objects.create(
                NombreUsuario=socio.Identificacion,  # Usar identificación como username
                Email=socio.Email,
                PasswordHash=make_password(password),
                RolID=rol_socio
            )
            
            messages.success(request, f"Socio {socio.NombreCompleto} y usuario creados correctamente.")
            # Redirige al formulario de membresía con el socio recién creado
            return redirect("crear_membresia", socio_id=socio.id)
    else:
        socio_form = SocioForm()

    return render(request, "Administrador/crearSocio.html", {"form": socio_form})

@admin_requerido
def editar_socio_view(request, socio_id):
    """Editar un Socio existente"""
    socio = get_object_or_404(Socio, id=socio_id)

    if request.method == 'POST':
        socio_form = SocioForm(request.POST, instance=socio)
        if socio_form.is_valid():
            socio_form.save()
            
            # Si se proporcionó una nueva contraseña, actualizar el Usuario asociado
            password = socio_form.cleaned_data.get('password')
            if password:
                try:
                    # Buscar el usuario por la identificación del socio
                    usuario = Usuario.objects.get(NombreUsuario=socio.Identificacion)
                    from django.contrib.auth.hashers import make_password
                    usuario.PasswordHash = make_password(password)
                    usuario.Email = socio.Email  # Actualizar email también
                    usuario.save()
                    messages.success(request, f"Socio {socio.NombreCompleto} y contraseña actualizados correctamente.")
                except Usuario.DoesNotExist:
                    messages.warning(request, f"Socio actualizado, pero no se encontró usuario asociado para actualizar contraseña.")
            else:
                messages.success(request, f"Socio {socio.NombreCompleto} actualizado correctamente.")
            
            return redirect('gestionar_usuarios')
    else:
        socio_form = SocioForm(instance=socio)

    return render(request, "Administrador/editarSocio.html", {"form": socio_form, "socio": socio})


@admin_requerido
def editar_usuario_view(request, usuario_id):
    """Editar un Usuario existente"""
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        usuario_form = UsuarioForm(request.POST, instance=usuario)
        if usuario_form.is_valid():
            usuario_form.save()
            messages.success(request, f"Usuario {usuario.Email} actualizado correctamente.")
            return redirect('gestionar_usuarios')
    else:
        usuario_form = UsuarioForm(instance=usuario)

    return render(request, "Administrador/editarUsuario.html", {"form": usuario_form, "usuario": usuario})


@admin_requerido
def crear_membresia_view(request, socio_id):
    socio = get_object_or_404(Socio, id=socio_id)

    if request.method == "POST":
        membresia_form = SocioMembresiaForm(request.POST)
        if membresia_form.is_valid():
            membresia = membresia_form.save(commit=False)
            membresia.SocioID = socio
            membresia.save()
            messages.success(request, f"Membresía creada para {socio.NombreCompleto}.")
            return redirect("gestionar_usuarios")
    else:
        membresia_form = SocioMembresiaForm()

    return render(
        request,
        "Administrador/crearMembresia.html",
        {"form": membresia_form, "socio": socio},
    )


@admin_requerido
@require_http_methods(["POST"])
def eliminar_entidad_view(request, tipo, entidad_id):
    """
    Elimina una entidad (Socio o Usuario) y todas sus datos asociados.
    Requiere método POST y devuelve JSON.
    
    Args:
        tipo: 'Socio' o 'Usuario' (se normaliza a minúsculas)
        entidad_id: ID de la entidad a eliminar
    """
    
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    # Normalizar tipo a minúsculas para comparación
    tipo_normalizado = tipo.lower()
    
    try:
        if tipo_normalizado == 'socio':
            socio = Socio.objects.get(id=entidad_id)
            nombre = socio.NombreCompleto
            email = socio.Email
            socio.delete()
            mensaje = f'Socio {nombre} ({email}) eliminado correctamente.'
        
        elif tipo_normalizado == 'usuario':
            usuario = Usuario.objects.get(id=entidad_id)
            nombre = usuario.NombreUsuario
            email = usuario.Email
            usuario.delete()
            mensaje = f'Usuario {nombre} ({email}) eliminado correctamente.'
        
        else:
            return JsonResponse({'success': False, 'error': 'Tipo de entidad no válido'}, status=400)
        
        return JsonResponse({
            'success': True,
            'message': mensaje
        })
    
    except Socio.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Socio no encontrado'}, status=404)
    except Usuario.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def eliminar_socio_view(request, socio_id):
    """
    Elimina un socio y todas sus membresías asociadas.
    Requiere método POST y devuelve JSON.
    (Vista legada - ahora usa eliminar_entidad_view)
    """
    return eliminar_entidad_view(request, 'socio', socio_id)

