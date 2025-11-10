import re  
from django.db import transaction, IntegrityError
from django.contrib.auth.hashers import make_password
from apps.socios.models import Socio
from datetime import datetime

class ValidationError(ValueError):
    pass

def validate_socio_data(data: dict):
    errors = []

    password = data.get('password', '')
    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")

    email = data.get('email', '')
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append("El formato del email no es válido.")

    identificacion = data.get('identificacion', '')
    if not (identificacion.isdigit() and len(identificacion) == 10):
        errors.append("La identificación debe tener 10 dígitos numéricos.")

    phone = data.get('phone', '')
    if not phone.startswith('+57 3'):
        errors.append("El teléfono debe iniciar con '+57 3' (ej: +57 3001234567).")

    health_status = data.get('health_status', '')
    if not health_status:
        errors.append("Debes seleccionar una opción válida en 'Estado de salud'.")

    if Socio.objects.filter(Email=email).exists():
        errors.append("Ya existe un socio con este correo electrónico.")
    
    if Socio.objects.filter(Identificacion=identificacion).exists():
        errors.append("Ya existe un socio con esta identificación.")

    if Socio.objects.filter(Telefono=phone).exists():
        errors.append("Ya existe un socio con este número de teléfono.")

    if errors:
        raise ValidationError("Por favor, corrige los siguientes errores: " + "; ".join(errors))



def create_socio_from_dict(data: dict) -> Socio:
    
    validate_socio_data(data)

    try:
        with transaction.atomic():
            hashed_pwd = make_password(data.get('password')) if data.get('password') else None

            birth = data.get('birthdate')
            if isinstance(birth, str) and birth:
                try:
                    birthdate = datetime.fromisoformat(birth).date()
                except ValueError:
                    birthdate = None
            else:
                birthdate = data.get('birthdate')

            socio = Socio.objects.create(
                Identificacion = data.get('identificacion'),
                NombreCompleto = data.get('full_name'),
                Email = data.get('email'),
                Telefono = data.get('phone'),
                FechaNacimiento = birthdate,
                ConsentimientoDatos = bool(data.get('consent')),
                SaludBasica = data.get('health_status', '') or '',
                NotaOpcional = data.get('follow_up_note', '') or '',
                Password = hashed_pwd,
            )
            return socio
    except IntegrityError:
      
        raise