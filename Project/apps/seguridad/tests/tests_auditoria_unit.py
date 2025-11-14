from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock


class AuditoriaUnitTests(SimpleTestCase):
    """
    Tests unitarios puros para registrar_evento_auditoria(),
    sin usar base de datos (RegistroAuditoria está mockeado).
    """

    @patch("apps.seguridad.servicios.autenticacion.RegistroAuditoria")
    def test_registrar_evento_con_usuario(self, MockRegistroAuditoria):
        """
        Debe crear un registro de auditoría cuando se pasa un usuario.
        """
        from apps.seguridad.servicios.autenticacion import registrar_evento_auditoria

        mock_user = MagicMock()

        resultado = registrar_evento_auditoria(
            usuario=mock_user,
            tipo_accion="LOGIN_EXITOSO",
            detalle="Inicio de sesión correcto",
        )

        MockRegistroAuditoria.objects.create.assert_called_once_with(
            UsuarioID=mock_user,
            TipoAccion="LOGIN_EXITOSO",
            Detalle="Inicio de sesión correcto",
        )

        self.assertIs(
            resultado,
            MockRegistroAuditoria.objects.create.return_value
        )

    @patch("apps.seguridad.servicios.autenticacion.RegistroAuditoria")
    def test_registrar_evento_sin_usuario(self, MockRegistroAuditoria):
        """
        Debe permitir registrar un evento con usuario=None (por ejemplo, login fallido).
        """
        from apps.seguridad.servicios.autenticacion import registrar_evento_auditoria

        resultado = registrar_evento_auditoria(
            usuario=None,
            tipo_accion="LOGIN_FALLIDO",
            detalle="Intento de acceso con usuario inexistente: alguien",
        )

        MockRegistroAuditoria.objects.create.assert_called_once_with(
            UsuarioID=None,
            TipoAccion="LOGIN_FALLIDO",
            Detalle="Intento de acceso con usuario inexistente: alguien",
        )

        self.assertIs(
            resultado,
            MockRegistroAuditoria.objects.create.return_value
        )
