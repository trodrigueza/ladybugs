import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), "Project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Project.settings")
django.setup()

from apps.control_acceso.models import (
    Alimento,
    ComidaAlimento,
    DiaComida,
    DiaRutinaEjercicio,
    Ejercicio,
    PlanNutricional,
    RutinaSemanal,
)
from apps.seguridad.models import Rol, Usuario
from apps.seguridad.servicios.registro_usuario import crear_usuario_para_socio
from apps.socios.models import Medicion, Socio
from django.utils import timezone


def create_test_data():
    print("Creating test data...")

    # 1. Create Socio
    email = "test_socio1@example.com"
    socio, created = Socio.objects.get_or_create(
        Identificacion="123456781",
        defaults={
            "NombreCompleto": "Test Socio",
            "Email": email,
            "Telefono": "555-01001",
            "FechaNacimiento": date(1995, 5, 15),
            "ConsentimientoDatos": True,
            "Altura": 1.75,
        },
    )
    if created:
        print(f"Socio created: {socio.NombreCompleto}")
        # Create associated Usuario
        crear_usuario_para_socio(socio, "password123")
        print("Usuario created with password: password123")
    else:
        print(f"Socio already exists: {socio.NombreCompleto}")
        if not socio.Altura:
            socio.Altura = 1.75
            socio.save()
            print("Updated Socio height to 1.75m")

    # 2. Create Measurements (Weight History)
    base_date = timezone.now().date()
    weights = [75.5, 75.2, 74.8, 74.5, 74.2, 74.0, 73.8]  # Trend de baja

    for i, weight in enumerate(weights):
        med_date = base_date - timedelta(days=(len(weights) - i - 1) * 4)
        Medicion.objects.get_or_create(
            SocioID=socio,
            Fecha=med_date,
            defaults={
                "PesoCorporal": weight,
                "MedidasCorporales": f"Pecho: {90 + i}cm, Cintura: {80 - i}cm",
                "IMC": round(weight / (1.75**2), 2),
            },
        )
    print("Measurements created.")

    # 3. Create Membership (required for sessions)
    from apps.pagos.models import PlanMembresia, SocioMembresia

    plan, _ = PlanMembresia.objects.get_or_create(
        Nombre="Plan Mensual",
        defaults={
            "Precio": 50000,
            "DuracionDias": 30,  # días
        },
    )

    membresia, created = SocioMembresia.objects.get_or_create(
        SocioID=socio,
        PlanID=plan,
        defaults={
            "FechaInicio": timezone.now().date(),
            "FechaFin": (timezone.now() + timedelta(days=30)).date(),
            "Estado": "Activa",
        },
    )
    if created:
        print(f"Membership created: {membresia}")
    else:
        print(f"Membership already exists: {membresia}")

    # 4. Create Exercises
    from apps.control_acceso.models import Ejercicio

    ejercicios_data = [
        {
            "Nombre": "Sentadilla",
            "GrupoMuscular": "Piernas",
            "Descripcion": "Ejercicio compuesto para piernas",
        },
        {
            "Nombre": "Press de Banca",
            "GrupoMuscular": "Pecho",
            "Descripcion": "Ejercicio principal de pecho",
        },
        {
            "Nombre": "Peso Muerto",
            "GrupoMuscular": "Espalda",
            "Descripcion": "Ejercicio compuesto de espalda",
        },
        {
            "Nombre": "Remo con Barra",
            "GrupoMuscular": "Espalda",
            "Descripcion": "Ejercicio de espalda",
        },
        {
            "Nombre": "Press Militar",
            "GrupoMuscular": "Hombros",
            "Descripcion": "Ejercicio de hombros",
        },
        {
            "Nombre": "Dominadas",
            "GrupoMuscular": "Espalda",
            "Descripcion": "Trabajo con peso corporal para espalda y brazos",
        },
        {
            "Nombre": "Plancha",
            "GrupoMuscular": "Core",
            "Descripcion": "Ejercicio isométrico para abdomen y zona media",
        },
        {
            "Nombre": "Zancadas",
            "GrupoMuscular": "Piernas",
            "Descripcion": "Ejercicio unilateral para cuádriceps y glúteos",
        },
        {
            "Nombre": "Press de Piernas",
            "GrupoMuscular": "Piernas",
            "Descripcion": "Variación guiada para trabajar tren inferior",
        },
        {
            "Nombre": "Curl de Bíceps",
            "GrupoMuscular": "Brazos",
            "Descripcion": "Aislamiento de bíceps con peso libre",
        },
        {
            "Nombre": "Extensión de Tríceps",
            "GrupoMuscular": "Brazos",
            "Descripcion": "Trabajo de tríceps en polea o barra",
        },
        {
            "Nombre": "Burpees",
            "GrupoMuscular": "Full Body",
            "Descripcion": "Ejercicio metabólico de cuerpo completo",
        },
    ]

    ejercicios = {}
    for ej_data in ejercicios_data:
        ej, _ = Ejercicio.objects.get_or_create(
            Nombre=ej_data["Nombre"],
            defaults={
                "GrupoMuscular": ej_data["GrupoMuscular"],
                "Descripcion": ej_data["Descripcion"],
            },
        )
        ejercicios[ej_data["Nombre"]] = ej
    print(f"Exercises created: {len(ejercicios)}")

    # 5. Create Weekly Routine
    from apps.control_acceso.models import DiaRutinaEjercicio, RutinaSemanal

    rutina, created = RutinaSemanal.objects.get_or_create(
        SocioID=socio,
        Nombre="Rutina Push/Pull/Legs",
        defaults={"DiasEntrenamiento": "LMXJV", "EsPlantilla": False},
    )
    if created:
        print(f"Routine created: {rutina.Nombre}")

        # Monday (0) - Push
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios["Press de Banca"],
            DiaSemana=0,
            Series=4,
            Repeticiones=10,
            PesoObjetivo=60,
        )
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios["Press Militar"],
            DiaSemana=0,
            Series=3,
            Repeticiones=10,
            PesoObjetivo=40,
        )

        # Wednesday (2) - Pull
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios["Peso Muerto"],
            DiaSemana=2,
            Series=4,
            Repeticiones=8,
            PesoObjetivo=80,
        )
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios["Remo con Barra"],
            DiaSemana=2,
            Series=3,
            Repeticiones=10,
            PesoObjetivo=50,
        )

        # Friday (4) - Legs
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios["Sentadilla"],
            DiaSemana=4,
            Series=4,
            Repeticiones=10,
            PesoObjetivo=70,
        )

        print("Routine exercises created for Mon/Wed/Fri")
    else:
        print(f"Routine already exists: {rutina.Nombre}")

    def to_decimal(value):
        if value is None:
            return None
        return Decimal(str(value))

    additional_routines = [
        {
            "nombre": "Full Body Equilibrado",
            "dias_entrenamiento": "LMXJV",
            "es_plantilla": False,
            "ejercicios_por_dia": {
                0: [
                    {
                        "nombre": "Sentadilla",
                        "series": 4,
                        "repeticiones": 8,
                        "peso": 75,
                    },
                    {
                        "nombre": "Press de Banca",
                        "series": 4,
                        "repeticiones": 8,
                        "peso": 65,
                    },
                    {
                        "nombre": "Dominadas",
                        "series": 3,
                        "repeticiones": 8,
                        "peso": None,
                    },
                ],
                1: [
                    {
                        "nombre": "Peso Muerto",
                        "series": 4,
                        "repeticiones": 6,
                        "peso": 90,
                    },
                    {
                        "nombre": "Remo con Barra",
                        "series": 4,
                        "repeticiones": 10,
                        "peso": 55,
                    },
                    {
                        "nombre": "Plancha",
                        "series": 3,
                        "repeticiones": 45,
                        "peso": None,
                    },
                ],
                3: [
                    {"nombre": "Zancadas", "series": 4, "repeticiones": 12, "peso": 30},
                    {
                        "nombre": "Press Militar",
                        "series": 3,
                        "repeticiones": 10,
                        "peso": 42,
                    },
                    {
                        "nombre": "Curl de Bíceps",
                        "series": 3,
                        "repeticiones": 12,
                        "peso": 12,
                    },
                ],
                4: [
                    {
                        "nombre": "Press de Piernas",
                        "series": 4,
                        "repeticiones": 12,
                        "peso": 120,
                    },
                    {
                        "nombre": "Extensión de Tríceps",
                        "series": 3,
                        "repeticiones": 12,
                        "peso": 20,
                    },
                ],
            },
        },
        {
            "nombre": "HIIT + Fuerza Express",
            "dias_entrenamiento": "LXVSD",
            "es_plantilla": True,
            "ejercicios_por_dia": {
                0: [
                    {
                        "nombre": "Burpees",
                        "series": 5,
                        "repeticiones": 15,
                        "peso": None,
                    },
                    {
                        "nombre": "Sentadilla",
                        "series": 3,
                        "repeticiones": 15,
                        "peso": 60,
                    },
                ],
                2: [
                    {
                        "nombre": "Dominadas",
                        "series": 4,
                        "repeticiones": 6,
                        "peso": None,
                    },
                    {
                        "nombre": "Press Militar",
                        "series": 3,
                        "repeticiones": 10,
                        "peso": 40,
                    },
                    {
                        "nombre": "Plancha",
                        "series": 4,
                        "repeticiones": 60,
                        "peso": None,
                    },
                ],
                5: [
                    {
                        "nombre": "Peso Muerto",
                        "series": 4,
                        "repeticiones": 5,
                        "peso": 95,
                    },
                    {"nombre": "Zancadas", "series": 3, "repeticiones": 10, "peso": 35},
                ],
            },
        },
    ]

    for rutina_data in additional_routines:
        rutina_obj, rutina_created = RutinaSemanal.objects.get_or_create(
            SocioID=socio,
            Nombre=rutina_data["nombre"],
            defaults={
                "DiasEntrenamiento": rutina_data["dias_entrenamiento"],
                "EsPlantilla": rutina_data["es_plantilla"],
            },
        )

        if not rutina_created:
            updated = False
            if rutina_obj.DiasEntrenamiento != rutina_data["dias_entrenamiento"]:
                rutina_obj.DiasEntrenamiento = rutina_data["dias_entrenamiento"]
                updated = True
            if rutina_obj.EsPlantilla != rutina_data["es_plantilla"]:
                rutina_obj.EsPlantilla = rutina_data["es_plantilla"]
                updated = True
            if updated:
                rutina_obj.save()

        estado = "created" if rutina_created else "updated"
        print(f"Routine {estado}: {rutina_obj.Nombre}")

        asignaciones_configuradas = 0
        for dia_semana, ejercicios_dia in rutina_data["ejercicios_por_dia"].items():
            for ejercicio_cfg in ejercicios_dia:
                ejercicio_obj = ejercicios[ejercicio_cfg["nombre"]]
                DiaRutinaEjercicio.objects.update_or_create(
                    RutinaID=rutina_obj,
                    EjercicioID=ejercicio_obj,
                    DiaSemana=dia_semana,
                    defaults={
                        "Series": ejercicio_cfg.get("series"),
                        "Repeticiones": ejercicio_cfg.get("repeticiones"),
                        "PesoObjetivo": to_decimal(ejercicio_cfg.get("peso")),
                        "Tempo": "",
                    },
                )
                asignaciones_configuradas += 1

        print(
            f"  -> {asignaciones_configuradas} ejercicios configurados para {rutina_obj.Nombre}"
        )

    # 6. Create Weekly Routine for current day
    dia_semana_actual = datetime.now().weekday()
    rutina_hoy = DiaRutinaEjercicio.objects.filter(
        RutinaID=rutina, DiaSemana=dia_semana_actual
    )
    if not rutina_hoy.exists():
        # Add at least one exercise for today for testing
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=list(ejercicios.values())[0],
            DiaSemana=dia_semana_actual,
            Series=3,
            Repeticiones="12",
            PesoObjetivo=50,
        )
        print(f"Added exercise for today ({dia_semana_actual})")

    # 7. Create Nutritional Plan + foods for the week
    alimentos_data = [
        {
            "nombre": "Avena con frutas",
            "porcion": "100 g",
            "kcal": 320,
            "macros": "P: 12g, C: 58g, G: 7g",
        },
        {
            "nombre": "Yogur griego con miel",
            "porcion": "150 g",
            "kcal": 180,
            "macros": "P: 15g, C: 20g, G: 4g",
        },
        {
            "nombre": "Pechuga de pollo a la plancha",
            "porcion": "150 g",
            "kcal": 250,
            "macros": "P: 37g, C: 0g, G: 6g",
        },
        {
            "nombre": "Arroz integral",
            "porcion": "140 g",
            "kcal": 220,
            "macros": "P: 5g, C: 45g, G: 2g",
        },
        {
            "nombre": "Ensalada verde",
            "porcion": "100 g",
            "kcal": 90,
            "macros": "P: 3g, C: 10g, G: 4g",
        },
        {
            "nombre": "Batido de proteínas",
            "porcion": "250 ml",
            "kcal": 200,
            "macros": "P: 30g, C: 12g, G: 3g",
        },
        {
            "nombre": "Salmón al horno",
            "porcion": "160 g",
            "kcal": 280,
            "macros": "P: 34g, C: 0g, G: 15g",
        },
        {
            "nombre": "Quinoa cocida",
            "porcion": "130 g",
            "kcal": 190,
            "macros": "P: 7g, C: 35g, G: 3g",
        },
        {
            "nombre": "Mix frutos secos",
            "porcion": "40 g",
            "kcal": 210,
            "macros": "P: 6g, C: 9g, G: 17g",
        },
    ]

    alimentos = {}
    for data in alimentos_data:
        alimento, created = Alimento.objects.get_or_create(
            Nombre=data["nombre"],
            defaults={
                "PorcionBase": data["porcion"],
                "Kcal": data["kcal"],
                "Macros": data["macros"],
            },
        )
        if not created:
            updated = False
            if alimento.PorcionBase != data["porcion"]:
                alimento.PorcionBase = data["porcion"]
                updated = True
            if alimento.Kcal != data["kcal"]:
                alimento.Kcal = data["kcal"]
                updated = True
            if alimento.Macros != data["macros"]:
                alimento.Macros = data["macros"]
                updated = True
            if updated:
                alimento.save()
        alimentos[data["nombre"]] = alimento
    print(f"Foods ready: {len(alimentos)}")

    plan_nutricional, created = PlanNutricional.objects.get_or_create(
        SocioID=socio, EsPlantilla=False, defaults={"ObjetivoCaloricoDiario": 2200}
    )
    if created:
        print("Nutritional plan created")
    else:
        print("Nutritional plan already exists")

    meal_templates = {
        "Desayuno": [
            {"alimento": "Avena con frutas", "porcion": Decimal("120")},
            {"alimento": "Yogur griego con miel", "porcion": Decimal("150")},
        ],
        "Almuerzo": [
            {"alimento": "Pechuga de pollo a la plancha", "porcion": Decimal("180")},
            {"alimento": "Arroz integral", "porcion": Decimal("150")},
            {"alimento": "Ensalada verde", "porcion": Decimal("100")},
        ],
        "Cena": [
            {"alimento": "Salmón al horno", "porcion": Decimal("170")},
            {"alimento": "Quinoa cocida", "porcion": Decimal("130")},
            {"alimento": "Ensalada verde", "porcion": Decimal("100")},
        ],
        "Snack": [
            {"alimento": "Batido de proteínas", "porcion": Decimal("250")},
            {"alimento": "Mix frutos secos", "porcion": Decimal("40")},
        ],
    }

    for dia_semana in range(7):
        for tipo_comida, alimentos_list in meal_templates.items():
            dia_comida, _ = DiaComida.objects.get_or_create(
                PlanNutricionalID=plan_nutricional,
                DiaSemana=dia_semana,
                TipoComida=tipo_comida,
            )
            for alimento_item in alimentos_list:
                alimento_obj = alimentos[alimento_item["alimento"]]
                ComidaAlimento.objects.update_or_create(
                    DiaComidaID=dia_comida,
                    AlimentoID=alimento_obj,
                    defaults={"Porcion": alimento_item["porcion"], "Cantidad": None},
                )
    print("Nutrition plan populated for every day of the week")

    print("\nDone! You can log in with:")
    print("Email: test_socio@example.com")
    print("Password: password123")


if __name__ == "__main__":
    create_test_data()
