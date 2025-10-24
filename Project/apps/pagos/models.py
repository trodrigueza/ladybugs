from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

# === TABLA PlanMembresia ===
class PlanMembresia(models.Model):
    Nombre = models.CharField(max_length=50, unique=True)
    Precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    DuracionDias = models.IntegerField()
    Beneficios = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        verbose_name = "Plan de Membresía"
        verbose_name_plural = "Planes de Membresía"
        ordering = ["Nombre"]


# === TABLA SocioMembresia ===
class SocioMembresia(models.Model):
    SocioID = models.ForeignKey("socios.Socio", on_delete=models.CASCADE, related_name="membresias")
    PlanID = models.ForeignKey(PlanMembresia, on_delete=models.PROTECT, related_name="socio_membresias")

    FechaInicio = models.DateField()
    FechaFin = models.DateField()
    ESTADO_ACTIVA = "Activa"
    ESTADO_MOROSA = "Morosa"
    ESTADO_EXPIRADA = "Expirada"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVA, "Activa"),
        (ESTADO_MOROSA, "Morosa"),
        (ESTADO_EXPIRADA, "Expirada"),
    ]
    Estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ACTIVA)

    def __str__(self):
        nombre = getattr(self.SocioID, "NombreCompleto", str(self.SocioID))
        return f"Membresía {self.id} de {nombre}"

    class Meta:
        verbose_name_plural = "Socio Membresías"
        db_table = "socio_membresia"
        ordering = ["-FechaInicio"]

    def is_active(self):
        today = timezone.localdate()
        return self.FechaInicio <= today <= self.FechaFin and self.Estado == self.ESTADO_ACTIVA

    def remaining_days(self):
        return (self.FechaFin - timezone.localdate()).days


# === TABLA Pago ===
class Pago(models.Model):
    SocioMembresiaID = models.ForeignKey(SocioMembresia, on_delete=models.CASCADE, related_name="pagos")

    Monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    TipoPago = models.CharField(max_length=50, null=True, blank=True)  # opcional: usar choices
    FechaPago = models.DateTimeField(default=timezone.now)
    ComprobanteID = models.CharField(max_length=50, null=True, blank=True)
    MontoPendiente = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])

    def __str__(self):
        return f"Pago {self.id} - {self.Monto} ({self.SocioMembresiaID_id})"

    class Meta:
        ordering = ["-FechaPago"]
        db_table = "pago"


# === TABLA AlertaPago ===
class AlertaPago(models.Model):
    SocioMembresiaID = models.ForeignKey(SocioMembresia, on_delete=models.CASCADE, related_name="alertas")

    TipoAlerta = models.CharField(max_length=50, null=True, blank=True)
    FechaGeneracion = models.DateField(default=timezone.localdate)
    VistaEnPanel = models.BooleanField(default=False)

    def __str__(self):
        return f"Alerta {self.id} para Membresía {self.SocioMembresiaID_id}"

    class Meta:
        ordering = ["-FechaGeneracion"]
        db_table = "alerta_pago"