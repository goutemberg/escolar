from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("home", "0025_diariodeclasse_status_alter_chamada_criado_por_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Nota"),
            ],
        ),
    ]
