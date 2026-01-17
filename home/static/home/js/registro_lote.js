

const PREVIEW_MATRICULA_URL = '/preview-matricula/';

/* =========================================================
   DOM READY
========================================================= */

document.addEventListener('DOMContentLoaded', () => {

  const alunosContainer = document.getElementById('alunos-container');
  const addAlunoBtn = document.getElementById('addAlunoBtn');
  const submitBtn = document.getElementById('submitButton');

  if (!alunosContainer || !addAlunoBtn || !submitBtn) {
    console.warn('⚠️ Elementos da matrícula em lote não encontrados');
    return;
  }

  aplicarMascaraTelefone();
  carregarPreviewMatriculas();
  reindexarTudo();
document.querySelectorAll('.aluno-bloco').forEach(bloco => {
  const index = Number(bloco.dataset.index);
  bindAtualizacaoNome(index);
});

  

  /* ==========================================
     ADD / REMOVE ALUNO
  ========================================== */

  addAlunoBtn.addEventListener('click', () => {
    const index = alunosContainer.children.length;

    const novoAluno = criarAlunoBloco(index);
    alunosContainer.appendChild(novoAluno);

    duplicarBloco('.aluno-saude', index);
    duplicarBloco('.aluno-transporte', index);
    duplicarBloco('.aluno-autorizacoes', index);

    aplicarMascaraTelefone(novoAluno);
    bindAtualizacaoNome(index);

    reindexarTudo();
    carregarPreviewMatriculas();
  
    novoAluno.scrollIntoView({ behavior: 'smooth', block: 'start' });
    showTab(0);
  });

  alunosContainer.addEventListener('click', (e) => {
  if (!e.target.classList.contains('remove-aluno')) return;

  const bloco = e.target.closest('.aluno-bloco');

  // remove abas relacionadas usando o próprio bloco
  const indexAtual = [...document.querySelectorAll('.aluno-bloco')]
    .indexOf(bloco);

  removerBlocoRelacionado(indexAtual);

  bloco.remove();

  // 🔥 agora sim, reindexa com base no DOM atual
  reindexarTudo();
  carregarPreviewMatriculas();
});


  /* ==========================================
     SUBMIT
  ========================================== */

  submitBtn.addEventListener('click', () => {
    const payload = montarPayload();
    if (!payload) return;

    if (!validarCpfDuplicado(payload.alunos)) return;

    fetch('/alunos/salvar-lote/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'sucesso') {
          alert(`✅ ${data.total} aluno(s) cadastrados com sucesso`);
          window.location.href = '/listar_aluno/';
          return;
        }

        if (data.status === 'parcial') {
          let msg = `⚠️ Alguns alunos não foram cadastrados:\n\n`;
          (data.erros || []).forEach(e => {
            msg += `Aluno ${e.aluno}: ${e.erro}\n`;
          });
          alert(msg);
          return;
        }

        alert(data.mensagem || 'Erro ao salvar matrículas');
      })
      .catch(() => alert('Erro inesperado ao salvar matrículas'));
  });

});


/* =========================================================
   CRIAÇÃO DE BLOCO DE ALUNO (COM MATRÍCULA)
========================================================= */

