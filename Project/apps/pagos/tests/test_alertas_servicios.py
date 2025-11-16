from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.pagos.models import PlanMembresia, SocioMembresia, AlertaPago
from apps.pagos.servicios.pagos_service import (
    ValidationError,
    crear_membresia_para_socio,
    generar_alerta_morosidad,
)
from apps.socios.models import Socio


class AlertasPagoServicioTest(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(
            Identificacion="7777777777",
            NombreCompleto="Socio Alertas",
            Email="alertas@test.com",
            Telefono="+57 3000000003",
            ConsentimientoDatos=True,
            SaludBasica="Sin antecedentes",
        )

        self.plan = PlanMembresia.objects.create(
            Nombre="Plan Mensual Alertas",
            Precio=Decimal("30000.00"),
            DuracionDias=30,
            Beneficios="Acceso 1 mes",
        )
        self.hoy = timezone.localdate()

    def test_generar_alerta_para_membresia_morosa_sin_duplicar(self):
        """Genera una única alerta para membresía morosa (idempotente)."""
        membresia = crear_membresia_para_socio(
            socio_id=self.socio.id,
            plan_id=self.plan.id,
            fecha_inicio=self.hoy,
        )
        membresia.Estado = SocioMembresia.ESTADO_MOROSA
        membresia.save(update_fields=["Estado"])

        alerta1 = generar_alerta_morosidad(membresia.id)
        alerta2 = generar_alerta_morosidad(membresia.id)

        self.assertIsInstance(alerta1, AlertaPago)
        self.assertEqual(alerta1.id, alerta2.id)
        self.assertEqual(AlertaPago.objects.count(), 1)
        self.assertFalse(alerta1.VistaEnPanel)

    def test_no_generar_alerta_si_membresia_no_morosa(self):
        """No permite generar alerta si la membresía no está morosa."""
        membresia = crear_membresia_para_socio(
            socio_id=self.socio.id,
            plan_id=self.plan.id,
            fecha_inicio=self.hoy,
        )
        self.assertEqual(membresia.Estado, SocioMembresia.ESTADO_ACTIVA)

        with self.assertRaises(ValidationError):
            generar_alerta_morosidad(membresia.id)

        self.assertEqual(AlertaPago.objects.count(), 0)