from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from pymongo import MongoClient
import requests
import urllib.parse
import time
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Permite que o frontend aceda à API

# Conectar ao MongoDB (local)
client = MongoClient("mongodb://localhost:27017/")
db = client["CarregadoresDB"]
sessoes_carga = db["sessoes_carga"]

#para os testes com os dados dummy do RFID
colecao_teste = db["sessoes_carga_teste"]


print("Base de dados conectada com sucesso!")

# ========================== Teste de inserção de dados dummy ==========================

@app.route('/teste-rfid', methods=['POST'])
def testar_rfid():
    data = request.get_json()
    codigo_rfid = data.get('codigo')

    if not codigo_rfid:
        return jsonify({"erro": "Código RFID em falta"}), 400

    dados = {
        "codigo_rfid": codigo_rfid,
        "data_hora": datetime.now()
    }

    # Inserir na coleção de testes
    db["sessoes_carga_teste"].insert_one(dados)

    return jsonify({"status": "Teste registado"}), 200




# ========================== Request dos dados ==========================

def get_last_entry_date():
    """Retorna a data da última entrada na coleção sessoes_carga"""
    last_entry = sessoes_carga.find_one(sort=[("begin", -1)])
    if last_entry:
        return last_entry["begin"]
    return "2026-03-23T23:59:59.999Z"  # Data padrão se não houver entradas

def atualizar_dados():
    """Busca novos dados da API e insere no MongoDB"""
    last_entry_date = get_last_entry_date()
    filtro = {
        "where": {
            "begin": {
                "between": ["2022-01-01T00:00:00.000Z", last_entry_date]
            },
            "siteId": "63722d1ffaf87162cc48fe46"
        },
        "order": "begin+desc"
    }

    filtro_codificado = urllib.parse.quote(str(filtro).replace("'", '"'))
    url = f"https://dev-hgp-sgi.streamline.pt/api/transactions?filter={filtro_codificado}"

    response = requests.get(url)
    if response.status_code == 200:
        novos_dados = response.json()
        print(novos_dados)  # Verificação da resposta da API
        if novos_dados:  # Evita inserir se a resposta estiver vazia
            for dado in novos_dados:
                print(dado)  # Verificação dos dados antes da inserção
                if not sessoes_carga.find_one({"begin": dado["begin"]}):
                    sessoes_carga.insert_one(dado)
            print("Base de dados atualizada com novos dados!")
    else:
        print(f"Erro ao buscar dados: {response.status_code} - {response.text}")

