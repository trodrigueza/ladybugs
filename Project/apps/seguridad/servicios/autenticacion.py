from django.contrib.auth.hashers import check_password
from django.utils import timezone
from apps.seguridad.models import Usuario, RegistroAuditoria
from django.contrib.auth.hashers import make_password


def registrar_evento_auditoria(usuario, tipo_accion, detalle):

    return RegistroAuditoria.objects.create(
        UsuarioID=usuario,
        TipoAccion=tipo_accion,
        Detalle=detalle,
    )


def autenticar_usuario(email, password_plano):

    try:
        usuario = Usuario.objects.get(Email=email)
    except Usuario.DoesNotExist:
        registrar_evento_auditoria(
            usuario=None,
            tipo_accion="LOGIN_FALLIDO",
            detalle=f"Intento de acceso con email inexistente: {email}",
        )
        return None

    if check_password(password_plano, usuario.PasswordHash):
        usuario.UltimoAcceso = timezone.now()
        usuario.save(update_fields=["UltimoAcceso"])

        registrar_evento_auditoria(
            usuario=usuario,
            tipo_accion="LOGIN_EXITOSO",
            detalle="Inicio de sesión correcto",
        )
        return usuario

    try:
        if usuario.PasswordHash == password_plano:
            usuario.PasswordHash = make_password(password_plano)
            usuario.UltimoAcceso = timezone.now()
            usuario.save(update_fields=["PasswordHash", "UltimoAcceso"])

            registrar_evento_auditoria(
                usuario=usuario,
                tipo_accion="LOGIN_EXITOSO",
                detalle="Inicio de sesión correcto (upgrade de hash)",
            )
            return usuario
    except Exception:
    
        pass

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
