from django.db import migrations


def vincular_chamadas_a_diarios(apps, schema_editor):
    Chamada = apps.get_model("home", "Chamada")
    DiarioDeClasse = apps.get_model("home", "DiarioDeClasse")

    for chamada in Chamada.objects.filter(diario__isnull=True):

        # Tentativa 1: casar por data + turma + disciplina
        diario_qs = DiarioDeClasse.objects.filter(
            data_ministrada=chamada.data,
            turma=chamada.turma,
            disciplina=chamada.disciplina,
        ).order_by("hora_inicio")

        diario = diario_qs.first()

        # Se não existir, cria um diário novo
        if not diario:
            diario = DiarioDeClasse.objects.create(
                data_ministrada=chamada.data,
                turma=chamada.turma,
                disciplina=chamada.disciplina,
                professor=chamada.professor,
                escola=chamada.turma.escola,
                status="REALIZADA",
                resumo_conteudo="Diário gerado automaticamente (migração)",
            )

        chamada.diario = diario
        chamada.save(update_fields=["diario"])


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_remove_nota_from_state"),
    ]

    operations = [
        migrations.RunPython(vincular_chamadas_a_diarios),
    ]
