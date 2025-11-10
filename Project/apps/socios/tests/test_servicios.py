from django.test import TestCase
from apps.socios.servicios.registro_db import create_socio_from_dict, ValidationError
from apps.socios.models import Socio

class ServicioCreacionSocioTest(TestCase):

    def setUp(self):
        self.valid_data = {
            'identificacion': "1020304050",
            'full_name': "Socio de Prueba",
            'phone': "+57 3001234567",
            'email': "prueba@valido.com",
            'password': "ClaveSegura123",
            'health_status': "Sin antecedentes",
            'birthdate': '2000-01-01',
            'consent': True,
        }

    def test_creacion_exitosa_socio(self):
        socio = create_socio_from_dict(self.valid_data)
        self.assertIsInstance(socio, Socio)
        self.assertEqual(socio.Email, "prueba@valido.com")
        self.assertEqual(Socio.objects.count(), 1)

    def test_falla_email_duplicado(self):
        create_socio_from_dict(self.valid_data)
        
        data_duplicada = self.valid_data.copy()
        data_duplicada['identificacion'] = "9876543210" 
        
        with self.assertRaises(ValidationError):
            create_socio_from_dict(data_duplicada)