from decimal import Decimal

from django.test import TestCase

from apps.control_acceso.models import DiaRutinaEjercicio, Ejercicio, RutinaSemanal
from apps.control_acceso.servicios.rutina_service import (
    ValidationError,
    asignar_ejercicio_a_rutina,
    crear_rutina_semanal,
    obtener_ejercicios_por_dia,
)
from apps.socios.models import Socio


class RutinaServicioTest(TestCase):
    def setUp(self):
        # Crear socio de prueba
        self.socio = Socio.objects.create(
            Identificacion="1234567890",
            NombreCompleto="María González",
            Email="maria@test.com",
            Telefono="+57 3009876543",
            ConsentimientoDatos=True,
            SaludBasica="Saludable",
        )

        # Crear ejercicios de prueba
        self.ejercicio_press = Ejercicio.objects.create(
            Nombre="Press de Banca", GrupoMuscular="Pecho", Equipo="Barra"
        )

        self.ejercicio_sentadilla = Ejercicio.objects.create(
            Nombre="Sentadilla", GrupoMuscular="Piernas", Equipo="Barra"
        )

    def test_crear_rutina_semanal_exitosa(self):
        """
        Test: Crear rutina semanal exitosa
        """
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id,
            nombre="Rutina Push-Pull-Legs",
            dias_entrenamiento="LMXJV",
            es_plantilla=False,
        )

        self.assertIsInstance(rutina, RutinaSemanal)
        self.assertEqual(rutina.SocioID.id, self.socio.id)
        self.assertEqual(rutina.Nombre, "Rutina Push-Pull-Legs")
        self.assertEqual(rutina.DiasEntrenamiento, "LMXJV")
        self.assertFalse(rutina.EsPlantilla)
        self.assertEqual(RutinaSemanal.objects.count(), 1)

    def test_crear_rutina_sin_nombre(self):
        """
        Test: No se puede crear rutina sin nombre
        """
        with self.assertRaises(ValidationError) as context:
            crear_rutina_semanal(
                socio_id=self.socio.id, nombre="", dias_entrenamiento="LMX"
            )

        self.assertIn("nombre de la rutina es obligatorio", str(context.exception))

    def test_crear_rutina_socio_inexistente(self):
        """
        Test: No se puede crear rutina para socio inexistente
        """
        with self.assertRaises(ValidationError) as context:
            crear_rutina_semanal(
                socio_id=99999, nombre="Rutina Test", dias_entrenamiento="LMX"
            )

        self.assertIn("socio especificado no existe", str(context.exception))

    def test_asignar_ejercicio_a_rutina_exitoso(self):
        """
        Test: Asignar ejercicio a día de rutina exitosamente
        """
        # Crear rutina
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id, nombre="Rutina Básica", dias_entrenamiento="LMX"
        )

        # Asignar ejercicio al lunes (día 0)
        dia_rutina_ejercicio = asignar_ejercicio_a_rutina(
            rutina_id=rutina.id,
            ejercicio_id=self.ejercicio_press.id,
            dia_semana=0,
            series=4,
            repeticiones=8,
            tempo="3-0-1-0",
            peso_objetivo=Decimal("80.00"),
        )

        self.assertIsInstance(dia_rutina_ejercicio, DiaRutinaEjercicio)
        self.assertEqual(dia_rutina_ejercicio.RutinaID.id, rutina.id)
        self.assertEqual(dia_rutina_ejercicio.EjercicioID.id, self.ejercicio_press.id)
        self.assertEqual(dia_rutina_ejercicio.DiaSemana, 0)
        self.assertEqual(dia_rutina_ejercicio.Series, 4)
        self.assertEqual(dia_rutina_ejercicio.Repeticiones, 8)
        self.assertEqual(dia_rutina_ejercicio.PesoObjetivo, Decimal("80.00"))

    def test_asignar_ejercicio_dia_invalido(self):
        """
        Test: No se puede asignar ejercicio con día fuera de rango (0-6)
        """
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id, nombre="Rutina Test", dias_entrenamiento="LMXJVSD"
        )

        # Intentar asignar con día 7 (inválido)
        with self.assertRaises(ValidationError) as context:
            asignar_ejercicio_a_rutina(
                rutina_id=rutina.id,
                ejercicio_id=self.ejercicio_press.id,
                dia_semana=7,
                series=3,
                repeticiones=10,
            )

        self.assertIn("debe ser un número entre 0", str(context.exception))

    def test_asignar_ejercicio_valores_negativos(self):
        """
        Test: No se puede asignar ejercicio con valores negativos
        """
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id, nombre="Rutina Test", dias_entrenamiento="LMX"
        )

        # Intentar asignar con series negativas
        with self.assertRaises(ValidationError) as context:
            asignar_ejercicio_a_rutina(
                rutina_id=rutina.id,
                ejercicio_id=self.ejercicio_press.id,
                dia_semana=0,
                series=-1,
                repeticiones=10,
            )

        self.assertIn("series deben ser un número positivo", str(context.exception))

    def test_asignar_ejercicio_duplicado_mismo_dia(self):
        """
        Test: No se puede asignar el mismo ejercicio dos veces en el mismo día
        """
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id, nombre="Rutina Test", dias_entrenamiento="LMX"
        )

        # Primera asignación exitosa
        asignar_ejercicio_a_rutina(
            rutina_id=rutina.id,
            ejercicio_id=self.ejercicio_press.id,
            dia_semana=0,
            series=4,
            repeticiones=8,
        )

        # Intentar asignar el mismo ejercicio en el mismo día
        with self.assertRaises(ValidationError) as context:
            asignar_ejercicio_a_rutina(
                rutina_id=rutina.id,
                ejercicio_id=self.ejercicio_press.id,
                dia_semana=0,
                series=3,
                repeticiones=12,
            )

        self.assertIn("Ya existe este ejercicio asignado", str(context.exception))

    def test_obtener_ejercicios_por_dia(self):
        """
        Test: Obtener ejercicios asignados a un día específico
        """
        rutina = crear_rutina_semanal(
            socio_id=self.socio.id, nombre="Rutina Full Body", dias_entrenamiento="LMX"
        )

        # Asignar ejercicios al lunes (día 0)
        asignar_ejercicio_a_rutina(
            rutina_id=rutina.id,
            ejercicio_id=self.ejercicio_press.id,
            dia_semana=0,
            series=4,
            repeticiones=8,
        )

        asignar_ejercicio_a_rutina(
            rutina_id=rutina.id,
            ejercicio_id=self.ejercicio_sentadilla.id,
            dia_semana=0,
            series=4,
            repeticiones=10,
        )

        # Asignar ejercicio al miércoles (día 2)
        asignar_ejercicio_a_rutina(
            rutina_id=rutina.id,
            ejercicio_id=self.ejercicio_press.id,
            dia_semana=2,
            series=3,
            repeticiones=12,
        )

        # Obtener ejercicios del lunes
        ejercicios_lunes = obtener_ejercicios_por_dia(rutina.id, 0)
        self.assertEqual(ejercicios_lunes.count(), 2)

        # Obtener ejercicios del miércoles
        ejercicios_miercoles = obtener_ejercicios_por_dia(rutina.id, 2)
        self.assertEqual(ejercicios_miercoles.count(), 1)

        # Verificar que el martes no tiene ejercicios
        ejercicios_martes = obtener_ejercicios_por_dia(rutina.id, 1)
        self.assertEqual(ejercicios_martes.count(), 0)
