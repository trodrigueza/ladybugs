from django import forms
from apps.socios.models import Socio
from apps.pagos.models import SocioMembresia
from apps.seguridad.models import Usuario, Rol
from django.contrib.auth.hashers import make_password


class SocioForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary',
            'placeholder': 'Ingrese contraseña para el socio'
        }),
        required=False,
        help_text="En creación: obligatorio. En edición: dejar en blanco para mantener la contraseña actual"
    )
    
    class Meta:
        model = Socio
        fields = ["Identificacion", "NombreCompleto", "Email", "Telefono", "FechaNacimiento", "Altura", "SaludBasica", "NotaOpcional"]
        labels = {
            "Identificacion": "Identificación/Cédula",
            "NombreCompleto": "Nombre Completo",
            "Email": "Correo Electrónico",
            "Telefono": "Teléfono",
            "FechaNacimiento": "Fecha de Nacimiento",
            "Altura": "Altura (metros)",
            "SaludBasica": "Información de Salud",
            "NotaOpcional": "Nota Adicional"
        }
        widgets = {
            "FechaNacimiento": forms.DateInput(attrs={'type': 'date'}),
            "SaludBasica": forms.Textarea(attrs={'rows': 3}),
            "NotaOpcional": forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_Email(self):
        """Validar que el email sea obligatorio"""
        email = self.cleaned_data.get('Email')
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio para que el socio pueda iniciar sesión.")
        return email


class UsuarioForm(forms.ModelForm):
    """Formulario para crear y editar Usuarios (Administrativos, Entrenadores, etc.)"""
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Dejar en blanco para mantener la contraseña actual (o usar contraseña temporal en creación)"
    )
    
    class Meta:
        model = Usuario
        fields = ["NombreUsuario", "Email", "RolID"]
        labels = {
            "NombreUsuario": "Nombre de Usuario",
            "Email": "Correo Electrónico",
            "RolID": "Rol"
        }
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Si se proporciona contraseña, hashearla
        if self.cleaned_data.get('password'):
            from django.contrib.auth.hashers import make_password
            usuario.PasswordHash = make_password(self.cleaned_data['password'])
        # Si es creación (no existe id) y no hay contraseña, usar una por defecto
        elif not usuario.id:
            from django.contrib.auth.hashers import make_password
            usuario.PasswordHash = make_password('DefaultPassword123!')
        
        if commit:
            usuario.save()
        return usuario


class SocioMembresiaForm(forms.ModelForm):
    class Meta:
        model = SocioMembresia
        fields = ["PlanID", "FechaInicio", "FechaFin", "Estado"]
        labels = {
            "PlanID": "Plan de Membresía",
            "FechaInicio": "Fecha de Inicio",
            "FechaFin": "Fecha de Fin",
            "Estado": "Estado"
        }
        widgets = {
            "FechaInicio": forms.DateInput(attrs={
                'type': 'date',
                'id': 'id_FechaInicio',
                'readonly': 'readonly',
                'class': 'bg-gray-100'
            }),
            "FechaFin": forms.DateInput(attrs={
                'type': 'date',
                'id': 'id_FechaFin',
                'readonly': 'readonly',
                'class': 'bg-gray-100'
            }),
            "Estado": forms.Select(attrs={'id': 'id_Estado'}),
            "PlanID": forms.Select(attrs={'id': 'id_PlanID'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer estado Activa por defecto
        if not self.instance.pk:  # Solo en creación
            self.initial['Estado'] = SocioMembresia.ESTADO_ACTIVA
            # Establecer fecha de inicio como hoy
            from django.utils import timezone
            self.initial['FechaInicio'] = timezone.localdate()
