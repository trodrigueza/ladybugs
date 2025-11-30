"""
Servicio para calcular estadísticas del dashboard administrativo
"""
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q
from apps.socios.models import Socio
from apps.pagos.models import SocioMembresia, Pago
import calendar
    

def obtener_estadisticas_dashboard():

    hoy = timezone.now()
    
    total_socios = Socio.objects.count()
    
    hace_30_dias = hoy - timedelta(days=30)
    
    nuevos_socios = Socio.objects.filter(
        membresias__FechaInicio__gte=hace_30_dias
    ).distinct().count()
    
    primer_dia_mes = timezone.make_aware(timezone.datetime(hoy.year, hoy.month, 1))
    ingresos_mes = Pago.objects.filter(
        FechaPago__gte=primer_dia_mes
    ).aggregate(total=Sum('Monto'))['total'] or 0
    
    suscripciones_activas = SocioMembresia.objects.filter(Estado='Activa').count()
    
    return {
        'total_socios': total_socios,
        'nuevos_socios': nuevos_socios,
        'ingresos_mes': ingresos_mes,
        'suscripciones_activas': suscripciones_activas,
    }


def obtener_estadisticas_pagos_dashboard():
    
    socios_con_membresia = Socio.objects.filter(membresias__isnull=False).distinct()
    
    activas = 0
    morosas = 0
    expiradas = 0
    
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

    hoy = timezone.now()
    
    nombres_meses = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    datos_mensuales = []
    
    for i in range(5, -1, -1): 
        mes_actual = hoy.month - i
        año_actual = hoy.year
        
        while mes_actual <= 0:
            mes_actual += 12
            año_actual -= 1
        
        primer_dia = timezone.datetime(año_actual, mes_actual, 1)
        primer_dia = timezone.make_aware(primer_dia)
        
        ultimo_dia_num = calendar.monthrange(año_actual, mes_actual)[1]
        ultimo_dia = timezone.datetime(año_actual, mes_actual, ultimo_dia_num, 23, 59, 59)
        ultimo_dia = timezone.make_aware(ultimo_dia)

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
