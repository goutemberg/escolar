(() => {
  "use strict";

  /* ===============================
     CONFIG
  =============================== */
  const URL_SALVAR = "/registro-pedagogico/salvar/";
  const URL_ALUNOS_POR_TURMA = "/api/alunos-por-turma/";
  const URL_BUSCAR_REGISTROS = "/api/registro-pedagogico/";

  const btnSalvar = document.getElementById("btnSalvar");
  const selectTurma = document.getElementById("turma");
  const selectAluno = document.getElementById("aluno");
  const inputAno = document.getElementById("ano_letivo");

  const trimestres = {
    1: document.getElementById("trimestre_1"),
    2: document.getElementById("trimestre_2"),
    3: document.getElementById("trimestre_3"),
    4: document.getElementById("trimestre_4"),
  };

  let isSaving = false;

  /* ===============================
     HELPERS
  =============================== */

  function getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  function showAlert(msg) {
    alert(msg);
  }

  function resetTrimestres() {
    Object.values(trimestres).forEach((textarea) => {
      textarea.value = "";
      textarea.disabled = true;
    });
  }

  function enableTrimestres() {
    Object.values(trimestres).forEach((textarea) => {
      textarea.disabled = false;
    });
  }

  function validarContexto() {
    if (!selectTurma.value) {
      showAlert("Selecione uma turma.");
      return false;
    }

    if (!selectAluno.value) {
      showAlert("Selecione um aluno.");
      return false;
    }

    const ano = parseInt(inputAno.value, 10);
    if (!ano || ano < 2000 || ano > 2100) {
      showAlert("Ano letivo inválido.");
      return false;
    }

    return true;
  }

  /* ===============================
     BUSCAR ALUNOS POR TURMA
  =============================== */

  async function carregarAlunos(turmaId) {
    resetTrimestres();
    selectAluno.innerHTML = `<option value="">Carregando alunos...</option>`;

    try {
      const response = await fetch(`${URL_ALUNOS_POR_TURMA}?turma=${turmaId}`, {
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error("Falha ao buscar alunos");
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error("Resposta inválida");
      }

      selectAluno.innerHTML = `<option value="">Selecione o aluno</option>`;

      data.forEach((aluno) => {
        const opt = document.createElement("option");
        opt.value = aluno.id;
        opt.textContent = aluno.nome;
        selectAluno.appendChild(opt);
      });

    } catch (err) {
      console.error(err);
      selectAluno.innerHTML = `<option value="">Erro ao carregar alunos</option>`;
      showAlert("Erro ao carregar alunos da turma.");
    }
  }

  /* ===============================
     CARREGAR REGISTROS SALVOS
  =============================== */

  async function carregarRegistros() {
    if (!selectTurma.value || !selectAluno.value || !inputAno.value) {
      return;
    }

    try {
      const params = new URLSearchParams({
        turma: selectTurma.value,
        aluno: selectAluno.value,
        ano_letivo: inputAno.value,
      });

      const response = await fetch(
        `${URL_BUSCAR_REGISTROS}?${params.toString()}`,
        { credentials: "same-origin" }
      );

      if (!response.ok) {
        throw new Error("Erro ao buscar registros");
      }

      const data = await response.json();

      [1, 2, 3, 4].forEach((t) => {
        trimestres[t].value = data[t] || "";
      });

    } catch (err) {
      console.error(err);
      showAlert("Erro ao carregar registros pedagógicos.");
    }
  }

  /* ===============================
     SALVAR REGISTRO
  =============================== */

  async function salvarRegistroPedagogico() {
    if (isSaving) return;
    if (!validarContexto()) return;

    isSaving = true;
    btnSalvar.disabled = true;
    btnSalvar.textContent = "Salvando...";

    const payload = {
      turma: selectTurma.value,
      aluno: selectAluno.value,
      ano_letivo: parseInt(inputAno.value, 10),
      registros: {},
    };

    Object.keys(trimestres).forEach((tri) => {
      payload.registros[tri] = trimestres[tri].value.trim();
    });

    try {
      const response = await fetch(URL_SALVAR, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok || data.status !== "ok") {
        throw new Error(data.mensagem || "Erro ao salvar");
      }

      showAlert("Registro pedagógico salvo com sucesso.");

    } catch (err) {
      console.error(err);
      showAlert("Erro ao salvar o registro pedagógico.");
    } finally {
      isSaving = false;
      btnSalvar.disabled = false;
      btnSalvar.textContent = "Salvar Registro";
    }
  }

  /* ===============================
     EVENTS
  =============================== */

  selectTurma.addEventListener("change", () => {
    if (!selectTurma.value) {
      selectAluno.innerHTML = `<option value="">Selecione o aluno</option>`;
      resetTrimestres();
      return;
    }
    carregarAlunos(selectTurma.value);
  });

  selectAluno.addEventListener("change", () => {
    if (!selectAluno.value) {
      resetTrimestres();
      return;
    }
    enableTrimestres();
    carregarRegistros();
  });

  inputAno.addEventListener("change", () => {
    if (selectAluno.value) {
      carregarRegistros();
    }
  });

  btnSalvar.addEventListener("click", salvarRegistroPedagogico);

  /* ===============================
     INIT
  =============================== */

  resetTrimestres();
})();
