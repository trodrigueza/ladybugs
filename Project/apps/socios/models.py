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

    def __str__(self):
        return self.NombreCompleto

# === TABLA Medicion ===
class Medicion(models.Model):
    SocioID = models.ForeignKey(Socio, on_delete=models.CASCADE)
    
    Fecha = models.DateField()
    PesoCorporal = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    MedidasCorporales = models.TextField(null=True, blank=True)
    IMC = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)