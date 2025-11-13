# apps/seguridad/tests/test_modelos.py

from django.test import TestCase

from apps.seguridad.models import Rol, Usuario, RegistroAuditoria
from django.contrib.auth.hashers import make_password


class ModelosSeguridadTests(TestCase):

    def test_str_rol(self):
        rol = Rol.objects.create(NombreRol="Administrador")
        self.assertEqual(str(rol), "Administrador")

    def test_str_usuario(self):
        rol = Rol.objects.create(NombreRol="Cajero")
        usuario = Usuario.objects.create(
            NombreUsuario="cajero1",
            PasswordHash=make_password("clave123"),
            RolID=rol,
        )
        self.assertEqual(str(usuario), "cajero1")

    def test_creacion_registro_auditoria(self):
        rol = Rol.objects.create(NombreRol="Monitor")
        usuario = Usuario.objects.create(
            NombreUsuario="monitor1",
            PasswordHash=make_password("otraClave"),
            RolID=rol,
        )

        registro = RegistroAuditoria.objects.create(
            UsuarioID=usuario,
            TipoAccion="PRUEBA",
            Detalle="Registro de prueba de auditoría",
        )

        self.assertIsNotNone(registro.id)
        self.assertEqual(registro.UsuarioID, usuario)
        self.assertEqual(registro.TipoAccion, "PRUEBA")
        self.assertTrue(registro.FechaHora is not None)
