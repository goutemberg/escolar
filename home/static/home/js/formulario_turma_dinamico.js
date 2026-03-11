document.addEventListener('DOMContentLoaded', function () {

  const inputBusca = document.getElementById('buscaPessoa');
  const tipoPessoa = document.getElementById('tipoPessoa');
  const disciplinaSelect = document.getElementById('disciplinaSelecionada');
  const campoTags = document.getElementById('turmaMontadaTags');
  const form = document.getElementById('turmaForm');
  const sistemaSelect = document.getElementById('sistemaAvaliacao');

  let lastLista = [];

  const turma = {
    id: null,
    professores: [],
    alunos: []
  };

  function normalizaNome(s) {
    return (s || "")
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function sortPorNome(lista) {
    return (lista || []).slice().sort((a, b) => {
      const an = normalizaNome(a?.nome);
      const bn = normalizaNome(b?.nome);
      return an.localeCompare(bn, "pt-BR");
    });
  }

  function alunoJaNaTurma(id) {
    return turma.alunos.some(a => String(a.id) === String(id));
  }

  function professorJaNaDisciplina(professorId, disciplinaId) {
    return turma.professores.some(p =>
      String(p.professor_id) === String(professorId) &&
      String(p.disciplina_id) === String(disciplinaId)
    );
  }

  function getDisciplinaIdSelecionada() {
    return disciplinaSelect ? (disciplinaSelect.value || "") : "";
  }

  function renderSugestoesAtuais() {
    if (!lastLista.length) return;
    mostrarSugestoes(lastLista);
  }

  const params = new URLSearchParams(window.location.search);
  const turmaId = params.get('turma_id');

  if (turmaId) {
    turma.id = turmaId;

    const botaoSalvar = document.querySelector('#turmaForm button[type="submit"]');
    if (botaoSalvar) botaoSalvar.textContent = 'Salvar Edição';

    carregarTurma(turmaId);
  }

  if (tipoPessoa) {
    tipoPessoa.addEventListener('change', atualizarCampoDisciplina);
    atualizarCampoDisciplina();
  }

  function atualizarCampoDisciplina() {
    const tipo = tipoPessoa.value;

    if (!disciplinaSelect) return;

    disciplinaSelect.disabled = tipo !== 'professor';

    if (tipo !== 'professor') {
      disciplinaSelect.value = '';
    }

    renderSugestoesAtuais();
  }

  window.atualizarCampoDisciplina = atualizarCampoDisciplina;

  if (disciplinaSelect) {
    disciplinaSelect.addEventListener("change", renderSugestoesAtuais);
  }

  function carregarTurma(id) {
    fetch(`/turmas/api/turmas/${id}/`)
      .then(res => res.json())
      .then(data => {

        document.getElementById('nomeTurmaSelect').value = data.nome;
        document.getElementById('turnoTurma').value = data.turno;
        document.getElementById('anoTurma').value = data.ano;
        document.getElementById('salaTurma').value = data.sala;
        document.getElementById('descricaoTurma').value = data.descricao || '';

        if (sistemaSelect && data.sistema_avaliacao) {
          sistemaSelect.value = data.sistema_avaliacao;
        }

        turma.alunos = sortPorNome(data.alunos || []);

        turma.professores = sortPorNome((data.professores || []).map(p => ({
          professor_id: p.professor_id,
          nome: p.nome,
          disciplina_id: p.disciplina_id,
          disciplina_nome: p.disciplina_nome
        })));

        atualizarTags();
      })
      .catch(() => alert("Erro ao carregar dados da turma."));
  }

  window.adicionarPessoa = function () {

    const sugestoes = document.getElementById('sugestoes');
    const lista = sugestoes?.dataset.lista ? JSON.parse(sugestoes.dataset.lista) : [];

    const idSelecionado = sugestoes.dataset.selecionado;

    const pessoa = lista.find(p => String(p.id) === String(idSelecionado));

    if (!pessoa) {
      alert("Selecione um nome da lista.");
      return;
    }

    const tipo = tipoPessoa.value;

    if (tipo === 'aluno') {

      if (alunoJaNaTurma(pessoa.id)) {
        alert("Este aluno já está na turma.");
        return;
      }

      turma.alunos.push({
        id: pessoa.id,
        nome: pessoa.nome
      });

      turma.alunos = sortPorNome(turma.alunos);

    } else {

      const disciplinaId = getDisciplinaIdSelecionada();
      const disciplinaNome = disciplinaSelect.options[disciplinaSelect.selectedIndex].text;

      if (!disciplinaId) {
        alert("Selecione uma disciplina.");
        return;
      }

      if (professorJaNaDisciplina(pessoa.id, disciplinaId)) {
        alert("Este professor já está vinculado a essa disciplina.");
        return;
      }

      turma.professores.push({
        professor_id: pessoa.id,
        nome: pessoa.nome,
        disciplina_id: disciplinaId,
        disciplina_nome: disciplinaNome
      });

      turma.professores = sortPorNome(turma.professores);
    }

    inputBusca.value = '';
    limparSugestoes();
    atualizarTags();
  };

  function atualizarTags() {

    campoTags.innerHTML = '';

    turma.professores.forEach(p => {

      const tag = criarTag(
        `👨‍🏫 ${p.nome} – ${p.disciplina_nome}`,
        () => {

          turma.professores = turma.professores.filter(x =>
            !(String(x.professor_id) === String(p.professor_id) &&
              String(x.disciplina_id) === String(p.disciplina_id))
          );

          atualizarTags();
        }
      );

      campoTags.appendChild(tag);
    });

    turma.alunos.forEach(a => {

      const tag = criarTag(
        `👦 ${a.nome}`,
        () => {

          turma.alunos = turma.alunos.filter(x => String(x.id) !== String(a.id));

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

  inputBusca.addEventListener("keyup", function () {

    const nome = this.value.trim();
    const tipo = tipoPessoa.value;

    if (nome.length < 2) {
      limparSugestoes();
      lastLista = [];
      return;
    }

    fetch(`/autocomplete_pessoa/?nome=${encodeURIComponent(nome)}&tipo=${tipo}`)
      .then(res => res.json())
      .then(lista => {

        if (!Array.isArray(lista)) lista = [];

        lista = sortPorNome(lista);

        lastLista = lista;

        mostrarSugestoes(lista);
      })
      .catch(() => {
        limparSugestoes();
        lastLista = [];
      });

  });

  function mostrarSugestoes(lista) {

    const ul = document.getElementById('sugestoes');

    ul.innerHTML = '';
    ul.dataset.lista = JSON.stringify(lista);

    lista.forEach(p => {

      const li = document.createElement('li');

      li.textContent = p.nome;

      li.addEventListener("mousedown", function (ev) {

        ev.preventDefault();

        inputBusca.value = p.nome;

        ul.dataset.selecionado = p.id;

        ul.innerHTML = '';
      });

      ul.appendChild(li);
    });
  }

  function limparSugestoes() {
    const ul = document.getElementById('sugestoes');
    if (ul) ul.innerHTML = '';
  }

});