function criarAlunoBloco(index) {
  const div = document.createElement('div');
  div.className = 'aluno-bloco';
  div.dataset.index = index;

  div.innerHTML = `
    <h4>
    <span class="titulo-aluno">Aluno ${index + 1}</span>
    </h4>
    <div class="form-row row">
      <div class="form-group col-md-2">
        <label>Matrícula</label>
        <input type="text"
               name="alunos[${index}][matricula]"
               class="form-control"
               placeholder="Gerada"
               readonly>
      </div>

      <div class="form-group col-md-8">
        <label>Nome</label>
        <input type="text"
               name="alunos[${index}][nome]"
               class="form-control">
      </div>

      <div class="form-group col-md-2">
        <label>Data nasc.</label>
        <input type="date"
               name="alunos[${index}][data_nascimento]"
               class="form-control">
      </div>
    </div>

    <div class="form-row row">
      <div class="form-group col-md-4">
        <label>CPF</label>
        <input type="text"
               name="alunos[${index}][cpf]"
               class="form-control">
      </div>

      <div class="form-group col-md-4">
        <label>RG</label>
        <input type="text"
               name="alunos[${index}][rg]"
               class="form-control">
      </div>

      <div class="form-group col-md-4">
        <label>Sexo</label>
        <select name="alunos[${index}][sexo]"
                class="form-control">
          <option value="">Selecione</option>
          <option value="Masculino">Masculino</option>
          <option value="Feminino">Feminino</option>
        </select>
      </div>
    </div>

    <div class="form-row row">
      <div class="form-group col-md-4">
        <label>Série/Ano</label>
        <input type="text"
               name="alunos[${index}][serie_ano]"
               class="form-control">
      </div>

      <div class="form-group col-md-4">
        <label>Turno</label>
        <select name="alunos[${index}][turno_aluno]"
                class="form-control">
          <option value="">Selecione</option>
          <option value="Matutino">Matutino</option>
          <option value="Vespertino">Vespertino</option>
          <option value="Integral">Integral</option>
        </select>
      </div>

      <div class="form-group col-md-4">
        <label>Turma</label>
        <select name="alunos[${index}][turma_principal_id]"
                class="form-control">
          <option value="">Selecione</option>
          ${window.TURMAS_OPTIONS || ''}
        </select>
      </div>
    </div>

    <hr>
  `;

  return div;
}

/* =========================================================
   DUPLICAÇÃO DE ABAS (SAÚDE / TRANSPORTE / AUTORIZAÇÕES)
========================================================= */

function duplicarBloco(selector, index) {
  const blocos = document.querySelectorAll(selector);
  if (!blocos.length) return;

  const clone = blocos[blocos.length - 1].cloneNode(true);
  clone.dataset.index = index;

  const h4 = clone.querySelector('h4');
  if (h4) h4.textContent = `Aluno ${index + 1}`;

  clone.querySelectorAll('[name]').forEach(el => {
    el.name = el.name.replace(/alunos\[\d+]/, `alunos[${index}]`);
    if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = false;
    } else {
      el.value = '';
    }
  });

  blocos[blocos.length - 1].parentElement.appendChild(clone);
}

/* =========================================================
   UTIL — GARANTIR BOTÃO REMOVER
========================================================= */

function garantirBotaoRemover(bloco) {
  if (bloco.querySelector('.remove-aluno')) return;

  const h4 = bloco.querySelector('h4');
  if (!h4) return;

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'remove-aluno btn btn-sm btn-danger';
  btn.style.marginLeft = '8px';
  btn.textContent = 'Remover';

  h4.appendChild(btn);
}

/* =========================================================
   REINDEXAÇÃO
========================================================= */

function removerBlocoRelacionado(index) {
  ['.aluno-saude', '.aluno-transporte', '.aluno-autorizacoes']
    .forEach(sel => {
      const bloco = document.querySelector(`${sel}[data-index="${index}"]`);
      if (bloco) bloco.remove();
    });
}

function reindexarTudo() {
  reindexarGrupo('.aluno-bloco');
  reindexarGrupo('.aluno-saude');
  reindexarGrupo('.aluno-transporte');
  reindexarGrupo('.aluno-autorizacoes');
}

