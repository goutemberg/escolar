from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0037_nota_conceito_turma_sistema_avaliacao"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    -- se já estiver certo, não faz nada
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='home_chamada' AND column_name='feita_por_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='home_chamada' AND column_name='criado_por_id'
                    ) THEN
                        ALTER TABLE home_chamada RENAME COLUMN feita_por_id TO criado_por_id;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='home_chamada' AND column_name='criado_por_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='home_chamada' AND column_name='feita_por_id'
                    ) THEN
                        ALTER TABLE home_chamada RENAME COLUMN criado_por_id TO feita_por_id;
                    END IF;
                END $$;
            """,
        ),
    ]