from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.pagos.models import PlanMembresia, SocioMembresia, Pago, AlertaPago
from apps.socios.models import Socio


class ValidationError(ValueError):
    """Error de validación usado en los servicios de pagos."""
    pass


def crear_membresia_para_socio(socio_id, plan_id, fecha_inicio=None):
    """
    Crea una membresía para un socio a partir de un plan.

    - Calcula FechaFin con base en DuracionDias del plan.
    - No permite crear una segunda membresía ACTIVA que se solape en fechas.
    """
    try:
        socio = Socio.objects.get(id=socio_id)
    except Socio.DoesNotExist:
        raise ValidationError("El socio especificado no existe.")

    try:
        plan = PlanMembresia.objects.get(id=plan_id)
    except PlanMembresia.DoesNotExist:
        raise ValidationError("El plan de membresía especificado no existe.")

    if fecha_inicio is None:
        fecha_inicio = timezone.localdate()

    fecha_fin = fecha_inicio + timedelta(days=plan.DuracionDias)

    existe_activa = SocioMembresia.objects.filter(
        SocioID=socio,
        Estado=SocioMembresia.ESTADO_ACTIVA,
        FechaFin__gte=fecha_inicio,
    ).exists()

    if existe_activa:
        raise ValidationError(
            "El socio ya tiene una membresía activa vigente en ese periodo."
        )

    membresia = SocioMembresia.objects.create(
        SocioID=socio,
        PlanID=plan,
        FechaInicio=fecha_inicio,
        FechaFin=fecha_fin,
        Estado=SocioMembresia.ESTADO_ACTIVA,
    )
    return membresia


def registrar_pago_membresia(
    socio_membresia_id,
    monto,
    tipo_pago=None,
    comprobante_id=None,
):
    """
    Registra un pago para una membresía y actualiza el estado de la misma.

    Regla:
    - monto > 0
    - total pagado <= precio del plan
    - si MontoPendiente == 0 -> Estado ACTIVA
      si MontoPendiente > 0 -> Estado MOROSA
    """
    monto = Decimal(monto)
    if monto <= 0:
        raise ValidationError("El monto del pago debe ser un número positivo.")

    try:
        socio_membresia = SocioMembresia.objects.select_related("PlanID").get(
            id=socio_membresia_id
        )
    except SocioMembresia.DoesNotExist:
        raise ValidationError("La membresía especificada no existe.")

    with transaction.atomic():
        total_previos = (
            Pago.objects.filter(SocioMembresiaID=socio_membresia)
            .aggregate(total=Sum("Monto"))
            .get("total")
            or Decimal("0.00")
        )

        nuevo_total = total_previos + monto
        precio_plan = socio_membresia.PlanID.Precio

        if nuevo_total > precio_plan:
            raise ValidationError(
                "El total pagado no puede superar el precio del plan."
            )

        monto_pendiente = precio_plan - nuevo_total

        pago = Pago.objects.create(
            SocioMembresiaID=socio_membresia,
            Monto=monto,
            TipoPago=tipo_pago or "",
            ComprobanteID=comprobante_id or "",
            MontoPendiente=monto_pendiente,
        )

        if monto_pendiente == 0:
            socio_membresia.Estado = SocioMembresia.ESTADO_ACTIVA
        else:
            socio_membresia.Estado = SocioMembresia.ESTADO_MOROSA
        socio_membresia.save(update_fields=["Estado"])

        return pago


def generar_alerta_morosidad(socio_membresia_id, tipo_alerta="PAGO_PENDIENTE"):
    """
    Genera (o reusa) una alerta de pago pendiente para una membresía morosa.

    - Solo se permite si la membresía está en estado MOROSA.
    - Usa get_or_create para no duplicar alertas pendientes.
    """
    try:
        socio_membresia = SocioMembresia.objects.get(id=socio_membresia_id)
    except SocioMembresia.DoesNotExist:
        raise ValidationError("La membresía especificada no existe.")

    if socio_membresia.Estado != SocioMembresia.ESTADO_MOROSA:
        raise ValidationError(
            "Solo se generan alertas para membresías en estado moroso."
        )

    alerta, _ = AlertaPago.objects.get_or_create(
        SocioMembresiaID=socio_membresia,
        TipoAlerta=tipo_alerta,
        VistaEnPanel=False,
    )
    return alerta