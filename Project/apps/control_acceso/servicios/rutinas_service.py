from django.db import IntegrityError, transaction

from apps.control_acceso.models import DiaRutinaEjercicio, Ejercicio, RutinaSemanal
from apps.socios.models import Socio


class ValidationError(ValueError):
    pass


def validar_dia_semana(dia_semana):
    """
    Valida que el día de la semana esté en el rango válido (0-6).
    """
    if not isinstance(dia_semana, int) or dia_semana < 0 or dia_semana > 6:
        raise ValidationError(
            "El día de la semana debe ser un número entre 0 (lunes) y 6 (domingo)."
        )


def validar_valores_positivos(series=None, repeticiones=None, peso_objetivo=None):
    """
    Valida que series, repeticiones y peso sean valores positivos.
    """
    if series is not None and series <= 0:
        raise ValidationError("Las series deben ser un número positivo.")

    if repeticiones is not None and repeticiones <= 0:
        raise ValidationError("Las repeticiones deben ser un número positivo.")

    if peso_objetivo is not None and peso_objetivo < 0:
        raise ValidationError("El peso objetivo no puede ser negativo.")


def crear_rutina_semanal(socio_id, nombre, dias_entrenamiento, es_plantilla=False):
    """
    Crea una rutina semanal para un socio.

    Args:
        socio_id: ID del socio
        nombre: Nombre de la rutina
        dias_entrenamiento: String representando días (ej: "LMXJVSD")
        es_plantilla: Boolean indicando si es plantilla

    Returns:
        Objeto RutinaSemanal creado

    Raises:
        ValidationError: Si el socio no existe o los datos son inválidos
    """
    # Si es plantilla (es_plantilla=True) permitimos socio_id=None y no intentamos buscar socio
    socio = None
    if not es_plantilla:
        try:
            socio = Socio.objects.get(id=socio_id)
        except Socio.DoesNotExist:
            raise ValidationError("El socio especificado no existe.")

    if not nombre or not nombre.strip():
        raise ValidationError("El nombre de la rutina es obligatorio.")

    if not dias_entrenamiento or not dias_entrenamiento.strip():
        raise ValidationError("Debes especificar los días de entrenamiento.")

    with transaction.atomic():
        rutina = RutinaSemanal.objects.create(
            SocioID=socio,
            Nombre=nombre.strip(),
            DiasEntrenamiento=dias_entrenamiento.strip(),
            EsPlantilla=es_plantilla,
        )
        return rutina


def asignar_ejercicio_a_rutina(
    rutina_id,
    ejercicio_id,
    dia_semana,
    series=None,
    repeticiones=None,
    tempo=None,
    peso_objetivo=None,
):
    """
    Asigna un ejercicio a un día específico de una rutina.

    Args:
        rutina_id: ID de la rutina
        ejercicio_id: ID del ejercicio
        dia_semana: Día de la semana (0-6)
        series: Número de series (opcional)
        repeticiones: Número de repeticiones (opcional)
        tempo: Tempo del ejercicio (opcional, ej: "3-0-1-0")
        peso_objetivo: Peso objetivo en kg (opcional)

    Returns:
        Objeto DiaRutinaEjercicio creado

    Raises:
        ValidationError: Si los datos son inválidos o ya existe la asignación
    """
    try:
        rutina = RutinaSemanal.objects.get(id=rutina_id)
    except RutinaSemanal.DoesNotExist:
        raise ValidationError("La rutina especificada no existe.")

    try:
        ejercicio = Ejercicio.objects.get(id=ejercicio_id)
    except Ejercicio.DoesNotExist:
        raise ValidationError("El ejercicio especificado no existe.")

    validar_dia_semana(dia_semana)
    validar_valores_positivos(series, repeticiones, peso_objetivo)

    try:
        with transaction.atomic():
            dia_rutina_ejercicio = DiaRutinaEjercicio.objects.create(
                RutinaID=rutina,
                EjercicioID=ejercicio,
                DiaSemana=dia_semana,
                Series=series,
                Repeticiones=repeticiones,
                Tempo=tempo or "",
                PesoObjetivo=peso_objetivo,
            )
            return dia_rutina_ejercicio
    except IntegrityError:
        raise ValidationError(
            f"Ya existe este ejercicio asignado en el día {dia_semana} de esta rutina."
        )


def obtener_ejercicios_por_dia(rutina_id, dia_semana):
    """
    Obtiene todos los ejercicios asignados a un día específico de una rutina.

    Args:
        rutina_id: ID de la rutina
        dia_semana: Día de la semana (0-6)

    Returns:
        QuerySet de DiaRutinaEjercicio
    """
    validar_dia_semana(dia_semana)

    return DiaRutinaEjercicio.objects.filter(
        RutinaID_id=rutina_id, DiaSemana=dia_semana
    ).select_related("EjercicioID")
