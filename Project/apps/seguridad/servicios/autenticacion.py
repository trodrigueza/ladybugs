# seguridad/servicios/autenticacion.py

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from apps.seguridad.models import Usuario, RegistroAuditoria


def registrar_evento_auditoria(usuario, tipo_accion, detalle):
    """
    Crea un registro de auditoría.
    usuario puede ser None (login fallido de usuario inexistente).
    """
    return RegistroAuditoria.objects.create(
        UsuarioID=usuario,
        TipoAccion=tipo_accion,
        Detalle=detalle,
    )


def autenticar_usuario(nombre_usuario, password_plano):
    """
    Verifica usuario y contraseña contra la tabla Usuario.
    Devuelve el objeto Usuario si las credenciales son correctas, si no, None.
    Además:
      - Actualiza UltimoAcceso en login exitoso.
      - Registra auditoría de login exitoso / fallido.
    """
    try:
        usuario = Usuario.objects.get(NombreUsuario=nombre_usuario)
    except Usuario.DoesNotExist:
        registrar_evento_auditoria(
            usuario=None,
            tipo_accion="LOGIN_FALLIDO",
            detalle=f"Intento de acceso con usuario inexistente: {nombre_usuario}",
        )
        return None

    # Compara el password plano con el hash almacenado
    if check_password(password_plano, usuario.PasswordHash):
        usuario.UltimoAcceso = timezone.now()
        usuario.save(update_fields=["UltimoAcceso"])

        registrar_evento_auditoria(
            usuario=usuario,
            tipo_accion="LOGIN_EXITOSO",
            detalle="Inicio de sesión correcto",
        )
        return usuario

    # Contraseña incorrecta
    registrar_evento_auditoria(
        usuario=usuario,
        tipo_accion="LOGIN_FALLIDO",
        detalle="Contraseña incorrecta",
    )
    return None


def registrar_logout(usuario):
   
    if usuario is None:
        return

    registrar_evento_auditoria(
        usuario=usuario,
        tipo_accion="LOGOUT",
        detalle="Cierre de sesión",
    )
