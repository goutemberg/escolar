document.addEventListener("DOMContentLoaded", function () {


/* ======================================================
   DIÁRIO DE CLASSE
====================================================== */

const tabela = document.getElementById("tabela-diario");
const turmaSelect = document.getElementById("turma_id");

const disciplinaSelect = document.getElementById("disciplina");
disciplinaSelect.disabled = true;
const mesInput = document.getElementById("mes");

const btnNovo = document.getElementById("btnNovoDiario");
const btnImprimirTopo = document.getElementById("btnImprimirTopo");

let registrosCarregados = false;


/* =========================
   MÊS ATUAL AUTOMÁTICO
========================= */

(function definirMesAtual() {
    const hoje = new Date();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const ano = hoje.getFullYear();
    mesInput.value = `${ano}-${mes}`;
})();


/* =========================
   UTILIDADES
========================= */

function getCSRFToken() {
    const cookie = document.cookie
        .split("; ")
        .find(row => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : null;
}

function showError(msg, err = null) {
    console.error("[DIÁRIO ERRO]", msg, err);
    alert(msg);
}

function clearTable() {
    tabela.innerHTML = "";
}

function camposFiltroValidos() {
    return Boolean(
        turmaSelect.value &&
        disciplinaSelect.value &&
        mesInput.value
    );
}

function atualizarEstadoUI() {
    const filtrosOk = camposFiltroValidos();
    btnNovo.disabled = !filtrosOk;

    if (!btnImprimirTopo) return;

    if (!registrosCarregados || tabela.children.length === 0) {
        btnImprimirTopo.classList.add("d-none");
    } else {
        btnImprimirTopo.classList.remove("d-none");
    }
}


/* =========================
   DISCIPLINAS POR TURMA
========================= */

async function carregarDisciplinasPorTurma() {
    const turmaId = turmaSelect.value;

    disciplinaSelect.innerHTML =
        `<option value="">Selecione a disciplina</option>`;
    disciplinaSelect.disabled = true;

    clearTable();
    registrosCarregados = false;
    atualizarEstadoUI();

    if (!turmaId) return;

    try {
        const resp = await fetch(
            `/diario-classe/api/disciplinas_por_turma/${turmaId}/`
        );

        if (!resp.ok) {
            throw new Error(`Erro ${resp.status}`);
        }

        const disciplinas = await resp.json();

        if (!Array.isArray(disciplinas) || disciplinas.length === 0) {
            disciplinaSelect.innerHTML = `
                <option value="">
                    Nenhuma disciplina vinculada à turma
                </option>
            `;
            return;
        }

        disciplinas.forEach(d => {
            const opt = document.createElement("option");
            opt.value = d.id;
            opt.textContent = d.nome;
            disciplinaSelect.appendChild(opt);
        });

        disciplinaSelect.disabled = false;

    } catch (err) {
        showError("Erro ao carregar disciplinas da turma.", err);
    }
}


/* =========================
   TEMPLATE DE LINHA
========================= */

function criarLinha(dados = {}, index = 0) {
    const tr = document.createElement("tr");
    tr.dataset.id = dados.id || "";

    const isSalvo = Boolean(dados.id);

    tr.innerHTML = `
        <td class="text-center">${index + 1}</td>

        <td>
            <div class="mb-1">
                <input type="date"
                       class="form-control form-control-sm data"
                       ${isSalvo ? "disabled" : ""}>
            </div>

            <div class="d-flex gap-1">
                <input type="time"
                       class="form-control form-control-sm inicio"
                       ${isSalvo ? "disabled" : ""}>
                <span class="align-self-center">até</span>
                <input type="time"
                       class="form-control form-control-sm fim"
                       ${isSalvo ? "disabled" : ""}>
            </div>
        </td>

        <td class="text-center">
            <input type="date"
                   class="form-control form-control-sm data-min"
                   ${isSalvo ? "disabled" : ""}>
        </td>

        <td>
            <textarea
                class="form-control form-control-sm conteudo"
                placeholder="Resumo do conteúdo"
                ${isSalvo ? "disabled" : ""}>${dados.resumo_conteudo || ""}</textarea>
        </td>

        <td class="text-center acoes-diario">

            <!-- ✏️ EDITAR (SÓ QUANDO JÁ SALVO) -->
            <i class="bi bi-pencil-square text-warning btn-editar ${isSalvo ? "" : "d-none"}"
               title="Editar"></i>

            <!-- 💾 SALVAR -->
            <i class="bi bi-save text-primary btn-salvar ${isSalvo ? "d-none" : ""}"
               title="Salvar"></i>

            <!-- 🗑 EXCLUIR -->
            <i class="bi bi-trash text-danger btn-excluir ${isSalvo ? "d-none" : ""}"
               title="Excluir"></i>

            <!-- 📋 CHAMADA -->
            <i class="bi bi-check2-square text-success btn-chamada ${isSalvo ? "d-none" : ""}"
               title="Criar chamada"></i>

            <!-- 🔒 STATUS FECHADO -->
            <div class="small mt-1 status-fechado ${isSalvo ? "" : "d-none"}"
                 style="color:#6c757d; display:flex; align-items:center; gap:4px;">
                <i class="bi bi-lock-fill"></i>
                <span>Aula fechada</span>
            </div>

            <!-- ✅ SALVO -->
            <div class="small text-success mt-1 d-none status-salvo">
                ✔ Salvo com sucesso
            </div>
        </td>
    `;

    /* =========================
       DATA E HORÁRIO
    ========================= */

    const hojeISO = new Date().toISOString().split("T")[0];

    setTimeout(() => {
  const agora = new Date();

  const horaInicioAtual = agora.toTimeString().slice(0, 5);
  const fim = new Date(agora.getTime() + 50 * 60000);
  const horaFimAtual = fim.toTimeString().slice(0, 5);

  const dataEl = tr.querySelector(".data");
  const dataMinEl = tr.querySelector(".data-min");
  const inicioEl = tr.querySelector(".inicio");
  const fimEl = tr.querySelector(".fim");

  dataEl.value = dados.data_ministrada || hojeISO;
  dataMinEl.value = dados.data_ministrada || hojeISO;

  inicioEl.value = dados.hora_inicio || horaInicioAtual;
  fimEl.value = dados.hora_fim || horaFimAtual;

  
  dataEl.addEventListener("change", () => {
    dataMinEl.value = dataEl.value;
  });

  dataMinEl.addEventListener("change", () => {
    dataEl.value = dataMinEl.value;
  });

}, 0);


    /* =========================
       AÇÕES
    ========================= */

    const btnEditar = tr.querySelector(".btn-editar");
    const btnSalvar = tr.querySelector(".btn-salvar");
    const btnExcluir = tr.querySelector(".btn-excluir");
    const btnChamada = tr.querySelector(".btn-chamada");

    const statusSalvo = tr.querySelector(".status-salvo");
    const statusFechado = tr.querySelector(".status-fechado");

    const campos = tr.querySelectorAll("input, textarea");

    let salvando = false;

    // ✏️ EDITAR
    if (btnEditar) {
        btnEditar.onclick = () => {
            campos.forEach(c => c.disabled = false);

            btnSalvar.classList.remove("d-none");
            btnExcluir.classList.remove("d-none");
            btnChamada.classList.remove("d-none");

            statusFechado.classList.add("d-none");
            btnEditar.classList.add("d-none");
        };
    }

    // 💾 SALVAR
    btnSalvar.onclick = async () => {
        if (salvando) return;
        salvando = true;

        try {
            await salvarRegistro(tr);

            campos.forEach(c => c.disabled = true);

            btnSalvar.classList.add("d-none");
            btnExcluir.classList.add("d-none");
            btnChamada.classList.add("d-none");

            btnEditar.classList.remove("d-none");
            statusFechado.classList.remove("d-none");

            statusSalvo.classList.remove("d-none");

            setTimeout(() => {
                statusSalvo.classList.add("d-none");
            }, 2500);

        } catch (err) {
            showError("Erro ao salvar registro.", err);
        } finally {
            salvando = false;
        }
    };

    btnExcluir.onclick = () => excluirRegistro(tr);
    btnChamada.onclick = () => criarChamada(tr);

    return tr;
}


/* =========================
   CARREGAR DIÁRIO
========================= */

async function carregarDiario() {
    clearTable();
    registrosCarregados = false;
    atualizarEstadoUI();

    const btnPdf = document.getElementById("btnPdfDiario");
    if (btnPdf) {
        btnPdf.disabled = true;
        btnPdf.title = "Finalize ao menos uma aula para gerar o PDF";
    }

    if (!camposFiltroValidos()) return;

    try {
        const url =
            `/diario-classe/listar/?turma=${turmaSelect.value}` +
            `&disciplina=${disciplinaSelect.value}` +
            `&mes=${mesInput.value}`;

        const resp = await fetch(url);

        if (!resp.ok) throw new Error(`Erro ${resp.status}`);

        const data = await resp.json();
        if (!Array.isArray(data)) throw new Error("Formato inválido");

        if (data.length === 0) {
            tabela.innerHTML = `
                <tr id="estado-vazio">
                    <td colspan="5" class="text-center text-muted">
                        Nenhum registro encontrado.
                        Clique em <strong>➕</strong> para adicionar.
                    </td>
                </tr>
            `;
            atualizarEstadoUI();
            return;
        }

        // renderiza linhas
        data.forEach((registro, idx) => {
            tabela.appendChild(criarLinha(registro, idx));
        });

        registrosCarregados = true;
        atualizarEstadoUI();

        /* =========================
           CONTROLE DO PDF (UX)
        ========================= */

        const temAulaFechada = data.some(r => r.id);

        if (btnPdf) {
            if (temAulaFechada) {
                btnPdf.disabled = false;
                btnPdf.title = "Gerar PDF do Diário do mês";
            } else {
                btnPdf.disabled = true;
                btnPdf.title = "Finalize ao menos uma aula para gerar o PDF";
            }
        }

    } catch (err) {
        showError("Erro ao carregar diário de classe.", err);
    }
}



/* =========================
   NOVO REGISTRO
========================= */

function adicionarLinhaDiario() {
    if (!camposFiltroValidos()) {
        alert("Selecione turma, disciplina e mês antes de adicionar.");
        return;
    }

    /* =========================
       🚫 PROTEÇÃO: aula aberta
    ========================= */

    const aulaAberta = tabela.querySelector(
        'tr[data-id=""]'
    );

    if (aulaAberta) {
        alert("Finalize ou exclua a aula em edição antes de criar outra.");
        aulaAberta.scrollIntoView({ behavior: "smooth", block: "center" });
        aulaAberta.classList.add("nova-aula-highlight");
        return;
    }

    const estadoVazio = document.getElementById("estado-vazio");
    if (estadoVazio) estadoVazio.remove();

    const index = tabela.querySelectorAll("tr").length;
    const novaLinha = criarLinha({}, index);
    tabela.appendChild(novaLinha);

    registrosCarregados = true;
    atualizarEstadoUI();

    /* =========================
       🎯 SCROLL REAL (container)
    ========================= */

    // container que realmente rola
    const containerScroll =
        document.querySelector(".content-wrapper") || document.documentElement;

    setTimeout(() => {
        const top =
            novaLinha.getBoundingClientRect().top +
            containerScroll.scrollTop -
            120;

        containerScroll.scrollTo({
            top,
            behavior: "smooth",
        });

        // foco
        const campoData = novaLinha.querySelector(".data");
        if (campoData) campoData.focus();

        // highlight
        novaLinha.classList.add("nova-aula-highlight");
        setTimeout(() => {
            novaLinha.classList.remove("nova-aula-highlight");
        }, 1800);
    }, 50);
}


/* =========================
   SALVAR REGISTRO
========================= */

async function salvarRegistro(tr) {
    const payload = {
        id: tr.dataset.id || null,
        turma: turmaSelect.value,
        disciplina: disciplinaSelect.value,
        data_ministrada: tr.querySelector(".data-min").value,
        hora_inicio: tr.querySelector(".inicio").value,
        hora_fim: tr.querySelector(".fim").value,
        resumo_conteudo: tr.querySelector(".conteudo").value.trim()
    };

    if (!payload.data_ministrada || !payload.resumo_conteudo) {
        throw new Error("Data e conteúdo são obrigatórios.");
    }
    if (!payload.resumo_conteudo.trim()) {
    alert("Preencha o conteúdo antes de salvar.");
    return;
    }

    const resp = await fetch("/diario-classe/salvar/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify(payload)
    });

    if (!resp.ok) throw new Error(`Erro ${resp.status}`);

    const data = await resp.json();
    tr.dataset.id = data.id;
}


/* =========================
   EXCLUIR
========================= */

async function excluirRegistro(tr) {
    const id = tr.dataset.id;

    if (!id) {
        tr.remove();
        atualizarEstadoUI();
        return;
    }

    if (!confirm("Deseja excluir este registro?")) return;

    try {
        const resp = await fetch(
            `/diario-classe/excluir/${id}/`,
            {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": getCSRFToken()
                }
            }
        );

        if (!resp.ok) throw new Error(`Erro ${resp.status}`);

        tr.remove();
        atualizarEstadoUI();

    } catch (err) {
        showError("Erro ao excluir registro.", err);
    }
}


/* =========================
   CRIAR CHAMADA
========================= */

function criarChamada(tr) {
    const diarioId = tr.dataset.id;

    if (!diarioId) {
        alert("Salve o diário antes de criar a chamada.");
        return;
    }

    window.location.href =
        `/chamada/registrar/?diario=${diarioId}`;
}

/* =========================
   EVENTOS
========================= */

btnNovo.addEventListener("click", adicionarLinhaDiario);
turmaSelect.addEventListener("change", carregarDisciplinasPorTurma);

[disciplinaSelect, mesInput].forEach(el => {
    el.addEventListener("change", carregarDiario);
});

const btnPdf = document.getElementById("btnPdfDiario");

if (btnPdf) {
    btnPdf.addEventListener("click", () => {

        if (!camposFiltroValidos()) {
            alert("Selecione turma, disciplina e mês.");
            return;
        }

        const turma = turmaSelect.value;
        const disciplina = disciplinaSelect.value;
        const mes = mesInput.value;

        const url =
            `/diario-classe/pdf/?turma=${turma}` +
            `&disciplina=${disciplina}` +
            `&mes=${mes}`;

        // abre em nova aba (PDF nunca deve matar o contexto atual)
        window.open(url, "_blank");
    });
}

});
