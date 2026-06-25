from django.db import migrations


def popular_campos_chamada(apps, schema_editor):
    Chamada = apps.get_model("home", "Chamada")

    total = 0

    for chamada in Chamada.objects.select_related("diario"):

        if not chamada.diario:
            continue

        chamada.turma_id = chamada.diario.turma_id
        chamada.disciplina_id = chamada.diario.disciplina_id
        chamada.professor_id = chamada.diario.professor_id
        chamada.data = chamada.diario.data_ministrada
        chamada.escola_id = chamada.diario.escola_id

        chamada.save(update_fields=[
            "turma",
            "disciplina",
            "professor",
            "data",
            "escola",
        ])

        total += 1

    print(f"{total} chamadas atualizadas.")


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0065_chamada_data_chamada_disciplina_chamada_escola_and_more"),
    ]

    operations = [
        migrations.RunPython(
            popular_campos_chamada,
            migrations.RunPython.noop,
        ),
    ]