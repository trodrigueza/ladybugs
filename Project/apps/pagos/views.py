from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
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
    
    # Obtener todos los socios para el modal con sus membresías actuales
    socios = Socio.objects.filter(Rol='Socio').order_by('NombreCompleto')
    
    # Crear diccionario con membresía actual de cada socio (plan_id y precio)
    import json
    socios_membresias = {}
    for socio in socios:
        membresia_actual = SocioMembresia.objects.filter(
            SocioID=socio
        ).select_related('PlanID').order_by('-FechaInicio').first()
        
        # Sólo registrar la membresía si existe y tiene un Plan asociado
        if membresia_actual and getattr(membresia_actual, 'PlanID', None) is not None:
            socios_membresias[socio.id] = {
                'plan_id': membresia_actual.PlanID.id,
                'precio': float(membresia_actual.PlanID.Precio)
            }
    
    socios_membresias_json = json.dumps(socios_membresias)
    
    context = {
        'membresias': membresias,
        'estadisticas': estadisticas,
        'planes': planes,
        'socios': socios,
        'socios_membresias_json': socios_membresias_json,
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


@admin_requerido
def editar_plan_membresia_view(request, plan_id):
    """Vista para editar un plan de membresía"""
    try:
        plan = PlanMembresia.objects.get(id=plan_id)
    except PlanMembresia.DoesNotExist:
        messages.error(request, 'El plan solicitado no existe')
        return redirect('gestion_pagos')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        precio = request.POST.get('precio', '').strip()
        duracion_dias = request.POST.get('duracion_dias', '').strip()
        beneficios = request.POST.get('beneficios', '').strip()

        # Validaciones básicas
        if not nombre:
            messages.error(request, 'El nombre del plan es obligatorio')
            return redirect('editar_plan_membresia', plan_id=plan.id)

        try:
            if not precio or float(precio) <= 0:
                messages.error(request, 'El precio debe ser mayor a 0')
                return redirect('editar_plan_membresia', plan_id=plan.id)
        except ValueError:
            messages.error(request, 'Precio inválido')
            return redirect('editar_plan_membresia', plan_id=plan.id)

        try:
            if not duracion_dias or int(duracion_dias) <= 0:
                messages.error(request, 'La duración debe ser mayor a 0 días')
                return redirect('editar_plan_membresia', plan_id=plan.id)
        except ValueError:
            messages.error(request, 'Duración inválida')
            return redirect('editar_plan_membresia', plan_id=plan.id)

        # Evitar colisiones de nombre con otros planes
        if PlanMembresia.objects.filter(Nombre__iexact=nombre).exclude(id=plan.id).exists():
            messages.error(request, 'Ya existe otro plan con ese nombre')
            return redirect('editar_plan_membresia', plan_id=plan.id)

        # Actualizar
        plan.Nombre = nombre
        plan.Precio = precio
        plan.DuracionDias = int(duracion_dias)
        plan.Beneficios = beneficios if beneficios else None
        plan.save()

        messages.success(request, f'Plan "{plan.Nombre}" actualizado correctamente')
        return redirect('gestion_pagos')

    # GET -> renderizar formulario con datos del plan
    return render(request, 'pagos/CrearPlanMembresia.html', {'plan': plan})


@admin_requerido
def crear_plan_membresia_view(request):
    """Vista para crear un nuevo plan de membresía"""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()
            precio = request.POST.get('precio', '').strip()
            duracion_dias = request.POST.get('duracion_dias', '').strip()
            beneficios = request.POST.get('beneficios', '').strip()
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del plan es obligatorio')
                return redirect('crear_plan_membresia')
            
            if not precio or float(precio) <= 0:
                messages.error(request, 'El precio debe ser mayor a 0')
                return redirect('crear_plan_membresia')
            
            if not duracion_dias or int(duracion_dias) <= 0:
                messages.error(request, 'La duración debe ser mayor a 0 días')
                return redirect('crear_plan_membresia')
            
            # Verificar si ya existe un plan con ese nombre
            if PlanMembresia.objects.filter(Nombre__iexact=nombre).exists():
                messages.error(request, 'Ya existe un plan con ese nombre')
                return redirect('crear_plan_membresia')
            
            # Crear el plan
            plan = PlanMembresia.objects.create(
                Nombre=nombre,
                Precio=precio,
                DuracionDias=int(duracion_dias),
                Beneficios=beneficios if beneficios else None
            )
            
            messages.success(request, f'Plan "{plan.Nombre}" creado exitosamente')
            return redirect('gestion_pagos')
            
        except ValueError as e:
            messages.error(request, 'Error en los datos ingresados. Verifica los valores numéricos')
            return redirect('crear_plan_membresia')
        except Exception as e:
            messages.error(request, f'Error al crear el plan: {str(e)}')
            return redirect('crear_plan_membresia')
    
    return render(request, 'pagos/CrearPlanMembresia.html')


@admin_requerido
@require_http_methods(["POST"])
def eliminar_plan_membresia_view(request, plan_id):
    """Vista para eliminar un plan de membresía"""
    try:
        plan = PlanMembresia.objects.get(id=plan_id)
        
        # Contar socios afectados
        socios_afectados = SocioMembresia.objects.filter(PlanID=plan).count()
        
        # Actualizar membresías de socios afectados: quitar plan y cambiar a Morosa
        SocioMembresia.objects.filter(PlanID=plan).update(
            Estado=SocioMembresia.ESTADO_MOROSA
        )
        
        # Eliminar el plan (ahora SET_NULL se encargará de poner PlanID=NULL)
        nombre_plan = plan.Nombre
        plan.delete()
        
        mensaje = f'Plan "{nombre_plan}" eliminado exitosamente.'
        if socios_afectados > 0:
            mensaje += f' {socios_afectados} socio(s) afectado(s) - estado cambiado a Moroso.'
        
        return JsonResponse({
            'success': True,
            'message': mensaje
        })
        
    except PlanMembresia.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'El plan no existe'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
