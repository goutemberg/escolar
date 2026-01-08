/* =========================================================
   MATRÍCULA EM LOTE - JS
========================================================= */

document.addEventListener('DOMContentLoaded', () => {

  const alunosContainer = document.getElementById('alunos-container');
  const addAlunoBtn = document.getElementById('addAlunoBtn');
  const submitBtn = document.getElementById('submitButton');

  if (!alunosContainer || !addAlunoBtn || !submitBtn) {
    console.warn('⚠️ Elementos da matrícula em lote não encontrados');
    return;
  }

  /* ==========================================
     ADD / REMOVE ALUNO
  ========================================== */

  addAlunoBtn.addEventListener('click', () => {
    const index = alunosContainer.children.length;
    alunosContainer.appendChild(criarAlunoBloco(index));
  });

  alunosContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-aluno')) {
      e.target.closest('.aluno-bloco').remove();
      reindexarAlunos();
    }
  });

  /* ==========================================
     SUBMIT
  ========================================== */

  submitBtn.addEventListener('click', () => {
    const payload = montarPayload();

    if (!payload) return;

    console.log('📦 Payload matrícula em lote:', payload);

    fetch('/alunos/salvar_lote/', {
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
        alert(`✅ ${data.total} alunos matriculados com sucesso`);
        window.location.href = '/alunos/';
      } else {
        alert(data.mensagem || 'Erro ao salvar matrículas');
      }
    });
  });

});

/* =========================================================
   HELPERS
========================================================= */

function criarAlunoBloco(index) {
  const div = document.createElement('div');
  div.className = 'aluno-bloco';
  div.dataset.index = index;

  div.innerHTML = `
    <h4>
      Aluno ${index + 1}
      <button type="button" class="remove-aluno btn btn-sm btn-danger" style="margin-left:8px">
        Remover
      </button>
    </h4>

    <div class="form-row">
      <div class="form-group">
        <label>Nome</label>
        <input type="text" name="alunos[${index}][nome]">
      </div>

      <div class="form-group short-field">
        <label>Data de nascimento</label>
        <input type="date" name="alunos[${index}][data_nascimento]">
      </div>
    </div>

    <div class="form-row">
      <div class="form-group short-field">
        <label>CPF</label>
        <input type="text" name="alunos[${index}][cpf]">
      </div>

      <div class="form-group short-field">
        <label>RG</label>
        <input type="text" name="alunos[${index}][rg]">
      </div>

      <div class="form-group short-field">
        <label>Sexo</label>
        <select name="alunos[${index}][sexo]">
          <option value="">Selecione</option>
          <option value="Masculino">Masculino</option>
          <option value="Feminino">Feminino</option>
        </select>
      </div>
    </div>

    <hr>
  `;

  return div;
}

function reindexarAlunos() {
  const blocos = document.querySelectorAll('.aluno-bloco');

  blocos.forEach((bloco, i) => {
    bloco.dataset.index = i;
    bloco.querySelector('h4').childNodes[0].nodeValue = `Aluno ${i + 1} `;

    bloco.querySelectorAll('[name]').forEach(el => {
      el.name = el.name.replace(/alunos\[\d+]/, `alunos[${i}]`);
    });
  });
}

/* =========================================================
   PAYLOAD
========================================================= */

function montarPayload() {

  const alunos = [];
  const blocos = document.querySelectorAll('.aluno-bloco');

  if (blocos.length < 2) {
    alert('⚠️ Cadastre pelo menos dois alunos.');
    return null;
  }

  blocos.forEach(bloco => {
    const aluno = {};
    bloco.querySelectorAll('[name]').forEach(el => {
      const campo = el.name.match(/\[(\w+)]$/)[1];
      aluno[campo] = el.value.trim();
    });
    alunos.push(aluno);
  });

  return {
    dados_comuns: {
      serie_ano: document.getElementById('serie_ano')?.value || '',
      turno: document.getElementById('turno')?.value || '',
      turma_id: document.getElementById('turma_id')?.value || ''
    },
    alunos: alunos
  };
}

/* =========================================================
   CSRF
========================================================= */

function getCsrfToken() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return input ? input.value : '';
}
