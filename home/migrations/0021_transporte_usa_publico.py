from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0017_docente_ativo'),
    ]

    operations = [
        migrations.AddField(
            model_name='transporteescolar',
            name='usa_transporte_publico',
            field=models.BooleanField(default=False),
        ),
    ]

