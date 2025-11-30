from datetime import timedelta, datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Prefetch, Count, Q
from django.utils import timezone

from apps.pagos.models import PlanMembresia, SocioMembresia, Pago, AlertaPago
from apps.socios.models import Socio


class ValidationError(ValueError):
    """Error de validación usado en los servicios de pagos."""
    pass


def registrar_pago_membresia(socio_id, plan_id, monto, tipo_pago, comprobante_id=None):
    """
    Registra un pago de membresía para un socio.
    
    Lógica:
    - Si el socio NO tiene membresía activa → fecha_inicio = HOY
    - Si tiene membresía ACTIVA → fecha_inicio = fecha_fin_actual (extender)
    - Si tiene membresía MOROSA/EXPIRADA → fecha_inicio = HOY (renovar desde hoy)
    - Estado ACTIVA: monto >= precio del plan (pago completo)
    - Estado MOROSA: monto < precio del plan (pago incompleto)
    
    Returns:
        tuple: (SocioMembresia, Pago) - La membresía actualizada y el pago registrado
    """
    with transaction.atomic():
        # 1. Obtener socio y plan
        socio = Socio.objects.get(id=socio_id)
        plan = PlanMembresia.objects.get(id=plan_id)
        
        # 2. Buscar membresía existente del socio (la más reciente)
        membresia_existente = SocioMembresia.objects.filter(
            SocioID=socio
        ).order_by('-FechaFin').first()
        
        # 3. Determinar fechas de inicio y fin
        hoy = timezone.localdate()
        
        if membresia_existente and membresia_existente.Estado == SocioMembresia.ESTADO_ACTIVA:
            # Si está ACTIVA, extender desde la fecha_fin actual
            fecha_inicio = membresia_existente.FechaFin
        else:
            # Si NO tiene membresía, está MOROSA o EXPIRADA → iniciar desde HOY
            fecha_inicio = hoy
        
        fecha_fin = fecha_inicio + timedelta(days=plan.DuracionDias)
        
        # 4. Calcular monto pendiente y determinar estado
        monto_decimal = Decimal(str(monto))
        monto_pendiente = plan.Precio - monto_decimal
        if monto_pendiente < 0:
            monto_pendiente = Decimal('0.00')
        
        # Determinar estado: Activa si pago completo, Morosa si pago incompleto
        if monto_decimal >= plan.Precio:
            estado_membresia = SocioMembresia.ESTADO_ACTIVA
        else:
            estado_membresia = SocioMembresia.ESTADO_MOROSA
        
        # 5. Crear o actualizar SocioMembresia
        if membresia_existente:
            # Actualizar la membresía existente (sin importar su estado)
            # Si estaba Activa, extender desde fecha_fin
            # Si estaba Morosa o Expirada, las fechas ya se recalcularon desde HOY
            membresia_existente.PlanID = plan
            membresia_existente.FechaInicio = fecha_inicio
            membresia_existente.FechaFin = fecha_fin
            membresia_existente.Estado = estado_membresia
            membresia_existente.save()
            membresia = membresia_existente
        else:
            # Crear nueva membresía
            membresia = SocioMembresia.objects.create(
                SocioID=socio,
                PlanID=plan,
                FechaInicio=fecha_inicio,
                FechaFin=fecha_fin,
                Estado=estado_membresia
            )
        
        # 6. Crear registro de Pago
        pago = Pago.objects.create(
            SocioMembresiaID=membresia,
            Monto=monto_decimal,
            TipoPago=tipo_pago,
            FechaPago=timezone.now(),
            ComprobanteID=comprobante_id,
            MontoPendiente=monto_pendiente
        )
        
        return membresia, pago


def obtener_membresias_con_socios():
    """
    Obtiene todas las membresías con sus socios y planes.
    Actualiza automáticamente los estados de membresías que han expirado.
    
    Returns:
        QuerySet: Membresías ordenadas por fecha de fin (más recientes primero)
    """
    # Actualizar estados expirados antes de consultar
    actualizar_estados_membresias()
    
    membresias = SocioMembresia.objects.select_related(
        'SocioID', 'PlanID'
    ).prefetch_related(
        Prefetch('pagos', queryset=Pago.objects.order_by('-FechaPago'))
    ).order_by('-FechaFin')
    
    return membresias


def actualizar_estados_membresias():
    """
    Actualiza automáticamente el estado de las membresías:
    - De ACTIVA a EXPIRADA si FechaFin < hoy
    - De MOROSA a EXPIRADA si FechaFin < hoy
    
    Esta función se ejecuta cada vez que se consultan las membresías
    para mantener los estados actualizados.
    """
    hoy = timezone.localdate()
    
    # Actualizar membresías activas o morosas que ya expiraron
    membresias_expiradas = SocioMembresia.objects.filter(
        FechaFin__lt=hoy
    ).exclude(
        Estado=SocioMembresia.ESTADO_EXPIRADA
    )
    
    # Actualizar en batch para mejor rendimiento
    membresias_expiradas.update(Estado=SocioMembresia.ESTADO_EXPIRADA)


def obtener_estadisticas_pagos():
    """
    Calcula estadísticas para los cards de la página.
    
    Returns:
        dict: Diccionario con las estadísticas
    """
    hoy = timezone.localdate()
    primer_dia_mes = timezone.make_aware(datetime(hoy.year, hoy.month, 1))
    
    # Ingresos del mes actual
    ingresos_mes = Pago.objects.filter(
        FechaPago__gte=primer_dia_mes
    ).aggregate(total=Sum('Monto'))['total'] or Decimal('0.00')
    
    # Contar membresías por estado
    activas = SocioMembresia.objects.filter(Estado=SocioMembresia.ESTADO_ACTIVA).count()
    morosas = SocioMembresia.objects.filter(Estado=SocioMembresia.ESTADO_MOROSA).count()
    
    # Membresías que vencen en los próximos 7 días
    proximos_7_dias = hoy + timedelta(days=7)
    vencen_pronto = SocioMembresia.objects.filter(
        Estado=SocioMembresia.ESTADO_ACTIVA,
        FechaFin__gte=hoy,
        FechaFin__lte=proximos_7_dias
    ).count()
    
    return {
        'ingresos_mes': ingresos_mes,
        'activas': activas,
        'morosas': morosas,
        'vencen_pronto': vencen_pronto
    }


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


def registrar_pago_a_membresia_existente(
    socio_membresia_id,
    monto,
    tipo_pago=None,
    comprobante_id=None,
):
    """
    Registra un pago para una membresía EXISTENTE y actualiza el estado de la misma.

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