from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.control_acceso.servicios.asistencia_service import (
    ValidationError,
    validar_membresia_activa,
)
from apps.pagos.models import PlanMembresia, SocioMembresia
from apps.socios.models import Socio


class ValidacionesAsistenciaTest(TestCase):
    def setUp(self):
        # Crear socio
        self.socio = Socio.objects.create(
            Identificacion="1234567890",
            NombreCompleto="Carlos Ruiz",
            Email="carlos@test.com",
            Telefono="+57 3001112233",
            ConsentimientoDatos=True,
            SaludBasica="Saludable",
        )

        # Crear plan
        self.plan = PlanMembresia.objects.create(
            Nombre="Plan Anual",
            Precio=1000000.00,
            DuracionDias=365,
            Beneficios="Acceso ilimitado",
        )

        hoy = timezone.localdate()

        # Membresía activa
        self.membresia_activa = SocioMembresia.objects.create(
            SocioID=self.socio,
            PlanID=self.plan,
            FechaInicio=hoy - timedelta(days=10),
            FechaFin=hoy + timedelta(days=355),
            Estado=SocioMembresia.ESTADO_ACTIVA,
        )

        # Membresía morosa
        self.membresia_morosa = SocioMembresia.objects.create(
            SocioID=self.socio,
            PlanID=self.plan,
            FechaInicio=hoy - timedelta(days=60),
            FechaFin=hoy + timedelta(days=30),
            Estado=SocioMembresia.ESTADO_MOROSA,
        )

        # Membresía expirada
        self.membresia_expirada = SocioMembresia.objects.create(
            SocioID=self.socio,
            PlanID=self.plan,
            FechaInicio=hoy - timedelta(days=400),
            FechaFin=hoy - timedelta(days=35),
            Estado=SocioMembresia.ESTADO_EXPIRADA,
        )

    def test_validacion_membresia_activa_exitosa(self):
        """
        Test: Validación exitosa de membresía activa
        """
        # No debe lanzar excepción
        try:
            validar_membresia_activa(self.membresia_activa)
            validacion_exitosa = True
        except ValidationError:
            validacion_exitosa = False

        self.assertTrue(validacion_exitosa)

    def test_validacion_membresia_morosa_falla(self):
        """
        Test: Membresía morosa no pasa la validación
        """
        with self.assertRaises(ValidationError) as context:
            validar_membresia_activa(self.membresia_morosa)

        self.assertIn("no está activa", str(context.exception))

    def test_validacion_membresia_expirada_falla(self):
        """
        Test: Membresía expirada no pasa la validación
        """
        with self.assertRaises(ValidationError) as context:
            validar_membresia_activa(self.membresia_expirada)

        self.assertIn("no está activa", str(context.exception))

    def test_is_active_method_membresia_activa(self):
        """
        Test: Método is_active() retorna True para membresía activa
        """
        self.assertTrue(self.membresia_activa.is_active())

    def test_is_active_method_membresia_morosa(self):
        """
        Test: Método is_active() retorna False para membresía morosa
        """
        self.assertFalse(self.membresia_morosa.is_active())

    def test_is_active_method_membresia_expirada(self):
        """
        Test: Método is_active() retorna False para membresía expirada
        """
        self.assertFalse(self.membresia_expirada.is_active())

    def test_remaining_days_membresia_activa(self):
        """
        Test: Días restantes se calculan correctamente
        """
        dias_restantes = self.membresia_activa.remaining_days()
        self.assertEqual(dias_restantes, 355)

    def test_remaining_days_membresia_expirada(self):
        """
        Test: Días restantes de membresía expirada es negativo
        """
        dias_restantes = self.membresia_expirada.remaining_days()
        self.assertLess(dias_restantes, 0)
