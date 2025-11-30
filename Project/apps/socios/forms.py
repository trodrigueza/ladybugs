from django import forms

from apps.socios.models import Socio


class PerfilSocioForm(forms.ModelForm):
    peso_actual = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=0,
        label="Peso (kg)",
        widget=forms.NumberInput(
            attrs={
                "class": "w-full mt-1 p-2 rounded-md bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark focus:ring-2 focus:ring-primary focus:border-primary",
                "step": "0.1",
            }
        ),
    )

    class Meta:
        model = Socio
        fields = ["Telefono", "FechaNacimiento", "Altura"]
        labels = {
            "Telefono": "Teléfono",
            "FechaNacimiento": "Fecha de Nacimiento",
            "Altura": "Altura (m)",
        }
        widgets = {
            "Telefono": forms.TextInput(
                attrs={
                    "class": "w-full mt-1 p-2 rounded-md bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark focus:ring-2 focus:ring-primary focus:border-primary",
                }
            ),
            "FechaNacimiento": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full mt-1 p-2 rounded-md bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark focus:ring-2 focus:ring-primary focus:border-primary",
                }
            ),
            "Altura": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "class": "w-full mt-1 p-2 rounded-md bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark focus:ring-2 focus:ring-primary focus:border-primary",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        peso_inicial = kwargs.pop("peso_inicial", None)
        super().__init__(*args, **kwargs)
        if peso_inicial is not None:
            self.fields["peso_actual"].initial = peso_inicial

    def clean_peso_actual(self):
        peso = self.cleaned_data.get("peso_actual")
        if peso is None or peso <= 0:
            return None
        return peso
