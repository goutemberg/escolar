document.addEventListener('DOMContentLoaded', function () {

    const inputBusca = document.getElementById('buscaPessoa');
    const tipoPessoa = document.getElementById('tipoPessoa');
    const disciplinaSelect = document.getElementById('disciplinaSelecionada');
    const campoTags = document.getElementById('turmaMontadaTags');
    const form = document.getElementById('turmaForm');

    // ===============================
    // MODELO DA TURMA
    // ===============================
    const turma = {
        id: null,              // usado na edição
        professores: [],       // [{ professor_id, nome, disciplina_id, disciplina_nome }]
        alunos: []             // [{ id, nome }]
    };

    // ===============================
    // DETECTAR EDIÇÃO (?turma_id=)
    // ===============================
    const params = new URLSearchParams(window.location.search);
    const turmaId = params.get('turma_id');

    if (turmaId) {
        turma.id = turmaId;

        // 🔁 muda texto do botão
        const botaoSalvar = document.querySelector('#turmaForm button[type="submit"]');
        if (botaoSalvar) {
            botaoSalvar.textContent = 'Salvar Edição';
        }

        carregarTurma(turmaId);
    }

    // ===============================
    // DISCIPLINA ATIVA SOMENTE PARA PROFESSOR
    // ===============================
    tipoPessoa.addEventListener('change', atualizarCampoDisciplina);
    atualizarCampoDisciplina();

    function atualizarCampoDisciplina() {
        const tipo = tipoPessoa.value;
        disciplinaSelect.disabled = tipo !== 'professor';
        if (tipo !== 'professor') disciplinaSelect.value = '';
    }

    // ===============================
    // CARREGAR TURMA (EDIÇÃO)
    // ===============================
    function carregarTurma(id) {
        fetch(`/turmas/api/turmas/${id}/`)
            .then(res => res.json())
            .then(data => {

                document.getElementById('nomeTurmaSelect').value = data.nome;
                document.getElementById('turnoTurma').value = data.turno;
                document.getElementById('anoTurma').value = data.ano;
                document.getElementById('salaTurma').value = data.sala;
                document.getElementById('descricaoTurma').value = data.descricao || '';

                turma.alunos = data.alunos || [];
                turma.professores = data.professores || [];

                atualizarTags();
            })
            .catch(() => alert("Erro ao carregar dados da turma."));
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

        // -------- PROFESSOR --------
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

        // -------- ALUNO --------
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
    // TAGS VISUAIS
    // ===============================
    function atualizarTags() {
        campoTags.innerHTML = '';

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

        turma.alunos.forEach((a, index) => {
            const tag = criarTag(
                `👦 ${a.nome}`,
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
            li.onclick = () => {
                inputBusca.value = p.nome;
                ul.innerHTML = '';
            };
            ul.appendChild(li);
        });
    }

    function limparSugestoes() {
        const ul = document.getElementById('sugestoes');
        if (ul) ul.innerHTML = '';
    }

    // ===============================
    // SUBMIT (CREATE / UPDATE)
    // ===============================
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const payload = {
            turma_id: turma.id,
            nome: document.getElementById('nomeTurmaSelect').value.trim(),
            turno: document.getElementById('turnoTurma').value.trim(),
            ano: document.getElementById('anoTurma').value.trim(),
            sala: document.getElementById('salaTurma').value.trim(),
            descricao: document.getElementById('descricaoTurma').value.trim(),
            professores: turma.professores,
            alunos_ids: turma.alunos.map(a => a.id)
        };

        fetch('/turmas/cadastrar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.mensagem);
                window.location.href = `/turmas/${data.turma_id}/`;
            } else {
                alert(data.mensagem || "Erro ao salvar.");
            }
        })
        .catch(() => alert("Erro ao salvar turma."));
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie) {
            document.cookie.split(';').forEach(c => {
                c = c.trim();
                if (c.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(c.slice(name.length + 1));
                }
            });
        }
        return cookieValue;
    }
    // ===============================
// CANCELAR (CREATE / EDIT)
// ===============================
const btnCancelar = document.getElementById('btnCancelar');

if (btnCancelar) {
    btnCancelar.addEventListener('click', function () {

        // edição → volta para detalhe
        if (turma.id) {
            window.location.href = `/turmas/${turma.id}/`;
        }
        // cadastro → volta para listagem
        else {
            window.location.href = `/turmas/listar/`;
        }
    });
}
});
