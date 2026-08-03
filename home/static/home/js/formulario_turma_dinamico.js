document.addEventListener("DOMContentLoaded", () => {

  // ============================
  // Elementos do DOM
  // ============================

  const inputBusca = document.getElementById("buscaPessoa");
  const tipoPessoa = document.getElementById("tipoPessoa");
  const disciplinaSelect = document.getElementById("disciplinaSelecionada");
  const campoTags = document.getElementById("turmaMontadaTags");
  const form = document.getElementById("turmaForm");

  console.log("FORM:", form);

  const sistemaSelect = document.getElementById("sistemaAvaliacao");

  const nomeTurmaSelect = document.getElementById("nomeTurmaSelect");
  const turnoTurma = document.getElementById("turnoTurma");
  const anoTurma = document.getElementById("anoTurma");
  const salaTurma = document.getElementById("salaTurma");
  const descricaoTurma = document.getElementById("descricaoTurma");

  const botaoSalvar = document.querySelector('#turmaForm button[type="submit"]');

  // ============================
  // Estado
  // ============================

  let lastLista = [];

  const turma = {
    id: null,
    professores: [],
    alunos: []
  };

  // ============================
  // Helpers
  // ============================

  function normalizaNome(valor) {
    return (valor || "")
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function sortPorNome(lista = []) {
    return [...lista].sort((a, b) =>
      normalizaNome(a?.nome).localeCompare(
        normalizaNome(b?.nome),
        "pt-BR"
      )
    );
  }

  function alunoJaNaTurma(id) {
    return turma.alunos.some(
      aluno => String(aluno.id) === String(id)
    );
  }

  function professorJaNaDisciplina(professorId, disciplinaId) {
    return turma.professores.some(professor =>
      String(professor.professor_id) === String(professorId) &&
      String(professor.disciplina_id) === String(disciplinaId)
    );
  }

  function getDisciplinaIdSelecionada() {
    return disciplinaSelect?.value || "";
  }

  function renderSugestoesAtuais() {
    if (!lastLista.length) return;
    mostrarSugestoes(lastLista);
  }

  // ============================
  // Inicialização
  // ============================

  const params = new URLSearchParams(window.location.search);
  const turmaId = params.get("turma_id");

  if (turmaId) {
    turma.id = turmaId;

    if (botaoSalvar) {
      botaoSalvar.textContent = "Salvar Edição";
    }

    carregarTurma(turmaId);
  }

  if (tipoPessoa) {
    tipoPessoa.addEventListener("change", atualizarCampoDisciplina);
    atualizarCampoDisciplina();
  }

  if (disciplinaSelect) {
    disciplinaSelect.addEventListener(
      "change",
      renderSugestoesAtuais
    );
  }

  // ============================
  // Eventos
  // ============================

  function atualizarCampoDisciplina() {

    if (!disciplinaSelect) return;

    const ehProfessor = tipoPessoa.value === "professor";

    disciplinaSelect.disabled = !ehProfessor;

    if (!ehProfessor) {
      disciplinaSelect.value = "";
    }

    renderSugestoesAtuais();
  }

  // Mantido por compatibilidade com HTML existente
  window.atualizarCampoDisciplina = atualizarCampoDisciplina;

  // ============================
  // Carregamento
  // ============================

  async function carregarTurma(id) {

    try {

      const response = await fetch(`/turmas/api/turmas/${id}/`);

      if (!response.ok) {
        throw new Error("Erro ao carregar turma.");
      }

      const data = await response.json();

      preencherFormulario(data);

    } catch (error) {

      console.error(error);

      alert("Erro ao carregar dados da turma.");

    }
  }

  function preencherFormulario(data) {

    nomeTurmaSelect.value = data.nome;
    turnoTurma.value = data.turno;
    anoTurma.value = data.ano;
    salaTurma.value = data.sala;
    descricaoTurma.value = data.descricao || "";

    if (sistemaSelect && data.sistema_avaliacao) {
      sistemaSelect.value = data.sistema_avaliacao;
    }

    turma.alunos = sortPorNome(data.alunos || []);

    turma.professores = sortPorNome(
      (data.professores || []).map(professor => ({
        professor_id: professor.professor_id,
        nome: professor.nome,
        disciplina_id: professor.disciplina_id,
        disciplina_nome: professor.disciplina_nome
      }))
    );

    const selectCoordenadores = document.getElementById("coordenadoresSelect");

    if (selectCoordenadores) {
      Array.from(selectCoordenadores.options).forEach(option => {
        option.selected = (data.coordenadores || []).some(
          coordenador => String(coordenador.id) === option.value
        );
      });
    }

    atualizarTags();
  }

  // Mantido por compatibilidade com o HTML atual
  window.adicionarPessoa = function () {

    const sugestoes = document.getElementById("sugestoes");
    const lista = sugestoes?.dataset.lista
      ? JSON.parse(sugestoes.dataset.lista)
      : [];

    const pessoa = lista.find(
      p => String(p.id) === String(sugestoes.dataset.selecionado)
    );

    if (!pessoa) {
      alert("Selecione um nome da lista.");
      return;
    }

    if (tipoPessoa.value === "aluno") {

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
        disciplina_nome:
          disciplinaSelect.options[
            disciplinaSelect.selectedIndex
          ].text
      });

      turma.professores = sortPorNome(turma.professores);
    }

    inputBusca.value = "";

    limparSugestoes();

    atualizarTags();
  };

  function atualizarTags() {

    campoTags.innerHTML = "";

    turma.professores.forEach(professor => {

      campoTags.appendChild(
        criarTag(
          `👨‍🏫 ${professor.nome} – ${professor.disciplina_nome}`,
          () => {

            turma.professores = turma.professores.filter(item =>
              !(
                String(item.professor_id) === String(professor.professor_id) &&
                String(item.disciplina_id) === String(professor.disciplina_id)
              )
            );

            atualizarTags();

          }
        )
      );

    });

    turma.alunos.forEach(aluno => {

      campoTags.appendChild(
        criarTag(
          `👦 ${aluno.nome}`,
          () => {

            turma.alunos = turma.alunos.filter(
              item => String(item.id) !== String(aluno.id)
            );

            atualizarTags();

          }
        )
      );

    });

  }

  function criarTag(texto, onRemove) {

    const tag = document.createElement("div");

    tag.className = "tag-item";

    tag.innerHTML = `
    ${texto}
    <button type="button">×</button>
  `;

    tag.querySelector("button")
      .addEventListener("click", onRemove);

    return tag;

  }

  inputBusca.addEventListener("keyup", buscarPessoas);

  async function buscarPessoas() {

    const nome = inputBusca.value.trim();

    if (nome.length < 2) {

      limparSugestoes();

      lastLista = [];

      return;

    }

    try {

      const response = await fetch(
        `/autocomplete_pessoa/?nome=${encodeURIComponent(nome)}&tipo=${tipoPessoa.value}`
      );

      let lista = await response.json();

      if (!Array.isArray(lista)) {
        lista = [];
      }

      lastLista = sortPorNome(lista);

      mostrarSugestoes(lastLista);

    } catch (error) {

      console.error(error);

      limparSugestoes();

      lastLista = [];

    }

  }

  function mostrarSugestoes(lista) {

    const sugestoes = document.getElementById("sugestoes");

    sugestoes.innerHTML = "";

    sugestoes.dataset.lista = JSON.stringify(lista);

    lista.forEach(pessoa => {

      const li = document.createElement("li");

      li.textContent = pessoa.nome;

      li.addEventListener("mousedown", event => {

        event.preventDefault();

        inputBusca.value = pessoa.nome;

        sugestoes.dataset.selecionado = pessoa.id;

        sugestoes.innerHTML = "";

      });

      sugestoes.appendChild(li);

    });

  }

  function limparSugestoes() {

    const sugestoes = document.getElementById("sugestoes");

    if (sugestoes) {
      sugestoes.innerHTML = "";
    }

  }

  console.log("Entrou no if?", !!form);

  if (form) {

    form.addEventListener("submit", async function (e) {

      console.log("ENTREI NO SUBMIT");

      e.preventDefault();

      const payload = {

        turma_id: turma.id,

        nome: nomeTurmaSelect.value,
        turno: turnoTurma.value,
        ano: anoTurma.value,
        sala: salaTurma.value,
        descricao: descricaoTurma.value,

        tipo_turma: document.getElementById("tipoTurma").value,
        sistema_avaliacao: sistemaSelect.value,
        polivalente: document.getElementById("chamadaPolivalente").value,

        alunos_ids: turma.alunos.map(a => a.id),

        professores: turma.professores.map(p => ({
          professor_id: p.professor_id,
          disciplina_id: p.disciplina_id
        })),

        coordenadores_ids: Array.from(
          document.getElementById("coordenadoresSelect").selectedOptions
        ).map(option => option.value)

      };

      const url = turma.id
        ? `/turmas/${turma.id}/editar/`
        : "/turmas/cadastrar/";

      try {

        if (botaoSalvar) {
          botaoSalvar.disabled = true;
        }

        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
          },
          body: JSON.stringify(payload)
        });

        const resp = await response.json();

        if (resp.success) {

          alert("Turma salva com sucesso!");

          window.location.href = window.URL_LISTAR_TURMAS;
        } else {

          alert(resp.error || "Erro ao salvar turma.");

        }

      } catch (error) {

        console.error(error);

        alert("Erro ao salvar turma.");

      } finally {

        if (botaoSalvar) {
          botaoSalvar.disabled = false;
        }

      }

    });

  }

});