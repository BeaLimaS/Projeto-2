async function atualizarGrafico() {
    try {
        // força o modo CORS e vê o status da resposta
        const response = await fetch("http://localhost:5000/dados", {
            method: 'GET',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        console.log("Fetch /dados →", response.status, response.statusText);

        if (!response.ok) {
            console.error("Resposta do servidor não OK:", await response.text());
            return;
        }

        const data = await response.json();
        console.log("Dados recebidos do back-end:", data);

        if (data.error) {
            console.error("Erro no payload:", data.error);
            return;
        }

        // monta o trace só depois de teres certeza que data.labels/values existem
        console.log("labels:", data.datasInicio);
        console.log("values:", data.energias);

        const trace = {
            x: data.datasInicio,
            y: data.energias,
            type: 'bar',
            marker: { 
                color: 'rgba(11, 57, 245, 0.88)',
                size: 6
            }
        };
        const layout = {
            xaxis: { title: 'Data', tickangle: -45, tickfont: { size: 12 }, gridcolor: 'rgba(200, 200, 200, 0.2)' },
            yaxis: { title: 'Energia (kW)', tickfont: { size: 12 }, gridcolor: 'rgba(200,200,200,0.2)' },
            plot_bgcolor: '#acaaaa',
            paper_bgcolor: '#acaaaa',
            displayModeBar: true,
            modeBarButtonsToAdd: ['toImage']
        };

        Plotly.newPlot('grafico', [trace], layout);
    } catch (error) {
        console.error("Erro ao buscar ou processar dados:", error);
    }
}

// chama e repete
atualizarGrafico();
setInterval(atualizarGrafico, 60000);
