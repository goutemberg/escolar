from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('home', '0015_nota_bimestre'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='nota',
            unique_together={('aluno', 'disciplina', 'turma', 'bimestre', 'escola')},
        ),
    ]
