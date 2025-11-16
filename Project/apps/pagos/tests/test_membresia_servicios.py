from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.pagos.models import PlanMembresia, SocioMembresia
from apps.pagos.servicios.pagos_service import (
    ValidationError,
    crear_membresia_para_socio,
)
from apps.socios.models import Socio


class CrearMembresiaServicioTest(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(
            Identificacion="5555555555",
            NombreCompleto="Socio Pagos Membresia",
            Email="membresia@test.com",
            Telefono="+57 3000000001",
            ConsentimientoDatos=True,
            SaludBasica="Sin antecedentes",
        )

        self.plan = PlanMembresia.objects.create(
            Nombre="Plan Mensual Pagos",
            Precio=Decimal("30000.00"),
            DuracionDias=30,
            Beneficios="Acceso 1 mes",
        )
        self.hoy = timezone.localdate()

    def test_crear_membresia_calcula_fechas_y_estado_activa(self):
        """Crear membresía calcula FechaFin y queda en estado ACTIVA."""
        membresia = crear_membresia_para_socio(
            socio_id=self.socio.id,
            plan_id=self.plan.id,
            fecha_inicio=self.hoy,
        )

        self.assertEqual(membresia.SocioID, self.socio)
        self.assertEqual(membresia.PlanID, self.plan)
        self.assertEqual(membresia.FechaInicio, self.hoy)
        self.assertEqual(
            membresia.FechaFin,
            self.hoy + timedelta(days=self.plan.DuracionDias),
        )
        self.assertEqual(membresia.Estado, SocioMembresia.ESTADO_ACTIVA)

    def test_no_crea_segunda_membresia_activa_solapada(self):
        """No permite crear otra membresía activa que se solape en fechas."""
        crear_membresia_para_socio(
            socio_id=self.socio.id,
            plan_id=self.plan.id,
            fecha_inicio=self.hoy,
        )

        with self.assertRaises(ValidationError) as ctx:
            crear_membresia_para_socio(
                socio_id=self.socio.id,
                plan_id=self.plan.id,
                fecha_inicio=self.hoy + timedelta(days=5),
            )

        self.assertIn("ya tiene una membresía activa", str(ctx.exception))
        self.assertEqual(SocioMembresia.objects.count(), 1)