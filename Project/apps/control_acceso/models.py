from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# Referencias a otras apps hechas por string ("app_label.ModelName")
# Evita importaciones directas como `from socios.persistencia.models import Socio`

# === TABLA Ejercicio ===
class Ejercicio(models.Model):
    Nombre = models.CharField(max_length=100)
    GrupoMuscular = models.CharField(max_length=50, null=True, blank=True)
    Equipo = models.CharField(max_length=50, null=True, blank=True)
    Descripcion = models.TextField(null=True, blank=True)
    Variantes = models.TextField(null=True, blank=True)
    Version = models.PositiveIntegerField(default=1)

    # Referencia por string para evitar importaciones circulares
    UsuarioVersionID = models.ForeignKey(
        "seguridad.Usuario", on_delete=models.SET_NULL, null=True, blank=True, related_name="ejercicios_versionados"
    )

    FechaVersion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        ordering = ["Nombre"]
        db_table = "ejercicio"


# === TABLA Alimento ===
class Alimento(models.Model):
    Nombre = models.CharField(max_length=100)
    PorcionBase = models.CharField(max_length=50, null=True, blank=True)
    Kcal = models.PositiveIntegerField(null=True, blank=True)
    Macros = models.TextField(null=True, blank=True)
    Version = models.PositiveIntegerField(default=1)

    UsuarioVersionID = models.ForeignKey(
        "seguridad.Usuario", on_delete=models.SET_NULL, null=True, blank=True, related_name="alimentos_versionados"
    )

    FechaVersion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        ordering = ["Nombre"]
        db_table = "alimento"


# === TABLA Asistencia ===
class Asistencia(models.Model):
    SocioMembresiaID = models.ForeignKey(
        "pagos.SocioMembresia", on_delete=models.CASCADE, related_name="asistencias"
    )

    FechaHoraEntrada = models.DateTimeField()
    FechaHoraSalida = models.DateTimeField(null=True, blank=True)
    TerminalAcceso = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Asistencia {self.id} - {self.SocioMembresiaID_id} - {self.FechaHoraEntrada}"

    class Meta:
        ordering = ["-FechaHoraEntrada"]
        db_table = "asistencia"


# === TABLA RutinaSemanal ===
class RutinaSemanal(models.Model):
    SocioID = models.ForeignKey("socios.Socio", on_delete=models.CASCADE, related_name="rutinas")
    Nombre = models.CharField(max_length=100, null=True, blank=True)
    DiasEntrenamiento = models.CharField(max_length=7, help_text="Ej: LMXJVSD (Lunes..Domingo) o similar")
    EsPlantilla = models.BooleanField(default=False)

    def __str__(self):
        return self.Nombre or f"Rutina {self.id}"

    class Meta:
        ordering = ["-EsPlantilla", "Nombre"]
        db_table = "rutina_semanal"


# === TABLA dia_rutina_ejercicio (Tabla de relación) ===
class DiaRutinaEjercicio(models.Model):
    RutinaID = models.ForeignKey(RutinaSemanal, on_delete=models.CASCADE, related_name="dias_ejercicios")
    EjercicioID = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name="en_rutinas")
    DiaSemana = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])  # 0=lunes/0-6 según convención
    Series = models.PositiveIntegerField(null=True, blank=True)
    Repeticiones = models.PositiveIntegerField(null=True, blank=True)
    Tempo = models.CharField(max_length=10, null=True, blank=True)
    PesoObjetivo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])

    def __str__(self):
        return f"Rutina {self.RutinaID_id} - Ejercicio {self.EjercicioID_id} (día {self.DiaSemana})"

    class Meta:
        db_table = "dia_rutina_ejercicio"
        constraints = [
            models.UniqueConstraint(fields=["RutinaID", "EjercicioID", "DiaSemana"], name="u_rutina_ejercicio_dia")
        ]
        ordering = ["RutinaID", "DiaSemana"]


# === TABLA EjecucionSesion ===
class EjecucionSesion(models.Model):
    DiaRutinaEjercicioID = models.ForeignKey(DiaRutinaEjercicio, on_delete=models.CASCADE, related_name="ejecuciones")
    FechaEjecucion = models.DateField()
    PesoEfectivo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    SeriesEfectivas = models.PositiveIntegerField(null=True, blank=True)
    RPE = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)])
    Notas = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Ejecución {self.id} - {self.FechaEjecucion}"

    class Meta:
        ordering = ["-FechaEjecucion"]
        db_table = "ejecucion_sesion"


# === TABLA PlanNutricional ===
class PlanNutricional(models.Model):
    SocioID = models.ForeignKey("socios.Socio", on_delete=models.CASCADE, related_name="planes_nutricionales")
    ObjetivoCaloricoDiario = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"PlanNutricional {self.id} - Socio {self.SocioID_id}"

    class Meta:
        db_table = "plan_nutricional"


# === TABLA DiaComida ===
class DiaComida(models.Model):
    PlanNutricionalID = models.ForeignKey(PlanNutricional, on_delete=models.CASCADE, related_name="dias_comida")
    DiaSemana = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])  # 0-6
    TipoComida = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Dia {self.DiaSemana} - {self.TipoComida or ''}"

    class Meta:
        db_table = "dia_comida"
        ordering = ["PlanNutricionalID", "DiaSemana"]


# === TABLA comida_alimento (Tabla de relación) ===
class ComidaAlimento(models.Model):
    DiaComidaID = models.ForeignKey(DiaComida, on_delete=models.CASCADE, related_name="alimentos")
    AlimentoID = models.ForeignKey(Alimento, on_delete=models.CASCADE, related_name="en_comidas")
    Porcion = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    Cantidad = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"ComidaAlimento {self.id} - {self.AlimentoID_id}"

    class Meta:
        db_table = "comida_alimento"
        ordering = ["DiaComidaID"]