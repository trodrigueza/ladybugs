# apps/seguridad/tests/test_servicios.py

from django.test import TestCase
from django.contrib.auth.hashers import make_password

from apps.seguridad.models import Rol, Usuario, RegistroAuditoria
from apps.seguridad.servicios.autenticacion import autenticar_usuario


class AutenticacionServiciosTests(TestCase):

    def setUp(self):
        self.rol = Rol.objects.create(NombreRol="Administrador")
        self.usuario = Usuario.objects.create(
            NombreUsuario="admin",
            PasswordHash=make_password("secreto123"),
            RolID=self.rol,
        )

    def test_login_exitoso(self):
        usuario = autenticar_usuario("admin", "secreto123")
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.id, self.usuario.id)

        # UltimoAcceso se debe haber actualizado
        usuario.refresh_from_db()
        self.assertIsNotNone(usuario.UltimoAcceso)

        # Debe existir un registro de auditoría de LOGIN_EXITOSO
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                UsuarioID=usuario,
                TipoAccion="LOGIN_EXITOSO",
            ).exists()
        )

    def test_login_fallido_contraseña_incorrecta(self):
        usuario = autenticar_usuario("admin", "clave_mala")
        self.assertIsNone(usuario)

        self.assertTrue(
            RegistroAuditoria.objects.filter(
                UsuarioID=self.usuario,
                TipoAccion="LOGIN_FALLIDO",
                Detalle__icontains="Contraseña incorrecta",
            ).exists()
        )

    def test_login_usuario_inexistente(self):
        usuario = autenticar_usuario("no_existo", "loquesea")
        self.assertIsNone(usuario)

        self.assertTrue(
            RegistroAuditoria.objects.filter(
                UsuarioID__isnull=True,
                TipoAccion="LOGIN_FALLIDO",
                Detalle__icontains="usuario inexistente",
            ).exists()
        )
