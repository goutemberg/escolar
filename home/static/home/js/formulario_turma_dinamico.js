document.addEventListener('DOMContentLoaded', function () {

  const inputBusca = document.getElementById('buscaPessoa');
  const tipoPessoa = document.getElementById('tipoPessoa');
  const disciplinaSelect = document.getElementById('disciplinaSelecionada');
  const campoTags = document.getElementById('turmaMontadaTags');
  const form = document.getElementById('turmaForm');

  // ✅ pega o select uma vez
  const sistemaSelect = document.getElementById('sistemaAvaliacao');

  // ===============================
  // MODELO DA TURMA
  // ===============================
  const turma = {
    id: null,
    professores: [], // [{ professor_id, nome, disciplina_id, disciplina_nome }]
    alunos: []       // [{ id, nome }]
  };

  // ===============================
  // HELPERS (ordem, normalização, bloqueio)
  // ===============================
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

  // ✅ REGRA CERTA:
  // bloqueia SOMENTE professor + disciplina repetidos
  // permite mesmo professor em disciplinas diferentes
  function professorJaNaDisciplina(professorId, disciplinaId) {
    return turma.professores.some(p =>
      String(p.professor_id) === String(professorId) &&
      String(p.disciplina_id) === String(disciplinaId)
    );
  }

  function getDisciplinaIdSelecionada() {
    return disciplinaSelect ? (disciplinaSelect.value || "") : "";
  }

  // ===============================
  // DETECTAR EDIÇÃO (?turma_id=)
  // ===============================
  const params = new URLSearchParams(window.location.search);
  const turmaId = params.get('turma_id');

  if (turmaId) {
    turma.id = turmaId;

    const botaoSalvar = document.querySelector('#turmaForm button[type="submit"]');
    if (botaoSalvar) botaoSalvar.textContent = 'Salvar Edição';

    carregarTurma(turmaId);
  }

  // ===============================
  // DISCIPLINA ATIVA SOMENTE PARA PROFESSOR
  // ===============================
  if (tipoPessoa) {
    tipoPessoa.addEventListener('change', atualizarCampoDisciplina);
    atualizarCampoDisciplina();
  }

  function atualizarCampoDisciplina() {
    const tipo = tipoPessoa.value;
    if (!disciplinaSelect) return;

    disciplinaSelect.disabled = tipo !== 'professor';
    if (tipo !== 'professor') disciplinaSelect.value = '';

    // ✅ se mudar professor/aluno, atualiza sugestões (evita confusão)
    renderSugestoesAtuais();
  }

  // ✅ se mudar a disciplina, precisa re-renderizar sugestões
  // para aplicar corretamente o "já vinculado nessa disciplina"
  if (disciplinaSelect) {
    disciplinaSelect.addEventListener("change", renderSugestoesAtuais);
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

        // ✅ sistema de avaliação (se existir no retorno)
        if (sistemaSelect && data.sistema_avaliacao) {
          sistemaSelect.value = data.sistema_avaliacao;
        }

        // ✅ ordena alfabeticamente ao carregar
        turma.alunos = sortPorNome(data.alunos || []);

        turma.professores = sortPorNome((data.professores || []).map(p => ({
          professor_id: p.professor_id,
          nome: p.nome,
          disciplina_id: p.disciplina_id,
          disciplina_nome: p.disciplina_nome
        })));

        atualizarTags();
        renderSugestoesAtuais(); // garante que já adicionados fiquem desabilitados
      })
      .catch(() => alert("Erro ao carregar dados da turma."));
  }

  // ===============================
  // ADICIONAR PESSOA
  // ===============================
  window.adicionarPessoa = function () {
    const nome = (inputBusca.value || "").trim();
    const tipo = tipoPessoa.value;

    const sugestoes = document.getElementById('sugestoes');
    const lista = sugestoes?.dataset.lista ? JSON.parse(sugestoes.dataset.lista) : [];

    const pessoa = lista.find(p => (p?.nome || "").trim() === nome);

    if (!pessoa) {
      alert("Selecione um nome da lista.");
      return;
    }

    // ✅ bloqueia aluno repetido
    if (tipo === 'aluno' && alunoJaNaTurma(pessoa.id)) {
      alert("Este aluno já está na turma.");
      return;
    }

    if (tipo === 'professor') {
      const disciplinaId = getDisciplinaIdSelecionada();
      const disciplinaNome = disciplinaSelect?.options?.[disciplinaSelect.selectedIndex]?.text;

      if (!disciplinaId) {
        alert("Selecione uma disciplina.");
        return;
      }

      // ✅ BLOQUEIA SÓ SE FOR A MESMA DISCIPLINA
      if (professorJaNaDisciplina(pessoa.id, disciplinaId)) {
        alert("Este professor já está vinculado a essa disciplina.");
        return;
      }

      // ✅ PERMITE MESMO PROFESSOR EM OUTRA DISCIPLINA
      turma.professores.push({
        professor_id: pessoa.id,
        nome: pessoa.nome,
        disciplina_id: disciplinaId,
        disciplina_nome: disciplinaNome
      });

      turma.professores = sortPorNome(turma.professores);

    } else {
      turma.alunos.push({ id: pessoa.id, nome: pessoa.nome });
      turma.alunos = sortPorNome(turma.alunos);
    }

    inputBusca.value = '';
    limparSugestoes();
    atualizarTags();
    renderSugestoesAtuais();
  };

  // ===============================
  // TAGS VISUAIS
  // ===============================
  function atualizarTags() {
    campoTags.innerHTML = '';

    const profs = sortPorNome(turma.professores);
    const alunos = sortPorNome(turma.alunos);

    profs.forEach((p) => {
      const tag = criarTag(
        `👨‍🏫 ${p.nome} – ${p.disciplina_nome}`,
        () => {
          // remove pelo par professor+disciplina
          turma.professores = turma.professores.filter(x =>
            !(
              String(x.professor_id) === String(p.professor_id) &&
              String(x.disciplina_id) === String(p.disciplina_id)
            )
          );
          atualizarTags();
          renderSugestoesAtuais();
        }
      );
      campoTags.appendChild(tag);
    });

    alunos.forEach((a) => {
      const tag = criarTag(
        `👦 ${a.nome}`,
        () => {
          turma.alunos = turma.alunos.filter(x => String(x.id) !== String(a.id));
          atualizarTags();
          renderSugestoesAtuais();
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
  let lastLista = [];

  inputBusca.addEventListener('input', function () {
    const nome = this.value.trim();
    const tipo = tipoPessoa.value;

    if (nome.length < 2) {
      limparSugestoes();
      lastLista = [];
      return;
    }

    fetch(`/autocomplete_pessoa/?nome=${encodeURIComponent(nome)}&tipo=${tipo}`)
      .then(res => res.json())
      .then(data => {
        let lista = Array.isArray(data) ? data : (data.resultados || []);
        lista = sortPorNome(lista);
        lastLista = lista;
        mostrarSugestoes(lista);
      })
      .catch(() => {
        limparSugestoes();
        lastLista = [];
      });
  });

  // re-renderiza para aplicar disable quando muda disciplina/tipo etc.
  function renderSugestoesAtuais() {
    const ul = document.getElementById('sugestoes');
    if (!ul || !ul.children || ul.children.length === 0) return;
    if (!lastLista || lastLista.length === 0) return;
    mostrarSugestoes(lastLista);
  }

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

    const tipo = tipoPessoa.value;
    const disciplinaIdAtual = getDisciplinaIdSelecionada();

    lista.forEach(p => {
      const li = document.createElement('li');

      li.style.cssText = `
        padding:10px 12px;
        cursor:pointer;
        display:block;
        width:100%;
        user-select:none;
      `;
      li.textContent = p.nome;

      let disabled = false;

      if (tipo === "aluno") {
        disabled = alunoJaNaTurma(p.id);
      } else {
        // ✅ professor só fica "bloqueado" se já estiver NESSA disciplina
        // e só quando disciplina estiver selecionada
        if (disciplinaIdAtual && professorJaNaDisciplina(p.id, disciplinaIdAtual)) {
          disabled = true;
        }
      }

      if (disabled) {
        li.style.cursor = "not-allowed";
        li.style.opacity = "0.45";
        li.style.pointerEvents = "none";
        li.title = "Já adicionado na turma";
      } else {
        li.addEventListener("mousedown", function (ev) {
          ev.preventDefault();
          inputBusca.value = p.nome;
          ul.innerHTML = '';
        });
      }

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

    if (!sistemaSelect) {
      console.warn("Select #sistemaAvaliacao não encontrado. Enviando NUM por padrão.");
    }

    const sistemaSelectAtual = document.getElementById("sistemaAvaliacao");
    let sistemaVal = sistemaSelectAtual ? sistemaSelectAtual.value : "NUM";

    sistemaVal = sistemaVal.toString().trim().toUpperCase();

    if (!["NUM", "CON"].includes(sistemaVal)) {
      sistemaVal = "NUM";
    }

    const payload = {
      turma_id: turma.id,
      nome: document.getElementById('nomeTurmaSelect').value.trim(),
      turno: document.getElementById('turnoTurma').value.trim(),
      ano: document.getElementById('anoTurma').value.trim(),
      sala: document.getElementById('salaTurma').value.trim(),
      descricao: document.getElementById('descricaoTurma').value.trim(),
      sistema_avaliacao: sistemaVal,
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
      if (turma.id) {
        window.location.href = `/turmas/${turma.id}/`;
      } else {
        window.location.href = `/turmas/listar/`;
      }
    });
  }

});