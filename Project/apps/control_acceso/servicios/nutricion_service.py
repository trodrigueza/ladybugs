from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Dict, List

from django.db import transaction

from apps.control_acceso.models import (
    Alimento,
    ComidaAlimento,
    DiaComida,
    PlanNutricional,
)


def _meal(tipo: str, items: List[Dict]) -> Dict:
    return {"tipo": tipo, "items": items}


def _food(nombre: str, porcion: Decimal, kcal: int, macros: str, porcion_base: str) -> Dict:
    return {
        "nombre": nombre,
        "porcion": Decimal(str(porcion)),
        "kcal": kcal,
        "macros": macros,
        "porcion_base": porcion_base,
    }


DEFAULT_BASE_MEALS = [
    _meal(
        "Desayuno",
        [
            _food("Avena con frutas", 120, 320, "P: 12g, C: 58g, G: 7g", "100 g"),
            _food("Yogur griego con miel", 150, 180, "P: 15g, C: 20g, G: 4g", "150 g"),
        ],
    ),
    _meal(
        "Almuerzo",
        [
            _food("Pechuga de pollo a la plancha", 180, 250, "P: 37g, C: 0g, G: 6g", "150 g"),
            _food("Arroz integral", 150, 220, "P: 5g, C: 45g, G: 2g", "140 g"),
            _food("Ensalada verde", 120, 90, "P: 3g, C: 10g, G: 4g", "100 g"),
        ],
    ),
    _meal(
        "Cena",
        [
            _food("Salmón al horno", 170, 280, "P: 34g, C: 0g, G: 15g", "160 g"),
            _food("Quinoa cocida", 130, 190, "P: 7g, C: 35g, G: 3g", "130 g"),
            _food("Ensalada verde", 100, 90, "P: 3g, C: 10g, G: 4g", "100 g"),
        ],
    ),
    _meal(
        "Snack",
        [
            _food("Batido de proteínas", 250, 200, "P: 30g, C: 12g, G: 3g", "250 ml"),
            _food("Mix frutos secos", 40, 210, "P: 6g, C: 9g, G: 17g", "40 g"),
        ],
    ),
]

HIGH_PROTEIN_MEALS = [
    _meal(
        "Desayuno",
        [
            _food("Tostadas integrales con huevo", 2, 240, "P: 18g, C: 20g, G: 9g", "2 unidades"),
            _food("Batido verde", 300, 110, "P: 3g, C: 22g, G: 1g", "300 ml"),
        ],
    ),
    _meal(
        "Almuerzo",
        [
            _food("Lomo de res magro", 150, 275, "P: 35g, C: 0g, G: 12g", "150 g"),
            _food("Puré de papa", 180, 200, "P: 4g, C: 35g, G: 6g", "180 g"),
            _food("Brócoli al vapor", 120, 50, "P: 4g, C: 10g, G: 0g", "120 g"),
        ],
    ),
    _meal(
        "Pre-entrenamiento",
        [
            _food("Tortilla integral con mantequilla de maní", 1, 190, "P: 7g, C: 18g, G: 10g", "1 unidad"),
            _food("Banano", 1, 105, "P: 1g, C: 27g, G: 0g", "1 unidad"),
        ],
    ),
    _meal(
        "Cena",
        [
            _food("Tilapia al horno", 160, 195, "P: 32g, C: 0g, G: 5g", "160 g"),
            _food("Camote asado", 150, 135, "P: 2g, C: 31g, G: 0g", "150 g"),
            _food("Espárragos salteados", 110, 45, "P: 3g, C: 5g, G: 2g", "110 g"),
        ],
    ),
]

PLANTILLAS_NUTRICION = {
    "equilibrado": {
        "nombre": "Plan Equilibrado",
        "descripcion": "4 comidas diarias con macronutrientes balanceados.",
        "objetivo": 2200,
        "base": DEFAULT_BASE_MEALS,
    },
    "hiperproteico": {
        "nombre": "Plan Hiperproteico",
        "descripcion": "Pensado para hipertrofia moderada, con énfasis en proteína.",
        "objetivo": 2600,
        "base": HIGH_PROTEIN_MEALS,
    },
    "deficit_suave": {
        "nombre": "Plan Déficit Suave",
        "descripcion": "Reduce 15% del total calórico manteniendo snacks ligeros.",
        "objetivo": 1900,
        "base": DEFAULT_BASE_MEALS,
        "ajustes": {"calorias_factor": 0.9},
    },
}