# ========================== Rota para a página principal ==========================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dados')
def get_all_data():
    try:
        pipeline = [
            {
                "$project": {
                    "beginDate": {
                        "$dateToString": {
                            "format": "%Y-%m-%dT%H:%M:%S.%L",
                            "date": {"$toDate": "$begin"}
                        }
                    },
                    "endDate": {
                        "$dateToString": {
                            "format": "%Y-%m-%dT%H:%M:%S.%L",
                            "date": {"$toDate": "$end"}
                        }
                    },
                    "energyDelivered": 1,
                    "evseId": 1
                }
            },
            {
                "$group": {
                    "_id": "$beginDate",  # Ou podes usar outra lógica se quiseres agrupar de outra forma
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "datasFim": { "$first": "$endDate" },  # Opcional: guarda o primeiro fim associado
                    "carregador": { "$first": "$evseId" },
                    "registos": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            },
            {
                "$project": {
                    "dataInicio": "$_id",
                    "dataFim": "$datasFim",
                    "carregador": "$carregador",
                    "energia": "$totalEnergy",
                    "_id": 0
                }
            }
        ]

        resultados = list(db.sessoes_carga.aggregate(pipeline))

        # Extrair os arrays para o front-end
        labelsInicio = [doc["dataInicio"] for doc in resultados]
        labelsFim = [doc["dataFim"] for doc in resultados]
        evse = [doc["carregador"] for doc in resultados]
        values = [doc["energia"] for doc in resultados]

        return jsonify({
            "datasInicio": labelsInicio,
            "datasFim": labelsFim,
            "evse": evse,
            "energias": values
        })

    except Exception as e:
        print(f"Erro na rota /dados: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ========================== Rota para o gráfico das pessoas ==========================
@app.route('/dados/consumo-por-pessoa')
def consumo_por_pessoa():
    try:
        # Pipeline de agregação para agrupar por userId e data
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "data": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$toDate": "$begin"}  # Converte string para Date
                            }
                        },
                        "idTag": "$idTag"  # Agrupa por userId (pessoa)
                    },
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "registos": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.data": 1}  # Ordena por data ASC
            },
            {
                "$project": {
                    "data": "$_id.data",
                    "idTag": "$_id.idTag",
                    "energia": "$totalEnergy",
                    "_id": 0
                }
            }
        ]

        resultados = list(db.sessoes_carga.aggregate(pipeline))

        # Agrupar os dados por userId
        usuarios = {}
        for doc in resultados:
            if doc['idTag'] not in usuarios:
                usuarios[doc['idTag']] = []
            usuarios[doc['idTag']].append({
                'data': doc['data'],
                'energia': doc['energia']
            })

        # Retorna os dados agrupados por pessoa
        return jsonify(usuarios)

    except Exception as e:
        print(f"Erro na rota /dados/consumo-por-pessoa: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ========================== Exemplo para os gráficos ==========================

@app.route('/dados_grafico')
def dados_grafico():
    """Retorna os dados para os gráficos, agrupados por hora."""
    data_str = request.args.get('data')
    print(f"Data recebida: {data_str}")
    
    if not data_str:
        return jsonify({"error": "Parâmetro 'data' é obrigatório"}), 400

    try:
        # Converter a string para um objeto datetime
        data_inicio = datetime.strptime(data_str, '%Y-%m-%d')
        data_fim = data_inicio + timedelta(days=1)
    except ValueError as e:
        return jsonify({"error": f"Formato de data inválido: {str(e)}"}), 400

    try:
        # Converter datas para o formato ISO com Z (UTC)
        inicio_iso = data_inicio.isoformat() + "Z"
        fim_iso = data_fim.isoformat() + "Z"

        # Query para filtrar por datas
        query = {
            "begin": {
                "$gte": inicio_iso,
                "$lt": fim_iso
            }
        }

        # Buscar dados no MongoDB
        dados = list(sessoes_carga.find(query, {"_id": 0, "begin": 1, "energyDelivered": 1}))

        # Agrupar por hora
        valores_por_hora = {str(hora).zfill(2): 0 for hora in range(24)}  # Inicializa todas as horas com 0

        for d in dados:
            try:
                hora = datetime.fromisoformat(d["begin"].replace("Z", "")).hour
                hora_str = str(hora).zfill(2)  # Formata como "00", "01", ..., "23"
                valores_por_hora[hora_str] += d.get("energyDelivered", 0)
            except KeyError as e:
                print(f"Documento inválido: campo {str(e)} ausente. ID: {d.get('_id', 'desconhecido')}")
                continue

        # Preparar dados para resposta
        horas = [f"{h}h" for h in valores_por_hora.keys()]
        valores = list(valores_por_hora.values())

        return jsonify({
            "labels": horas,
            "values": valores
        })

    except Exception as e:
        print(f"Erro interno: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# ========================== Rota para os dados por carregador ==========================
@app.route('/dados/consumo-por-carregador')
def consumo_por_carregador():
    try:
        # Pipeline de agregação para agrupar por userId e data
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "data": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$toDate": "$begin"}  # Converte string para Date
                            }
                        },
                        "idCarregador": "$evseId"  # Agrupa por userId (pessoa)
                    },
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "registos": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.data": 1}  # Ordena por data ASC
            },
            {
                "$project": {
                    "data": "$_id.data",
                    "idCarregador": "$_id.idCarregador",
                    "energia": "$totalEnergy",
                    "_id": 0
                }
            }
        ]

        resultados = list(db.sessoes_carga.aggregate(pipeline))

        # Agrupar os dados por userId
        usuarios = {}
        for doc in resultados:
            if doc['idCarregador'] not in usuarios:
                usuarios[doc['idCarregador']] = []
            usuarios[doc['idCarregador']].append({
                'data': doc['data'],
                'energia': doc['energia']
            })

        # Retorna os dados agrupados por pessoa
        return jsonify(usuarios)

    except Exception as e:
        print(f"Erro na rota /dados/consumo-por-pessoa: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ========================== Loop para atualização automática ==========================

def atualizar_periodicamente():
    """Atualiza os dados a cada 1000 segundos"""
    while True:
        atualizar_dados()
        time.sleep(1000)

# ========================== Execução Principal ==========================
if __name__ == '__main__':
    from threading import Thread
    # Iniciar a atualização automática dos dados em segundo plano
    Thread(target=atualizar_periodicamente, daemon=True).start()
    
    # Iniciar o servidor Flask com reloader desativado para evitar conflitos com a thread
    app.run(debug=True, use_reloader=False)
