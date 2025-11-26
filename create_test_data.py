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
    weights = [75.5, 75.2, 74.8, 74.5, 74.2, 74.0, 73.8]  # Trend de baja
    
    for i, weight in enumerate(weights):
        med_date = base_date - timedelta(days=(len(weights) - i - 1) * 4)
        Medicion.objects.get_or_create(
            SocioID=socio,
            Fecha=med_date,
            defaults={
                'PesoCorporal': weight,
                'MedidasCorporales': f'Pecho: {90+i}cm, Cintura: {80-i}cm',
                'IMC': round(weight / (1.75 ** 2), 2)
            }
        )
    print("Measurements created.")

    # 3. Create Membership (required for sessions)
    from apps.pagos.models import PlanMembresia, SocioMembresia
    
    plan, _ = PlanMembresia.objects.get_or_create(
        Nombre="Plan Mensual",
        defaults={
            'Precio': 50000,
            'DuracionDias': 30  # días
        }
    )
    
    membresia, created = SocioMembresia.objects.get_or_create(
        SocioID=socio,
        PlanID=plan,
        defaults={
            'FechaInicio': timezone.now().date(),
            'FechaFin': (timezone.now() + timedelta(days=30)).date(),
            'Estado': 'Activa'
        }
    )
    if created:
        print(f"Membership created: {membresia}")
    else:
        print(f"Membership already exists: {membresia}")

    # 4. Create Exercises
    from apps.control_acceso.models import Ejercicio
    
    ejercicios_data = [
        {'Nombre': 'Sentadilla', 'GrupoMuscular': 'Piernas', 'Descripcion': 'Ejercicio compuesto para piernas'},
        {'Nombre': 'Press de Banca', 'GrupoMuscular': 'Pecho', 'Descripcion': 'Ejercicio principal de pecho'},
        {'Nombre': 'Peso Muerto', 'GrupoMuscular': 'Espalda', 'Descripcion': 'Ejercicio compuesto de espalda'},
        {'Nombre': 'Remo con Barra', 'GrupoMuscular': 'Espalda', 'Descripcion': 'Ejercicio de espalda'},
        {'Nombre': 'Press Militar', 'GrupoMuscular': 'Hombros', 'Descripcion': 'Ejercicio de hombros'},
    ]
    
    ejercicios = {}
    for ej_data in ejercicios_data:
        ej, _ = Ejercicio.objects.get_or_create(
            Nombre=ej_data['Nombre'],
            defaults={
                'GrupoMuscular': ej_data['GrupoMuscular'],
                'Descripcion': ej_data['Descripcion']
            }
        )
        ejercicios[ej_data['Nombre']] = ej
    print(f"Exercises created: {len(ejercicios)}")

    # 5. Create Weekly Routine
    from apps.control_acceso.models import RutinaSemanal, DiaRutinaEjercicio
    
    rutina, created = RutinaSemanal.objects.get_or_create(
        SocioID=socio,
        Nombre="Rutina Push/Pull/Legs",
        defaults={
            'DiasEntrenamiento': 'LMXJV',
            'EsPlantilla': False
        }
    )
    if created:
        print(f"Routine created: {rutina.Nombre}")
        
        # Monday (0) - Push
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios['Press de Banca'],
            DiaSemana=0,
            Series=4,
            Repeticiones=10,
            PesoObjetivo=60
        )
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios['Press Militar'],
            DiaSemana=0,
            Series=3,
            Repeticiones=10,
            PesoObjetivo=40
        )
        
        # Wednesday (2) - Pull
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios['Peso Muerto'],
            DiaSemana=2,
            Series=4,
            Repeticiones=8,
            PesoObjetivo=80
        )
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios['Remo con Barra'],
            DiaSemana=2,
            Series=3,
            Repeticiones=10,
            PesoObjetivo=50
        )
        
        # Friday (4) - Legs
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=ejercicios['Sentadilla'],
            DiaSemana=4,
            Series=4,
            Repeticiones=10,
            PesoObjetivo=70
        )
        
        print("Routine exercises created for Mon/Wed/Fri")
    else:
        print(f"Routine already exists: {rutina.Nombre}")

    # 6. Create Weekly Routine for current day
    dia_semana_actual = datetime.now().weekday()
    rutina_hoy = DiaRutinaEjercicio.objects.filter(RutinaID=rutina, DiaSemana=dia_semana_actual)
    if not rutina_hoy.exists():
        # Add at least one exercise for today for testing
        DiaRutinaEjercicio.objects.create(
            RutinaID=rutina,
            EjercicioID=list(ejercicios.values())[0],
            DiaSemana=dia_semana_actual,
            Series=3,
            Repeticiones='12',
            PesoObjetivo=50
        )
        print(f"Added exercise for today ({dia_semana_actual})")

    # 7. Create Nutritional Plan
    plan_nutricional, created = PlanNutricional.objects.get_or_create(
        SocioID=socio,
        defaults={'ObjetivoCaloricoDiario': 2200}
    )
    if created:
        print(f"Nutritional plan created")
        
        # Create meal for current day
        dia_comida = DiaComida.objects.create(
            PlanNutricionalID=plan_nutricional,
            DiaSemana=dia_semana_actual,
            TipoComida='Desayuno',
            HoraSugerida='08:00'
        )
        
        # Create sample food
        alimento, _ = Alimento.objects.get_or_create(
            Nombre='Avena con frutas',
            defaults={
                'Calorias': 350,
                'Proteinas': 12,
                'Carbohidratos': 60,
                'Grasas': 8
            }
        )
        
        ComidaAlimento.objects.create(
            DiaComidaID=dia_comida,
            AlimentoID=alimento,
            Cantidad='1 taza'
        )
        print("Nutrition plan created for today")
    else:
        print(f"Nutritional plan already exists")

    print("\nDone! You can log in with:")
    print("Email: test_socio@example.com")
    print("Password: password123")

if __name__ == "__main__":
    from datetime import datetime
    create_test_data()
