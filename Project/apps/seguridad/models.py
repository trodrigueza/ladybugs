from django.db import models

# === TABLA Rol ===
class Rol(models.Model):
    # id (PK) se crea automáticamente
    NombreRol = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.NombreRol
    
# === TABLA Usuario ===
class Usuario(models.Model):
    NombreUsuario = models.CharField(max_length=50, unique=True)
    PasswordHash = models.CharField(max_length=255) 
    
    RolID = models.ForeignKey(Rol, on_delete=models.PROTECT)
    
    UltimoAcceso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.NombreUsuario

# === TABLA RegistroAuditoria ===
class RegistroAuditoria(models.Model):

    UsuarioID = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    
    FechaHora = models.DateTimeField(auto_now_add=True)
    TipoAccion = models.CharField(max_length=50)
    Detalle = models.TextField()