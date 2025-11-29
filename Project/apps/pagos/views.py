from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.seguridad.decoradores import admin_requerido
from apps.pagos.servicios.pagos_service import (
    obtener_membresias_con_socios,
    obtener_estadisticas_pagos,
    registrar_pago_membresia
)
from apps.pagos.models import PlanMembresia, SocioMembresia
from apps.socios.models import Socio


@admin_requerido
def gestion_pagos_view(request):
    """Vista principal de gestión de pagos"""
    # Obtener filtros
    estado_filter = request.GET.get('estado', 'todos')
    plan_filter = request.GET.get('plan', 'todos')
    busqueda = request.GET.get('busqueda', '').strip()
    
    # Obtener todas las membresías
    membresias = obtener_membresias_con_socios()
    
    # Aplicar filtros
    if estado_filter != 'todos':
        membresias = membresias.filter(Estado=estado_filter)
    
    if plan_filter != 'todos':
        membresias = membresias.filter(PlanID__id=plan_filter)
    
    if busqueda:
        membresias = membresias.filter(
            SocioID__NombreCompleto__icontains=busqueda
        ) | membresias.filter(
            SocioID__Identificacion__icontains=busqueda
        )
    
    # Obtener estadísticas
    estadisticas = obtener_estadisticas_pagos()
    
    # Obtener todos los planes para el filtro
    planes = PlanMembresia.objects.all().order_by('Nombre')
    
    # Obtener todos los socios para el modal
    socios = Socio.objects.filter(Rol='Socio').order_by('NombreCompleto')
    
    context = {
        'membresias': membresias,
        'estadisticas': estadisticas,
        'planes': planes,
        'socios': socios,
        'estado_filter': estado_filter,
        'plan_filter': plan_filter,
        'busqueda': busqueda,
    }
    
    return render(request, "pagos/GestionPagos.html", context)


@admin_requerido
@require_http_methods(["POST"])
def registrar_pago_view(request):
    """Endpoint para registrar un pago de membresía"""
    try:
        socio_id = request.POST.get('socio_id')
        plan_id = request.POST.get('plan_id')
        monto = request.POST.get('monto')
        tipo_pago = request.POST.get('tipo_pago')
        comprobante_id = request.POST.get('comprobante_id', None)
        
        # Validar datos requeridos
        if not all([socio_id, plan_id, monto, tipo_pago]):
            return JsonResponse({
                'success': False,
                'error': 'Faltan datos requeridos'
            }, status=400)
        
        # Registrar el pago
        membresia, pago = registrar_pago_membresia(
            socio_id,
            plan_id,
            monto,
            tipo_pago,
            comprobante_id
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Pago registrado exitosamente',
            'membresia_id': membresia.id,
            'estado': membresia.Estado
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
