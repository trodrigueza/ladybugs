from django.db import transaction
from django.utils import timezone

from apps.control_acceso.models import Asistencia
from apps.pagos.models import SocioMembresia


class ValidationError(ValueError):
    pass


def validar_membresia_activa(socio_membresia):
    """
    Valida que la membresía esté activa antes de registrar asistencia.
    """
    if not socio_membresia.is_active():
        raise ValidationError(
            "La membresía no está activa. No se puede registrar la entrada."
        )


def registrar_entrada(socio_membresia_id, terminal_acceso=None):
    """
    Registra la entrada de un socio al gimnasio.

    Args:
        socio_membresia_id: ID de la membresía del socio
        terminal_acceso: Terminal de acceso opcional (ej: "Terminal 1")

    Returns:
        Objeto Asistencia creado

    Raises:
        ValidationError: Si la membresía no existe o no está activa
    """
    try:
        socio_membresia = SocioMembresia.objects.get(id=socio_membresia_id)
    except SocioMembresia.DoesNotExist:
        raise ValidationError("La membresía especificada no existe.")

    validar_membresia_activa(socio_membresia)

    entrada_abierta = Asistencia.objects.filter(
        SocioMembresiaID=socio_membresia, FechaHoraSalida__isnull=True
    ).exists()

    if entrada_abierta:
        raise ValidationError("Ya existe una entrada activa sin registrar salida.")

    with transaction.atomic():
        asistencia = Asistencia.objects.create(
            SocioMembresiaID=socio_membresia,
            FechaHoraEntrada=timezone.now(),
            TerminalAcceso=terminal_acceso or "",
        )
        return asistencia


def registrar_salida(asistencia_id):
    """
    Registra la salida de un socio del gimnasio.

    Args:
        asistencia_id: ID del registro de asistencia

    Returns:
        Objeto Asistencia actualizado

    Raises:
        ValidationError: Si la asistencia no existe o ya tiene salida registrada
    """
    try:
        asistencia = Asistencia.objects.get(id=asistencia_id)
    except Asistencia.DoesNotExist:
        raise ValidationError("El registro de asistencia no existe.")

    if asistencia.FechaHoraSalida is not None:
        raise ValidationError("Esta asistencia ya tiene una salida registrada.")

    with transaction.atomic():
        asistencia.FechaHoraSalida = timezone.now()
        asistencia.save(update_fields=["FechaHoraSalida"])
        return asistencia


def obtener_asistencia_activa(socio_membresia_id):
    """
    Obtiene la asistencia activa (sin salida) de un socio.

    Args:
        socio_membresia_id: ID de la membresía del socio

    Returns:
        Objeto Asistencia o None si no hay entrada activa
    """
    try:
        return Asistencia.objects.get(
            SocioMembresiaID_id=socio_membresia_id, FechaHoraSalida__isnull=True
        )
    except Asistencia.DoesNotExist:
        return None