function reindexarGrupo(selector) {
  document.querySelectorAll(selector).forEach((bloco, i) => {
    bloco.dataset.index = i;

    // atualiza título
    atualizarTituloAluno(i);
    bindAtualizacaoNome(i);

    // corrige names
    bloco.querySelectorAll('[name]').forEach(el => {
      el.name = el.name.replace(/alunos\[\d+]/, `alunos[${i}]`);
    });

    // ===== BOTÃO REMOVER (REGRA ÚNICA E ABSOLUTA) =====
    const h4 = bloco.querySelector('h4');
    let btn = h4.querySelector('.remove-aluno');

    if (i === 0) {
      // primeiro aluno nunca pode remover
      if (btn) btn.remove();
    } else {
      // todos os outros DEVEM ter botão
      if (!btn) {
        btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'remove-aluno btn btn-sm btn-danger';
        btn.style.marginLeft = '8px';
        btn.textContent = 'Remover';
        h4.appendChild(btn);
      }
    }
  });
}



/* =========================================================
   PAYLOAD + VALIDAÇÕES
========================================================= */

function montarPayload() {
  const alunos = [];
  const blocos = document.querySelectorAll('.aluno-bloco');

  if (blocos.length < 2) {
    alert('⚠️ Cadastre pelo menos dois alunos.');
    return null;
  }

  blocos.forEach(bloco => {
    const index = bloco.dataset.index;
    const aluno = {};

    document.querySelectorAll(`[name^="alunos[${index}]"]`).forEach(el => {
      const campo = el.name.match(/\[(\w+)]$/)[1];
      aluno[campo] = el.type === 'checkbox'
        ? el.checked
        : el.value.trim();
    });

    alunos.push(aluno);
  });

  return { alunos };
}

function validarCpfDuplicado(alunos) {
  const vistos = new Set();

  for (let i = 0; i < alunos.length; i++) {
    const cpf = (alunos[i].cpf || '').replace(/\D/g, '');
    if (!cpf) continue;

    if (vistos.has(cpf)) {
      alert(`⚠️ CPF duplicado (Aluno ${i + 1})`);
      return false;
    }
    vistos.add(cpf);
  }
  return true;
}

/* =========================================================
   UX — TÍTULO COM NOME
========================================================= */

function bindAtualizacaoNome(index) {
  const input = document.querySelector(`input[name="alunos[${index}][nome]"]`);
  if (!input) return;
  input.addEventListener('input', () => atualizarTituloAluno(index));
}

function atualizarTituloAluno(index) {
  const nome = document
    .querySelector(`input[name="alunos[${index}][nome]"]`)
    ?.value.trim();

  const titulo = nome
    ? `Aluno ${index + 1} — ${nome}`
    : `Aluno ${index + 1}`;

  [
    `.aluno-bloco[data-index="${index}"]`,
    `.aluno-saude[data-index="${index}"]`,
    `.aluno-transporte[data-index="${index}"]`,
    `.aluno-autorizacoes[data-index="${index}"]`
  ].forEach(sel => {
    const bloco = document.querySelector(sel);
    if (!bloco) return;

    const span = bloco.querySelector('.titulo-aluno');
    if (span) span.textContent = titulo;
  });
}

/* =========================================================
   MÁSCARAS
========================================================= */

function aplicarMascaraTelefone(container = document) {
  container.querySelectorAll('input[name*="telefone"]').forEach(input => {
    input.addEventListener('input', () => {
      let v = input.value.replace(/\D/g, '').slice(0, 11);
      input.value =
        v.length <= 10
          ? v.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3')
          : v.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
    });
  });
}

function carregarPreviewMatriculas() {
  const alunos = document.querySelectorAll('.aluno-bloco');
  const quantidade = alunos.length;

  if (!quantidade) return;

  fetch(`${PREVIEW_MATRICULA_URL}?quantidade=${quantidade}`)
    .then(r => r.json())
    .then(data => {
      if (!data.matriculas) return;

      data.matriculas.forEach((matricula, index) => {
        const input = document.querySelector(
          `input[name="alunos[${index}][matricula]"]`
        );
        if (input) {
          input.value = matricula;
        }
      });
    })
    .catch(() => {
      console.warn('⚠️ Erro ao carregar preview de matrículas');
    });
}

/* =========================================================
   CSRF
========================================================= */

function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
}
