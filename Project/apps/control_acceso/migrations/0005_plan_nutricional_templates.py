from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_acceso", "0004_alter_rutinasemanal_socioid"),
    ]

    operations = [
        migrations.AddField(
            model_name="plannutricional",
            name="EsPlantilla",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plannutricional",
            name="Nombre",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name="plannutricional",
            name="SocioID",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="planes_nutricionales",
                to="socios.socio",
            ),
        ),
    ]
