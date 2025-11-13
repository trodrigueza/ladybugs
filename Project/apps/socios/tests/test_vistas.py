from django.test import TestCase
from django.urls import reverse
from apps.socios.models import Socio

class RegisterViewTest(TestCase):
    
    def setUp(self):
        self.register_url = reverse('register')
        
        self.valid_data = {
            'identificacion': "1020304050",
            'full_name': "Socio de Prueba View",
            'phone': "+57 3001234567",
            'email': "view@valido.com",
            'birthdate': '2000-01-01',
            'consent': 'on', 
            'password': "ClaveSegura123",
            'confirm_password': "ClaveSegura123",
            'health_status': "Sin antecedentes",
        }

    def test_get_register_page(self):

        response = self.client.get(self.register_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'socio/register.html')

    def test_post_register_success(self):
        response = self.client.post(self.register_url, self.valid_data)
        
        self.assertEqual(Socio.objects.count(), 1)
        self.assertEqual(Socio.objects.first().Email, "view@valido.com")
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login')) # Asumiendo name='login'

        response_followed = self.client.post(self.register_url, self.valid_data, follow=True)
        messages = list(response_followed.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Cuenta creada correctamente. Puedes iniciar sesión.")

    def test_post_password_mismatch(self):
        invalid_data = self.valid_data.copy()
        invalid_data['confirm_password'] = "ESTA_ES_DIFERENTE"
        
        response = self.client.post(self.register_url, invalid_data)
        
        self.assertEqual(Socio.objects.count(), 0)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'socio/register.html')

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Las contraseñas no coinciden.")

    def test_post_service_validation_error(self):
        invalid_data = self.valid_data.copy()
        invalid_data['phone'] = "3001234567" 
        
        response = self.client.post(self.register_url, invalid_data)
        
        self.assertEqual(Socio.objects.count(), 0)
        
        self.assertEqual(response.status_code, 200)
        
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("El teléfono debe iniciar con '+57 3'", str(messages[0]))