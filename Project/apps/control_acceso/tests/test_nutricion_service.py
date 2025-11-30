from django.test import TestCase

from apps.control_acceso.models import PlanNutricional
from apps.control_acceso.servicios.nutricion_service import (
    PLANTILLAS_NUTRICION,
    asignar_plan_desde_plantilla,
)
from apps.socios.models import Socio


class NutricionServiceTests(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(
            Identificacion="123",
            NombreCompleto="Test Socio",
            Email="test@example.com",
        )

    def test_asignar_plan_crea_comidas_para_cada_dia(self):
        plantilla_slug = "equilibrado"
        plantilla = PLANTILLAS_NUTRICION[plantilla_slug]
        comidas_por_dia = len(plantilla["base"])

        plan = asignar_plan_desde_plantilla(self.socio, plantilla_slug, objetivo_personalizado=2100)

        self.assertEqual(plan.ObjetivoCaloricoDiario, 2100)
        self.assertEqual(
            PlanNutricional.objects.filter(SocioID=self.socio, EsPlantilla=False).count(), 1
        )
        self.assertEqual(plan.dias_comida.count(), comidas_por_dia * 7)

        desayunos = plan.dias_comida.filter(TipoComida="Desayuno")
        self.assertTrue(desayunos.exists())
        self.assertGreater(desayunos.first().alimentos.count(), 0)

    def test_error_al_usar_plantilla_inexistente(self):
        with self.assertRaises(ValueError):
            asignar_plan_desde_plantilla(self.socio, "no-existe")
