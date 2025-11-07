from django.db import transaction, IntegrityError
from django.contrib.auth.hashers import make_password
from apps.socios.models import Socio
from datetime import datetime

def create_socio_from_dict(data: dict) -> Socio:
    try:
        with transaction.atomic():
            # hash de la contraseña
            hashed_pwd = make_password(data.get('password')) if data.get('password') else None

            # convertir fecha si viene como string 'YYYY-MM-DD'
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
