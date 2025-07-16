async function atualizarGraficoPorDia() {
    const dataSelecionada = document.getElementById('dataSelecionada').value;
    if (!dataSelecionada) {
      alert("Selecione uma data!");
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/dados_grafico?data=${dataSelecionada}`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Erro ao buscar dados");
      }

      const data = await response.json();

      const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: { 
          color: 'rgba(11, 57, 245, 0.88)',
          size: 6
      }
      };

      const layout = {
        xaxis: { title: 'Hora' },
        yaxis: { title: 'Energia (kWh)' },
        plot_bgcolor: '#acaaaa',
        paper_bgcolor: '#acaaaa',
        displayModeBar: true,
        modeBarButtonsToAdd: ['toImage']
      };

      Plotly.newPlot('graficoPorDia', [trace], layout);

    } catch (error) {
      console.error("Erro:", error.message);
      alert("Erro ao carregar dados: " + error.message);
    }
  }

  document.addEventListener('DOMContentLoaded', async function () {
    const calendarEl = document.getElementById('calendarioHoras');

    const calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: 'dayGridMonth',
      locale: 'pt',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: ''
      },
      events: async function (fetchInfo, successCallback, failureCallback) {
        try {
          const response = await fetch('http://localhost:5000/dados');
          const dados = await response.json();

          const eventos = [];

          for (let i = 0; i < dados.datasInicio.length; i++) {
            const dataObj = dados.datasInicio[i];
            const energiaObj = dados.energias[i];

            const data = dataObj.data || dataObj.dataHora || dataObj.timestamp; // ajusta conforme o nome real
            const valor = energiaObj.valor;

            if (data && valor > 0) {
              eventos.push({
                title: `${valor} kWh`,
                start: data,
                allDay: true,
                color: '#007bff'
              });
            }
          }

          successCallback(eventos);
        } catch (error) {
          console.error("Erro ao carregar eventos:", error);
          failureCallback(error);
        }
      },
      dateClick: function(info) {
        document.getElementById('dataSelecionada').value = info.dateStr;
        atualizarGraficoPorDia();
      }
    });

    calendar.render();
  });