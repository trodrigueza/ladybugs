from django.test import TestCase
from apps.socios.servicios.registro_db import validate_socio_data, ValidationError

class ValidacionSocioTest(TestCase):

    def setUp(self):
        self.base_data = {
            'identificacion': "1020304050",
            'full_name': "Socio de Prueba",
            'phone': "+57 3001234567",
            'email': "prueba@valido.com",
            'password': "ClaveSegura123",
            'health_status': "Sin antecedentes",
        }

    def test_falla_password_corto(self):
        invalid_data = self.base_data.copy()
        invalid_data['password'] = "Pass123"
        with self.assertRaises(ValidationError):
            validate_socio_data(invalid_data)

    def test_falla_identificacion_longitud(self):
        invalid_data = self.base_data.copy()
        invalid_data['identificacion'] = "123456789" 
        with self.assertRaises(ValidationError):
            validate_socio_data(invalid_data)

    def test_falla_telefono_prefijo(self):
        invalid_data = self.base_data.copy()
        invalid_data['phone'] = "3001234567"
        with self.assertRaises(ValidationError):
            validate_socio_data(invalid_data)