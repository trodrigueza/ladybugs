from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock


class LogoutUnitTests(SimpleTestCase):
    """
    Tests  registrar_logout(),
    """

    @patch("apps.seguridad.servicios.autenticacion.registrar_evento_auditoria")
    def test_logout_registra_evento(self, mock_registrar_evento):
        """
        Si hay un usuario, registrar_logout() debe registrar un evento LOGOUT.
        """
        from apps.seguridad.servicios.autenticacion import registrar_logout

        mock_user = MagicMock()

        registrar_logout(mock_user)

        mock_registrar_evento.assert_called_once()
        args, kwargs = mock_registrar_evento.call_args
        self.assertIs(kwargs["usuario"], mock_user)
        self.assertEqual(kwargs["tipo_accion"], "LOGOUT")
        self.assertEqual(kwargs["detalle"], "Cierre de sesión")

    @patch("apps.seguridad.servicios.autenticacion.registrar_evento_auditoria")
    def test_logout_sin_usuario_no_registra_evento(self, mock_registrar_evento):
        """
        Si usuario es None, NO debe registrar un evento.
        """
        from apps.seguridad.servicios.autenticacion import registrar_logout

        registrar_logout(None)

        mock_registrar_evento.assert_not_called()
