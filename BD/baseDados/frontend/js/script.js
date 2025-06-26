let currentPage = 1;
const rowsPerPage = 100;
let datasInicio = [];
let horasInicio = [];
let datasFim = [];
let horasFim = [];
let energias = [];


async function carregarDados() {
  try {
    const response = await fetch('http://localhost:5000/dados');
    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const json = await response.json();
    console.log("Resposta do servidor:", json);

    datasInicio = json.datasInicio;
    datasFim = json.datasFim;
    energias = json.energias;

    if (!Array.isArray(datasInicio) || !Array.isArray(datasFim) || !Array.isArray(energias) ||
      datasInicio.length !== energias.length || datasFim.length !== energias.length) {
      throw new Error('Formato de dados inválido ou arrays com comprimentos diferentes');
    }

    renderTable();

  } catch (error) {
    console.error("Falha ao carregar dados:", error);
  }
}

function renderTable() {
  const tbody = document.querySelector('table tbody');
  tbody.innerHTML = '';

  const start = (currentPage - 1) * rowsPerPage;
  const end = Math.min(start + rowsPerPage, datasInicio.length);

  for (let i = start; i < end; i++) {
    const row = document.createElement('tr');
    const inicioFormatado = new Date(datasInicio[i]).toLocaleDateString('pt-PT', { year: 'numeric', month: '2-digit', day: '2-digit',hour: 'numeric', minute: 'numeric' });
    const fimFormatado = new Date(datasFim[i]).toLocaleDateString('pt-PT', { year: 'numeric', month: '2-digit', day: '2-digit',hour: 'numeric', minute: 'numeric' });
    row.innerHTML = `
      <td>${inicioFormatado}</td>
      <td>${fimFormatado}</td>
      <td>${energias[i]?.toFixed(3) ?? 'N/A'}</td>
    `;
    tbody.appendChild(row);
  }

  updatePaginationButtons();
}

function updatePaginationButtons() {
  const totalPages = Math.ceil(datasInicio.length / rowsPerPage);
  //document.getElementById('pagina-atual').innerText = `Página ${currentPage} de ${totalPages}`;
  
  document.getElementById('btn-anterior').disabled = currentPage === 1;
  document.getElementById('btn-proximo').disabled = currentPage === totalPages;
}

document.getElementById('btn-anterior').addEventListener('click', () => {
  if (currentPage > 1) {
    currentPage--;
    renderTable();
  }
});

document.getElementById('btn-proximo').addEventListener('click', () => {
  if (currentPage < Math.ceil(datasInicio.length / rowsPerPage)) {
    currentPage++;
    renderTable();
  }
});

document.addEventListener('DOMContentLoaded', carregarDados);
