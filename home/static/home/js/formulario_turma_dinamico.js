document.addEventListener('DOMContentLoaded', function () {
    const inputBusca = document.getElementById('buscaPessoa');
    const tipoPessoa = document.getElementById('tipoPessoa');
    const disciplinaSelect = document.getElementById('disciplinaSelecionada');
    const campoTags = document.getElementById('turmaMontadaTags');

    const turma = {
        professor: null,
        disciplina_id: null,
        disciplina_nome: '',
        alunos: []
    };

    tipoPessoa.addEventListener('change', atualizarCampoDisciplina);

    function atualizarCampoDisciplina() {
        const tipo = tipoPessoa.value;
        disciplinaSelect.disabled = tipo !== 'professor';
        if (tipo !== 'professor') disciplinaSelect.value = '';
    }

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

        if (tipo === 'professor') {
            const disciplinaId = disciplinaSelect.value;
            const disciplinaNome = disciplinaSelect.options[disciplinaSelect.selectedIndex]?.text;

            if (!disciplinaId) {
                alert("Selecione uma disciplina.");
                return;
            }
            if (turma.professor) {
                alert("Já há um professor atribuído. Remova-o primeiro.");
                return;
            }

            turma.professor = { id: pessoa.id, nome: pessoa.nome };
            turma.disciplina_id = disciplinaId;
            turma.disciplina_nome = disciplinaNome;
            document.getElementById('professor_id').value = pessoa.id;

        } else {
            if (!turma.alunos.some(a => a.id === pessoa.id)) {
                turma.alunos.push({ id: pessoa.id, nome: pessoa.nome });
            }
        }

        inputBusca.value = '';
        limparSugestoes();
        atualizarTags();
    };

    function atualizarTags() {
        campoTags.innerHTML = '';
        document.getElementById('alunos_ids').value = turma.alunos.map(a => a.id).join(',');

        // TAG DO PROFESSOR
        if (turma.professor) {
            const tag = criarTag(`👨‍🏫 ${turma.professor.nome} – ${turma.disciplina_nome}`, () => {
                turma.professor = null;
                turma.disciplina_id = null;
                turma.disciplina_nome = '';
                document.getElementById('professor_id').value = '';
                atualizarTags();
            });
            campoTags.appendChild(tag);
        }

        // TAG DOS ALUNOS
        turma.alunos.forEach(aluno => {
            const tag = criarTag(`👦 ${aluno.nome}`, () => {
                turma.alunos = turma.alunos.filter(a => a.id !== aluno.id);
                atualizarTags();
            });
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

    // ------------------------------
    // 🔥 AUTOCOMPLETE CORRIGIDO
    // ------------------------------
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
                // AQUI ESTÁ A CORREÇÃO ✔
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

    // Submit do formulário
    document.getElementById('turmaForm').addEventListener('submit', function (e) {
        e.preventDefault();

        const nome = document.getElementById('nomeTurmaSelect').value.trim();
        const turno = document.getElementById('turnoTurma').value.trim();
        const ano = document.getElementById('anoTurma').value.trim();
        const sala = document.getElementById('salaTurma').value.trim();
        const descricao = document.getElementById('descricaoTurma').value.trim();
        const professorId = document.getElementById('professor_id').value.trim();
        const disciplinaId = turma.disciplina_id;
        const alunosIds = turma.alunos.map(a => a.id);

        // VALIDAÇÃO COMPLETA
        if (!nome || !turno || !ano || !sala || !professorId || !disciplinaId || alunosIds.length === 0) {
            alert("Preencha todos os campos e adicione professor e alunos.");
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
                professor_id: professorId,
                disciplina_id: disciplinaId,
                alunos_ids: alunosIds
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.mensagem);
                window.location.reload();
            } else {
                alert("Erro: " + data.mensagem);
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
