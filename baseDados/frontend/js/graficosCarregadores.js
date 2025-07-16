let todosOsDados = {};  // Guardar todos os dados aqui
let todasAsDatas = [];  // Para fixar eixo X com todas as datas possíveis

async function carregarDados() {
    try {
        const response = await fetch('http://localhost:5000/dados/consumo-por-carregador');
 
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        const json = await response.json();
        console.log("Dados recebidos:", json);

        todosOsDados = json;

        // Extrair todas as datas disponíveis
        const datasSet = new Set();
        Object.values(json).forEach(consumos => {
            consumos.forEach(c => datasSet.add(c.data));
        });
        todasAsDatas = Array.from(datasSet).sort();

        // Preencher o selecionador
        const select = document.getElementById('selecionadorIdCarregador');
        Object.keys(json).forEach(idCarregador => {
            const option = document.createElement('option');
            option.value = idCarregador;
            option.textContent = idCarregador;
            select.appendChild(option);
        });

    } catch (error) {
        console.error("Erro ao carregar os dados:", error);
    }
}

function atualizarGraficoSelecionado() {
    const select = document.getElementById('selecionadorIdCarregador');
    const idSelecionado = select.value;

    if (!idSelecionado) {
        // Se não selecionou ninguém, limpa o gráfico
        document.getElementById('graficoCarregadorSelecionada').innerHTML = '';
        return;
    }

    criarGrafico(idSelecionado, todosOsDados[idSelecionado]);
}

function criarGrafico(idCarregador, consumos) {
    const energiaPorData = {};  // Mapa: data -> energia
    consumos.forEach(c => {
        energiaPorData[c.data] = c.energia;
    });

    // Para garantir que mesmo dias sem dados aparecem com 0
    const energias = todasAsDatas.map(data => energiaPorData[data] || 0);

    const trace = {
        x: todasAsDatas,
        y: energias,
        name: idCarregador,
        type: 'bar',
            marker: { 
                color: 'rgba(11, 57, 245, 0.88)',
                size: 6
            }
    };

    const layout = {
        title: `Consumo de Energia - ${idCarregador}`,
        xaxis: {
            title: 'Data',
            tickangle: -45
        },
        yaxis: {
            title: 'Energia (kWh)',
            range: [0, Math.max(...energias) * 1.2]  // Um pouco acima do máximo
        },
        plot_bgcolor: '#acaaaa',
        paper_bgcolor: '#acaaaa',
        plot_bgcolor: '#acaaaa',
        paper_bgcolor: '#acaaaa',
        displayModeBar: true,
        modeBarButtonsToAdd: ['toImage'],
        barmode: 'stack'
    };

    Plotly.newPlot('graficoCarregadorSelecionada', [trace], layout);
}

function filtrarOpcoes() {
    const input = document.getElementById('pesquisaIdCarregador').value.toLowerCase();
    const select = document.getElementById('selecionadorIdCarregador');

    // Percorre todas as opções e mostra/esconde conforme o que foi digitado
    Array.from(select.options).forEach(option => {
        if (option.value.toLowerCase().includes(input) || option.textContent.toLowerCase().includes(input)) {
            option.style.display = 'block';
        } else if (option.value !== '') {
            option.style.display = 'none';
        }
    });

    // Se houver alguma entrada na pesquisa, abre o selecionador
    if (input.length > 0) {
        select.size = Math.min(5, select.options.length); // Mostra até 5 opções (ou menos se houver menos)
        //select.style.display = 'block'; // Garante que o select está visível
    } else {
        select.size = 1; // Volta ao tamanho normal
    }
}
function fecharSelecionador() {
    const select = document.getElementById('selecionadorIdCarregador');
    select.size = 1; // Volta ao tamanho normal
}


document.addEventListener('DOMContentLoaded', carregarDados);
