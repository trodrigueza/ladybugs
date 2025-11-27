import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("control_acceso", "0003_sesionentrenamiento_esentrenamientolibre_and_more"),
        ("socios", "0004_socio_altura"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistroComidaDiaria",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("Fecha", models.DateField()),
                ("Completado", models.BooleanField(default=False)),
                ("HoraCompletado", models.DateTimeField(blank=True, null=True)),
                ("Notas", models.TextField(blank=True, null=True)),
                (
                    "DiaComidaID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registros_consumo",
                        to="control_acceso.diacomida",
                    ),
                ),
                (
                    "SocioID",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registros_comida",
                        to="socios.socio",
                    ),
                ),
            ],
            options={
                "db_table": "registro_comida_diaria",
                "ordering": ["-Fecha", "DiaComidaID"],
                "unique_together": {("SocioID", "DiaComidaID", "Fecha")},
            },
        ),
    ]
