from django.contrib import admin
from .models import PlanMembresia, SocioMembresia, Pago, AlertaPago


@admin.register(PlanMembresia)
class PlanMembresiaAdmin(admin.ModelAdmin):
    list_display = ('Nombre', 'Precio', 'DuracionDias', 'Beneficios')
    search_fields = ('Nombre',)
    list_filter = ('DuracionDias',)
    ordering = ('Nombre',)


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ('Monto', 'TipoPago', 'FechaPago', 'ComprobanteID', 'MontoPendiente')
    readonly_fields = ('FechaPago',)


class AlertaPagoInline(admin.TabularInline):
    model = AlertaPago
    extra = 0
    fields = ('TipoAlerta', 'FechaGeneracion', 'VistaEnPanel')
    readonly_fields = ('FechaGeneracion',)


@admin.register(SocioMembresia)
class SocioMembresiaAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_socio_nombre', 'PlanID', 'FechaInicio', 'FechaFin', 'Estado', 'get_dias_restantes')
    list_filter = ('Estado', 'PlanID', 'FechaInicio', 'FechaFin')
    search_fields = ('SocioID__NombreCompleto', 'SocioID__Email', 'SocioID__Identificacion')
    date_hierarchy = 'FechaInicio'
    ordering = ('-FechaInicio',)
    
    fieldsets = (
        ('Información del Socio', {
            'fields': ('SocioID',)
        }),
        ('Detalles de la Membresía', {
            'fields': ('PlanID', 'FechaInicio', 'FechaFin', 'Estado')
        }),
    )
    
    inlines = [PagoInline, AlertaPagoInline]
    
    def get_socio_nombre(self, obj):
        return obj.SocioID.NombreCompleto if hasattr(obj.SocioID, 'NombreCompleto') else str(obj.SocioID)
    get_socio_nombre.short_description = 'Socio'
    get_socio_nombre.admin_order_field = 'SocioID__NombreCompleto'
    
    def get_dias_restantes(self, obj):
        dias = obj.remaining_days()
        if dias < 0:
            return f"Expirada ({abs(dias)} días)"
        return f"{dias} días"
    get_dias_restantes.short_description = 'Días Restantes'


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_socio', 'Monto', 'TipoPago', 'FechaPago', 'MontoPendiente', 'ComprobanteID')
    list_filter = ('TipoPago', 'FechaPago')
    search_fields = ('SocioMembresiaID__SocioID__NombreCompleto', 'ComprobanteID')
    date_hierarchy = 'FechaPago'
    ordering = ('-FechaPago',)
    readonly_fields = ('FechaPago',)
    
    fieldsets = (
        ('Información de Pago', {
            'fields': ('SocioMembresiaID', 'Monto', 'TipoPago', 'FechaPago')
        }),
        ('Detalles Adicionales', {
            'fields': ('ComprobanteID', 'MontoPendiente')
        }),
    )
    
    def get_socio(self, obj):
        return obj.SocioMembresiaID.SocioID.NombreCompleto if hasattr(obj.SocioMembresiaID.SocioID, 'NombreCompleto') else str(obj.SocioMembresiaID.SocioID)
    get_socio.short_description = 'Socio'
    get_socio.admin_order_field = 'SocioMembresiaID__SocioID__NombreCompleto'


@admin.register(AlertaPago)
class AlertaPagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_socio', 'TipoAlerta', 'FechaGeneracion', 'VistaEnPanel')
    list_filter = ('TipoAlerta', 'VistaEnPanel', 'FechaGeneracion')
    search_fields = ('SocioMembresiaID__SocioID__NombreCompleto',)
    date_hierarchy = 'FechaGeneracion'
    ordering = ('-FechaGeneracion',)
    readonly_fields = ('FechaGeneracion',)
    
    def get_socio(self, obj):
        return obj.SocioMembresiaID.SocioID.NombreCompleto if hasattr(obj.SocioMembresiaID.SocioID, 'NombreCompleto') else str(obj.SocioMembresiaID.SocioID)
    get_socio.short_description = 'Socio'
    get_socio.admin_order_field = 'SocioMembresiaID__SocioID__NombreCompleto'
