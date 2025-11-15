from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.control_acceso.models import Asistencia
from apps.control_acceso.servicios.asistencia_service import (
    ValidationError,
    obtener_asistencia_activa,
    registrar_entrada,
    registrar_salida,
)
from apps.pagos.models import PlanMembresia, SocioMembresia
from apps.socios.models import Socio


class AsistenciaServicioTest(TestCase):
    def setUp(self):
        # Crear socio de prueba
        self.socio = Socio.objects.create(
            Identificacion="1234567890",
            NombreCompleto="Juan Pérez",
            Email="juan@test.com",
            Telefono="+57 3001234567",
            ConsentimientoDatos=True,
            SaludBasica="Saludable",
        )

        # Crear plan de membresía
        self.plan = PlanMembresia.objects.create(
            Nombre="Plan Mensual",
            Precio=100000.00,
            DuracionDias=30,
            Beneficios="Acceso completo",
        )

        # Crear membresía activa
        hoy = timezone.localdate()
        self.membresia_activa = SocioMembresia.objects.create(
            SocioID=self.socio,
            PlanID=self.plan,
            FechaInicio=hoy - timedelta(days=5),
            FechaFin=hoy + timedelta(days=25),
            Estado=SocioMembresia.ESTADO_ACTIVA,
        )

        # Crear membresía expirada
        self.membresia_expirada = SocioMembresia.objects.create(
            SocioID=self.socio,
            PlanID=self.plan,
            FechaInicio=hoy - timedelta(days=60),
            FechaFin=hoy - timedelta(days=30),
            Estado=SocioMembresia.ESTADO_EXPIRADA,
        )

    def test_registrar_entrada_exitosa(self):
        """
        Test: Registrar entrada exitosa con membresía activa
        """
        asistencia = registrar_entrada(
            self.membresia_activa.id, terminal_acceso="Terminal 1"
        )

        self.assertIsInstance(asistencia, Asistencia)
        self.assertEqual(asistencia.SocioMembresiaID.id, self.membresia_activa.id)
        self.assertIsNotNone(asistencia.FechaHoraEntrada)
        self.assertIsNone(asistencia.FechaHoraSalida)
        self.assertEqual(asistencia.TerminalAcceso, "Terminal 1")
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_registrar_entrada_membresia_inactiva(self):
        """
        Test: No se puede registrar entrada con membresía expirada
        """
        with self.assertRaises(ValidationError) as context:
            registrar_entrada(self.membresia_expirada.id)

        self.assertIn("no está activa", str(context.exception))
        self.assertEqual(Asistencia.objects.count(), 0)

    def test_registrar_entrada_duplicada(self):
        """
        Test: No se puede registrar entrada si ya hay una entrada activa sin salida
        """
        # Primera entrada exitosa
        registrar_entrada(self.membresia_activa.id)

        # Intentar segunda entrada sin haber registrado salida
        with self.assertRaises(ValidationError) as context:
            registrar_entrada(self.membresia_activa.id)

        self.assertIn("entrada activa", str(context.exception))
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_registrar_salida_exitosa(self):
        """
        Test: Registrar salida exitosa
        """
        # Primero registrar entrada
        asistencia = registrar_entrada(self.membresia_activa.id)
        asistencia_id = asistencia.id

        # Registrar salida
        asistencia_actualizada = registrar_salida(asistencia_id)

        self.assertIsNotNone(asistencia_actualizada.FechaHoraSalida)
        self.assertGreater(
            asistencia_actualizada.FechaHoraSalida,
            asistencia_actualizada.FechaHoraEntrada,
        )

    def test_registrar_salida_duplicada(self):
        """
        Test: No se puede registrar salida dos veces
        """
        # Registrar entrada y salida
        asistencia = registrar_entrada(self.membresia_activa.id)
        registrar_salida(asistencia.id)

        # Intentar registrar salida nuevamente
        with self.assertRaises(ValidationError) as context:
            registrar_salida(asistencia.id)

        self.assertIn("ya tiene una salida registrada", str(context.exception))

    def test_obtener_asistencia_activa(self):
        """
        Test: Obtener asistencia activa (sin salida) de un socio
        """
        # Crear entrada sin salida
        registrar_entrada(self.membresia_activa.id)

        # Obtener asistencia activa
        asistencia_activa = obtener_asistencia_activa(self.membresia_activa.id)

        self.assertIsNotNone(asistencia_activa)
        self.assertIsNone(asistencia_activa.FechaHoraSalida)

        # Registrar salida y verificar que ya no hay asistencia activa
        registrar_salida(asistencia_activa.id)
        asistencia_cerrada = obtener_asistencia_activa(self.membresia_activa.id)

        self.assertIsNone(asistencia_cerrada)
