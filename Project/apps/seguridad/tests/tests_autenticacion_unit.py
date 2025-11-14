from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock


class AutenticacionUnitTests(SimpleTestCase):
    """
    Tests autenticar_usuario,
    """

    @patch("apps.seguridad.servicios.autenticacion.registrar_evento_auditoria")
    @patch("apps.seguridad.servicios.autenticacion.check_password")
    @patch("apps.seguridad.servicios.autenticacion.Usuario")
    def test_login_exitoso(
        self,
        MockUsuario,
        mock_check_password,
        mock_registrar_evento,
    ):

        mock_user = MagicMock()
        MockUsuario.objects.get.return_value = mock_user

        mock_check_password.return_value = True

        from apps.seguridad.servicios.autenticacion import autenticar_usuario

        user = autenticar_usuario("tester", "secreto123")

        self.assertIs(user, mock_user)

        MockUsuario.objects.get.assert_called_once_with(NombreUsuario="tester")

        #login exitoso
        mock_registrar_evento.assert_called_once()
        args, kwargs = mock_registrar_evento.call_args
        self.assertIs(kwargs["usuario"], mock_user)
        self.assertEqual(kwargs["tipo_accion"], "LOGIN_EXITOSO")
        self.assertEqual(kwargs["detalle"], "Inicio de sesión correcto")

        mock_user.save.assert_called_once_with(update_fields=["UltimoAcceso"])

    @patch("apps.seguridad.servicios.autenticacion.registrar_evento_auditoria")
    @patch("apps.seguridad.servicios.autenticacion.Usuario")
    def test_login_usuario_inexistente(
        self,
        MockUsuario,
        mock_registrar_evento,
    ):
        """
        Simulacio2n: Usuario.objects.get lanza la excepción Usuario.DoesNotExist
        de forma correcta - Exception real).
        """

        class FakeDoesNotExist(Exception):
            pass

        MockUsuario.DoesNotExist = FakeDoesNotExist
        MockUsuario.objects.get.side_effect = FakeDoesNotExist

        from apps.seguridad.servicios.autenticacion import autenticar_usuario

        user = autenticar_usuario("no_existo", "loquesea")

        self.assertIsNone(user)

        mock_registrar_evento.assert_called_once()
        args, kwargs = mock_registrar_evento.call_args
        self.assertIsNone(kwargs["usuario"])
        self.assertEqual(kwargs["tipo_accion"], "LOGIN_FALLIDO")
        self.assertIn("usuario inexistente", kwargs["detalle"])

    @patch("apps.seguridad.servicios.autenticacion.registrar_evento_auditoria")
    @patch("apps.seguridad.servicios.autenticacion.check_password")
    @patch("apps.seguridad.servicios.autenticacion.Usuario")
    def test_login_contraseña_incorrecta(
        self,
        MockUsuario,
        mock_check_password,
        mock_registrar_evento,
    ):
        
        mock_user = MagicMock()
        MockUsuario.objects.get.return_value = mock_user

        mock_check_password.return_value = False

        from apps.seguridad.servicios.autenticacion import autenticar_usuario

        user = autenticar_usuario("tester", "clave_mala")

        self.assertIsNone(user)

        # Se registra login fallido con ese usuario
        mock_registrar_evento.assert_called_once()
        args, kwargs = mock_registrar_evento.call_args
        self.assertIs(kwargs["usuario"], mock_user)
        self.assertEqual(kwargs["tipo_accion"], "LOGIN_FALLIDO")
        self.assertEqual(kwargs["detalle"], "Contraseña incorrecta")
