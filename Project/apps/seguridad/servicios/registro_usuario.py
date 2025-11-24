from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from apps.seguridad.models import Usuario, Rol


def crear_usuario_para_socio(socio, password_plano):

    rol_socio, _ = Rol.objects.get_or_create(NombreRol="Socio")

    try:
        usuario, creado = Usuario.objects.get_or_create(
            Email=socio.Email,
            defaults={
                "NombreUsuario": socio.Email,  
                "PasswordHash": make_password(password_plano),
                "RolID": rol_socio,
            },
        )

        if not creado:
            usuario.PasswordHash = make_password(password_plano)
            usuario.RolID = rol_socio
            usuario.save(update_fields=["PasswordHash", "RolID"])

        return usuario

    except IntegrityError:
        return None
