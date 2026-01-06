document.addEventListener('DOMContentLoaded', function () {
    const inputBusca = document.getElementById('buscaPessoa');
    const tipoPessoa = document.getElementById('tipoPessoa');
    const disciplinaSelect = document.getElementById('disciplinaSelecionada');
    const campoTags = document.getElementById('turmaMontadaTags');

    // ===============================
    // MODELO CORRETO DA TURMA
    // ===============================
    const turma = {
        professores: [], // [{ professor_id, nome, disciplina_id, disciplina_nome }]
        alunos: []
    };

    tipoPessoa.addEventListener('change', atualizarCampoDisciplina);

    function atualizarCampoDisciplina() {
        const tipo = tipoPessoa.value;
        disciplinaSelect.disabled = tipo !== 'professor';
        if (tipo !== 'professor') disciplinaSelect.value = '';
    }

    // ===============================
    // ADICIONAR PESSOA
    // ===============================
    window.adicionarPessoa = function () {
        const nome = inputBusca.value.trim();
        const tipo = tipoPessoa.value;
        const sugestoes = document.getElementById('sugestoes');
        const lista = sugestoes?.dataset.lista ? JSON.parse(sugestoes.dataset.lista) : [];

        const pessoa = lista.find(p => p.nome === nome);

        if (!pessoa) {
            alert("Selecione um nome da lista.");
            return;
        }

        // -------------------------------
        // PROFESSOR + DISCIPLINA
        // -------------------------------
        if (tipo === 'professor') {
            const disciplinaId = disciplinaSelect.value;
            const disciplinaNome = disciplinaSelect.options[disciplinaSelect.selectedIndex]?.text;

            if (!disciplinaId) {
                alert("Selecione uma disciplina.");
                return;
            }

            const jaExiste = turma.professores.some(
                p => p.professor_id === pessoa.id && p.disciplina_id === disciplinaId
            );

            if (jaExiste) {
                alert("Este professor já está vinculado a essa disciplina.");
                return;
            }

            turma.professores.push({
                professor_id: pessoa.id,
                nome: pessoa.nome,
                disciplina_id: disciplinaId,
                disciplina_nome: disciplinaNome
            });

        // -------------------------------
        // ALUNO
        // -------------------------------
        } else {
            if (!turma.alunos.some(a => a.id === pessoa.id)) {
                turma.alunos.push({ id: pessoa.id, nome: pessoa.nome });
            }
        }

        inputBusca.value = '';
        limparSugestoes();
        atualizarTags();
    };

    // ===============================
    // ATUALIZAR TAGS VISUAIS
    // ===============================
    function atualizarTags() {
        campoTags.innerHTML = '';

        // hidden de alunos
        document.getElementById('alunos_ids').value =
            turma.alunos.map(a => a.id).join(',');

        // ---------- PROFESSORES ----------
        turma.professores.forEach((p, index) => {
            const tag = criarTag(
                `👨‍🏫 ${p.nome} – ${p.disciplina_nome}`,
                () => {
                    turma.professores.splice(index, 1);
                    atualizarTags();
                }
            );
            campoTags.appendChild(tag);
        });

        // ---------- ALUNOS ----------
        turma.alunos.forEach((aluno, index) => {
            const tag = criarTag(
                `👦 ${aluno.nome}`,
                () => {
                    turma.alunos.splice(index, 1);
                    atualizarTags();
                }
            );
            campoTags.appendChild(tag);
        });
    }

    function criarTag(texto, onRemove) {
        const div = document.createElement('div');
        div.className = 'tag-item';
        div.innerHTML = `${texto} <button type="button">×</button>`;
        div.querySelector('button').addEventListener('click', onRemove);
        return div;
    }

    // ===============================
    // AUTOCOMPLETE
    // ===============================
    inputBusca.addEventListener('input', function () {
        const nome = this.value.trim();
        const tipo = tipoPessoa.value;

        if (nome.length < 2) {
            limparSugestoes();
            return;
        }

        fetch(`/autocomplete_pessoa/?nome=${encodeURIComponent(nome)}&tipo=${tipo}`)
            .then(res => res.json())
            .then(data => {
                const lista = Array.isArray(data) ? data : (data.resultados || []);
                mostrarSugestoes(lista);
            })
            .catch(() => limparSugestoes());
    });

    function mostrarSugestoes(lista) {
        let ul = document.getElementById('sugestoes');
        if (!ul) {
            ul = document.createElement('ul');
            ul.id = 'sugestoes';
            ul.style = `
                position:absolute;
                z-index:1000;
                background:white;
                border:1px solid #ccc;
                list-style:none;
                padding:0;
                margin:0;
                width:100%;
                max-height:200px;
                overflow-y:auto;
            `;
            inputBusca.parentNode.appendChild(ul);
        }

        ul.innerHTML = '';
        ul.dataset.lista = JSON.stringify(lista);

        lista.forEach(p => {
            const li = document.createElement('li');
            li.textContent = p.nome;
            li.style = 'padding:8px;cursor:pointer';
            li.addEventListener('click', () => {
                inputBusca.value = p.nome;
                ul.innerHTML = '';
            });
            ul.appendChild(li);
        });
    }

    function limparSugestoes() {
        const ul = document.getElementById('sugestoes');
        if (ul) ul.innerHTML = '';
    }

    // ===============================
    // SUBMIT
    // ===============================
    document.getElementById('turmaForm').addEventListener('submit', function (e) {
        e.preventDefault();

        const nome = document.getElementById('nomeTurmaSelect').value.trim();
        const turno = document.getElementById('turnoTurma').value.trim();
        const ano = document.getElementById('anoTurma').value.trim();
        const sala = document.getElementById('salaTurma').value.trim();
        const descricao = document.getElementById('descricaoTurma').value.trim();

        if (!nome || !turno || !ano || !sala) {
            alert("Preencha os campos obrigatórios da turma.");
            return;
        }

        fetch('/turmas/cadastrar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                nome,
                turno,
                ano,
                sala,
                descricao,
                professores: turma.professores,
                alunos_ids: turma.alunos.map(a => a.id)
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.mensagem || "Turma criada com sucesso!");
                window.location.reload();
            } else {
                alert("Erro: " + (data.mensagem || data.error));
            }
        })
        .catch(() => alert("Erro ao salvar turma."));
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie) {
            const cookies = document.cookie.split(';');
            for (let c of cookies) {
                const cookie = c.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
