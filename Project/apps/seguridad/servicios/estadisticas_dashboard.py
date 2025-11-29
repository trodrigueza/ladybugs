"""
Servicio para calcular estadísticas del dashboard administrativo
"""
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q
from apps.socios.models import Socio
from apps.pagos.models import SocioMembresia, Pago


def obtener_estadisticas_dashboard():
    """
    Calcula todas las estadísticas para el panel de administración
    
    Returns:
        dict: Diccionario con las estadísticas:
            - total_socios: Total de socios registrados
            - nuevos_socios: Socios registrados en los últimos 30 días
            - ingresos_mes: Suma de pagos del mes actual
            - suscripciones_activas: Membresías con estado 'Activa'
    """
    hoy = timezone.now()
    
    # Total de socios
    total_socios = Socio.objects.count()
    
    # Nuevos socios en los últimos 30 días
    # Como no hay FechaRegistro, usamos el id (socios recientes tienen IDs más altos)
    # O podemos usar la fecha de la membresía más antigua
    hace_30_dias = hoy - timedelta(days=30)
    
    # Contar socios que tienen al menos una membresía creada en los últimos 30 días
    nuevos_socios = Socio.objects.filter(
        membresias__FechaInicio__gte=hace_30_dias
    ).distinct().count()
    
    # Ingresos del mes actual
    primer_dia_mes = timezone.make_aware(timezone.datetime(hoy.year, hoy.month, 1))
    ingresos_mes = Pago.objects.filter(
        FechaPago__gte=primer_dia_mes
    ).aggregate(total=Sum('Monto'))['total'] or 0
    
    # Suscripciones activas
    suscripciones_activas = SocioMembresia.objects.filter(Estado='Activa').count()
    
    return {
        'total_socios': total_socios,
        'nuevos_socios': nuevos_socios,
        'ingresos_mes': ingresos_mes,
        'suscripciones_activas': suscripciones_activas,
    }


def obtener_estadisticas_pagos_dashboard():
    """
    Calcula estadísticas específicas de pagos para el gráfico de dona.
    Solo cuenta la membresía MÁS RECIENTE de cada socio (no todo el historial).
    
    Returns:
        dict: Diccionario con:
            - total: Total de socios con membresía
            - activas: Socios con membresía más reciente en estado 'Activa'
            - morosas: Socios con membresía más reciente en estado 'Morosa'
            - expiradas: Socios con membresía más reciente en estado 'Expirada'
    """
    from django.db.models import Max
    
    # Obtener todos los socios que tienen al menos una membresía
    socios_con_membresia = Socio.objects.filter(membresias__isnull=False).distinct()
    
    activas = 0
    morosas = 0
    expiradas = 0
    
    # Para cada socio, obtener su membresía más reciente
    for socio in socios_con_membresia:
        membresia_actual = socio.membresias.order_by('-FechaInicio').first()
        
        if membresia_actual:
            if membresia_actual.Estado == 'Activa':
                activas += 1
            elif membresia_actual.Estado == 'Morosa':
                morosas += 1
            elif membresia_actual.Estado == 'Expirada':
                expiradas += 1
    
    total = activas + morosas + expiradas
    
    return {
        'total': total,
        'activas': activas,
        'morosas': morosas,
        'expiradas': expiradas,
    }


def obtener_actividad_plataforma():
    """
    Calcula el número de socios registrados por mes en los últimos 6 meses.
    Se basa en la fecha de la primera membresía de cada socio.
    
    Returns:
        dict: Diccionario con:
            - meses: Lista de nombres de meses ['Ene', 'Feb', ...]
            - datos: Lista de números de socios registrados por mes
            - max_valor: Valor máximo para escalar el gráfico
    """
    from datetime import datetime
    import calendar
    
    hoy = timezone.now()
    
    # Nombres de meses en español (abreviados)
    nombres_meses = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    # Inicializar últimos 6 meses con 0 (de más antiguo a más reciente)
    datos_mensuales = []
    
    for i in range(5, -1, -1):  # 5, 4, 3, 2, 1, 0 (de más antiguo a más reciente)
        # Calcular el año y mes
        mes_actual = hoy.month - i
        año_actual = hoy.year
        
        # Ajustar si el mes es negativo o cero
        while mes_actual <= 0:
            mes_actual += 12
            año_actual -= 1
        
        # Primer día del mes
        primer_dia = timezone.datetime(año_actual, mes_actual, 1)
        primer_dia = timezone.make_aware(primer_dia)
        
        # Último día del mes
        ultimo_dia_num = calendar.monthrange(año_actual, mes_actual)[1]
        ultimo_dia = timezone.datetime(año_actual, mes_actual, ultimo_dia_num, 23, 59, 59)
        ultimo_dia = timezone.make_aware(ultimo_dia)
        
        # Contar socios que obtuvieron su primera membresía en este mes
        count = 0
        socios = Socio.objects.filter(
            membresias__FechaInicio__gte=primer_dia,
            membresias__FechaInicio__lte=ultimo_dia
        ).distinct()
        
        for socio in socios:
            primera_membresia = socio.membresias.order_by('FechaInicio').first()
            if primera_membresia and primer_dia.date() <= primera_membresia.FechaInicio <= ultimo_dia.date():
                count += 1
        
        datos_mensuales.append({
            'nombre': nombres_meses[mes_actual],
            'count': count
        })
    
    meses = [item['nombre'] for item in datos_mensuales]
    datos = [item['count'] for item in datos_mensuales]
    max_valor = max(datos) if datos and max(datos) > 0 else 1
    
    return {
        'meses': meses,
        'datos': datos,
        'max_valor': max_valor,
    }
