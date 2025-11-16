from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.pagos.models import PlanMembresia, SocioMembresia, Pago
from apps.pagos.servicios.pagos_service import (
    ValidationError,
    crear_membresia_para_socio,
    registrar_pago_membresia,
)
from apps.socios.models import Socio


class RegistrarPagoServicioTest(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(
            Identificacion="6666666666",
            NombreCompleto="Socio Pagos Servicio",
            Email="pagos_servicio@test.com",
            Telefono="+57 3000000002",
            ConsentimientoDatos=True,
            SaludBasica="Sin antecedentes",
        )

        self.plan = PlanMembresia.objects.create(
            Nombre="Plan Trimestral Pagos",
            Precio=Decimal("90000.00"),
            DuracionDias=90,
            Beneficios="Acceso 3 meses",
        )
        self.hoy = timezone.localdate()

        self.membresia = crear_membresia_para_socio(
            socio_id=self.socio.id,
            plan_id=self.plan.id,
            fecha_inicio=self.hoy,
        )
        # Partimos de estado MOROSA para simular deuda
        self.membresia.Estado = SocioMembresia.ESTADO_MOROSA
        self.membresia.save(update_fields=["Estado"])

    def test_pago_parcial_actualiza_monto_pendiente_y_estado_morosa(self):
        """Pago parcial deja saldo pendiente y mantiene estado MOROSA."""
        pago = registrar_pago_membresia(
            socio_membresia_id=self.membresia.id,
            monto=Decimal("30000.00"),
            tipo_pago="efectivo",
        )

        self.membresia.refresh_from_db()

        self.assertIsInstance(pago, Pago)
        self.assertEqual(pago.Monto, Decimal("30000.00"))
        self.assertEqual(pago.MontoPendiente, Decimal("60000.00"))
        self.assertEqual(self.membresia.Estado, SocioMembresia.ESTADO_MOROSA)

    def test_pago_completo_deja_sin_saldo_y_estado_activa(self):
        """Pago que completa el valor del plan deja la membresía ACTIVA."""
        pago = registrar_pago_membresia(
            socio_membresia_id=self.membresia.id,
            monto=Decimal("90000.00"),
            tipo_pago="tarjeta",
        )

        self.membresia.refresh_from_db()

        self.assertEqual(pago.MontoPendiente, Decimal("0.00"))
        self.assertEqual(self.membresia.Estado, SocioMembresia.ESTADO_ACTIVA)

    def test_monto_negativo_lanza_validation_error(self):
        """No se aceptan pagos con monto negativo o cero."""
        with self.assertRaises(ValidationError):
            registrar_pago_membresia(
                socio_membresia_id=self.membresia.id,
                monto=Decimal("-1.00"),
            )

        self.assertEqual(Pago.objects.count(), 0)