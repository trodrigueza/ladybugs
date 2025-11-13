# apps/seguridad/tests/test_vistas.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password

from apps.seguridad.models import Rol, Usuario


class LoginViewTests(TestCase):

    def setUp(self):
        self.url_login = reverse("login")
        self.rol = Rol.objects.create(NombreRol="Administrador")
        self.usuario = Usuario.objects.create(
            NombreUsuario="admin",
            PasswordHash=make_password("secreto123"),
            RolID=self.rol,
        )

    def test_get_login_retorna_200(self):
        response = self.client.get(self.url_login)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "seguridad/login.html")

    def test_post_login_credenciales_invalidas(self):
        data = {"username": "admin", "password": "malapass"}
        response = self.client.post(self.url_login, data)
        # No redirige, se queda en la misma página
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "seguridad/login.html")
        # Debe mostrar mensaje de error (si usas messages)
        messages = list(response.context["messages"])
        self.assertTrue(any("incorrectos" in str(m) for m in messages))

    def test_post_login_exitoso_redirige_home(self):
        data = {"username": "admin", "password": "secreto123"}
        response = self.client.post(self.url_login, data)
        # Redirige (302) a 'home'
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), reverse("home"))
        # Sesión debe tener el usuario_id
        session = self.client.session
        self.assertEqual(session.get("usuario_id"), self.usuario.id)
