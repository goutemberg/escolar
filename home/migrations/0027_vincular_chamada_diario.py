from django.db import migrations, connection


def vincular_chamadas_a_diarios(apps, schema_editor):
    Chamada = apps.get_model("home", "Chamada")
    DiarioDeClasse = apps.get_model("home", "DiarioDeClasse")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, data, turma_id, disciplina_id, professor_id
            FROM home_chamada
            WHERE diario_id IS NULL
        """)
        chamadas = cursor.fetchall()

    for chamada_id, data, turma_id, disciplina_id, professor_id in chamadas:

        diario_qs = DiarioDeClasse.objects.filter(
            data_ministrada=data,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
        ).order_by("hora_inicio")

        diario = diario_qs.first()

        if not diario:
            diario = DiarioDeClasse.objects.create(
                data_ministrada=data,
                turma_id=turma_id,
                disciplina_id=disciplina_id,
                professor_id=professor_id,
                escola_id=DiarioDeClasse.objects.model._meta.get_field("escola").remote_field.model.objects.filter(turma_id=turma_id).values_list("escola_id", flat=True).first(),
                status="REALIZADA",
                resumo_conteudo="Diário gerado automaticamente (migração)",
            )

        Chamada.objects.filter(id=chamada_id).update(diario=diario)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_remove_nota_from_state"),
    ]

    operations = [
        migrations.RunPython(
            vincular_chamadas_a_diarios,
            reverse_code=migrations.RunPython.noop,
        ),
    ]