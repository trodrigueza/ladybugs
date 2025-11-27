from django.db import models


# === TABLA Socio ===
class Socio(models.Model):
    Identificacion = models.CharField(max_length=20, unique=True)
    NombreCompleto = models.CharField(max_length=100)
    Email = models.CharField(max_length=100, null=True, blank=True)
    Telefono = models.CharField(max_length=20, null=True, blank=True)
    FechaNacimiento = models.DateField(null=True, blank=True)

    ConsentimientoDatos = models.BooleanField(default=True)
    SaludBasica = models.TextField(null=True, blank=True)
    NotaOpcional = models.TextField(null=True, blank=True)

    Password = models.CharField(max_length=128, null=True, blank=True)
    Rol = models.CharField(max_length=20, default="Socio")
    Altura = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altura en metros",
    )

    def __str__(self):
        return f"{self.NombreCompleto} ({self.Rol})"


# === TABLA Medicion ===
class Medicion(models.Model):
    SocioID = models.ForeignKey(Socio, on_delete=models.CASCADE)

    Fecha = models.DateField()
    PesoCorporal = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    MedidasCorporales = models.TextField(null=True, blank=True)
    IMC = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)


class RegistroComidaDiaria(models.Model):
    SocioID = models.ForeignKey(
        Socio, on_delete=models.CASCADE, related_name="registros_comida"
    )
    DiaComidaID = models.ForeignKey(
        "control_acceso.DiaComida",
        on_delete=models.CASCADE,
        related_name="registros_consumo",
    )
    Fecha = models.DateField()
    Completado = models.BooleanField(default=False)
    HoraCompletado = models.DateTimeField(null=True, blank=True)
    Notas = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "registro_comida_diaria"
        ordering = ["-Fecha", "DiaComidaID"]
        unique_together = [["SocioID", "DiaComidaID", "Fecha"]]

    def __str__(self):
        estado = "✓" if self.Completado else "✗"
        return f"{self.SocioID.NombreCompleto} - {self.DiaComidaID.TipoComida} ({self.Fecha}) {estado}"
