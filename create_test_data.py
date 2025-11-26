import os
import django
import sys
from datetime import date, timedelta
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'Project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project.settings')
django.setup()

from django.utils import timezone
from apps.socios.models import Socio, Medicion
from apps.seguridad.models import Usuario, Rol
from apps.control_acceso.models import (
    Ejercicio, RutinaSemanal, DiaRutinaEjercicio, 
    Alimento, PlanNutricional, DiaComida, ComidaAlimento
)
from apps.seguridad.servicios.registro_usuario import crear_usuario_para_socio

def create_test_data():
    print("Creating test data...")

    # 1. Create Socio
    email = "test_socio@example.com"
    socio, created = Socio.objects.get_or_create(
        Identificacion="123456789",
        defaults={
            "NombreCompleto": "Test Socio",
            "Email": email,
            "Telefono": "555-0100",
            "FechaNacimiento": date(1995, 5, 15),
            "ConsentimientoDatos": True,
            "Altura": 1.75
        }
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
    weights = [70.5, 70.2, 69.8, 69.5, 69.0]
    for i, weight in enumerate(weights):
        med_date = base_date - timedelta(days=(len(weights)-i)*7)
        Medicion.objects.get_or_create(
            SocioID=socio,
            Fecha=med_date,
            defaults={"PesoCorporal": weight}
        )
    print("Measurements created.")

    # 3. Create Routine for Today
    rutina, _ = RutinaSemanal.objects.get_or_create(
        SocioID=socio,
        Nombre="Rutina de Prueba",
        defaults={"DiasEntrenamiento": "LMXJVSD"}
    )

    ejercicio1, _ = Ejercicio.objects.get_or_create(Nombre="Sentadilla")
    ejercicio2, _ = Ejercicio.objects.get_or_create(Nombre="Press Banca")

    today_weekday = datetime.now().weekday() # 0=Monday

    DiaRutinaEjercicio.objects.get_or_create(
        RutinaID=rutina,
        EjercicioID=ejercicio1,
        DiaSemana=today_weekday,
        defaults={"Series": 4, "Repeticiones": 10}
    )
    DiaRutinaEjercicio.objects.get_or_create(
        RutinaID=rutina,
        EjercicioID=ejercicio2,
        DiaSemana=today_weekday,
        defaults={"Series": 3, "Repeticiones": 12}
    )
    print(f"Routine created for weekday {today_weekday}.")

    # 4. Create Nutrition Plan for Today
    plan_nutri, _ = PlanNutricional.objects.get_or_create(
        SocioID=socio,
        defaults={"ObjetivoCaloricoDiario": 2000}
    )

    alimento1, _ = Alimento.objects.get_or_create(Nombre="Pollo", Kcal=165)
    alimento2, _ = Alimento.objects.get_or_create(Nombre="Arroz", Kcal=130)

    dia_comida, _ = DiaComida.objects.get_or_create(
        PlanNutricionalID=plan_nutri,
        DiaSemana=today_weekday,
        TipoComida="Almuerzo"
    )

    ComidaAlimento.objects.get_or_create(
        DiaComidaID=dia_comida,
        AlimentoID=alimento1,
        defaults={"Cantidad": 100} # grams
    )
    ComidaAlimento.objects.get_or_create(
        DiaComidaID=dia_comida,
        AlimentoID=alimento2,
        defaults={"Cantidad": 150}
    )
    print(f"Nutrition plan created for weekday {today_weekday}.")

    print("\nDone! You can log in with:")
    print(f"Email: {email}")
    print("Password: password123")

if __name__ == "__main__":
    from datetime import datetime
    create_test_data()