def get_nutrition_templates():
    """Return metadata describing the available nutrition templates."""
    return [
        {
            "slug": slug,
            "nombre": data["nombre"],
            "descripcion": data["descripcion"],
            "objetivo": data["objetivo"],
        }
        for slug, data in PLANTILLAS_NUTRICION.items()
    ]


def _obtener_meals_para_dia(plantilla: Dict) -> List[Dict]:
    meals = deepcopy(plantilla["base"])
    factor = plantilla.get("ajustes", {}).get("calorias_factor")
    if factor:
        for meal in meals:
            for item in meal["items"]:
                item["porcion"] = (item["porcion"] * Decimal(str(factor))).quantize(Decimal("0.01"))
    return meals


def _sincronizar_alimento(datos: Dict) -> Alimento:
    alimento, _ = Alimento.objects.get_or_create(
        Nombre=datos["nombre"],
        defaults={
            "PorcionBase": datos["porcion_base"],
            "Kcal": datos["kcal"],
            "Macros": datos["macros"],
        },
    )
    actualizado = False
    if datos["porcion_base"] and alimento.PorcionBase != datos["porcion_base"]:
        alimento.PorcionBase = datos["porcion_base"]
        actualizado = True
    if datos["kcal"] and alimento.Kcal != datos["kcal"]:
        alimento.Kcal = datos["kcal"]
        actualizado = True
    if datos["macros"] and alimento.Macros != datos["macros"]:
        alimento.Macros = datos["macros"]
        actualizado = True
    if actualizado:
        alimento.save()
    return alimento


@transaction.atomic
def asignar_plan_desde_plantilla(socio, plantilla_slug: str, objetivo_personalizado: int | None = None) -> PlanNutricional:
    """Crea o actualiza el plan nutricional de un socio a partir de una plantilla predefinida."""
    plantilla = PLANTILLAS_NUTRICION.get(plantilla_slug)
    if not plantilla:
        raise ValueError("La plantilla solicitada no existe.")

    plan, _ = PlanNutricional.objects.get_or_create(
        SocioID=socio,
        EsPlantilla=False,
        defaults={"Nombre": plantilla["nombre"]},
    )
    plan.ObjetivoCaloricoDiario = objetivo_personalizado or plantilla["objetivo"]
    plan.EsPlantilla = False
    plan.Nombre = plan.Nombre or plantilla["nombre"]
    plan.save()

    # Limpiar comidas existentes para reescribir el plan completo
    plan.dias_comida.all().delete()

    for dia in range(7):
        for meal in _obtener_meals_para_dia(plantilla):
            dia_comida = DiaComida.objects.create(
                PlanNutricionalID=plan,
                DiaSemana=dia,
                TipoComida=meal["tipo"],
            )
            for item in meal["items"]:
                alimento = _sincronizar_alimento(item)
                ComidaAlimento.objects.create(
                    DiaComidaID=dia_comida,
                    AlimentoID=alimento,
                    Porcion=item["porcion"],
                )

    return plan


@transaction.atomic
def aplicar_plan_desde_template_db(
    template_plan: PlanNutricional, socio, objetivo_personalizado: int | None = None
) -> PlanNutricional:
    """Clona un plan plantilla almacenado en BD hacia el socio indicado."""
    if not template_plan.EsPlantilla:
        raise ValueError("El plan proporcionado no es una plantilla.")
    if template_plan.SocioID_id:
        raise ValueError("Las plantillas no deben estar asociadas a un socio.")

    plan, _ = PlanNutricional.objects.get_or_create(
        SocioID=socio,
        EsPlantilla=False,
        defaults={"Nombre": template_plan.Nombre},
    )
    plan.Nombre = template_plan.Nombre or plan.Nombre
    plan.ObjetivoCaloricoDiario = objetivo_personalizado or template_plan.ObjetivoCaloricoDiario
    plan.EsPlantilla = False
    plan.save()

    plan.dias_comida.all().delete()

    for dia in template_plan.dias_comida.all():
        copia_dia = DiaComida.objects.create(
            PlanNutricionalID=plan,
            DiaSemana=dia.DiaSemana,
            TipoComida=dia.TipoComida,
        )
        for item in dia.alimentos.all():
            ComidaAlimento.objects.create(
                DiaComidaID=copia_dia,
                AlimentoID=item.AlimentoID,
                Porcion=item.Porcion,
                Cantidad=item.Cantidad,
            )

    return plan
