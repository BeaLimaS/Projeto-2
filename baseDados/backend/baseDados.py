from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from pymongo import MongoClient
import requests
import urllib.parse
import time
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import json
import os
import ssl

app = Flask(__name__)
CORS(app)

# Configurações do MongoDB
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = client["CarregadoresDB"]
sessoes_carga = db["sessoes_carga"]
colecao_teste = db["sessoes_carga_teste"]

# Configuração do JSON
JSON_FILE = "energy_data.json"
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'w') as f:
        json.dump({"energy_data": []}, f)

# Configuração MQTT para HiveMQ Cloud
MQTT_BROKER = "c4a0e4602d804089ad70745f4aa640d3.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC_POWER = "Esp32/potencia"
MQTT_USERNAME = "seu_usuario"  # Substitua pelo seu username
MQTT_PASSWORD = "sua_senha"    # Substitua pela sua senha

# ==================== MQTT Client ====================
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Conectado com sucesso ao broker MQTT")
        client.subscribe(MQTT_TOPIC_POWER)
    else:
        print(f"Falha na conexão. Código: {reason_code}")

def on_mqtt_message(client, userdata, message):
    try:
        print(f"Mensagem recebida no tópico {message.topic}: {message.payload.decode()}")
        
        if message.topic == MQTT_TOPIC_POWER:
            power_value = float(message.payload.decode())
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Documento para MongoDB
            mongo_doc = {
                "begin": timestamp,
                "energyDelivered": power_value,
                "evseId": "1",
                "end": timestamp,
                "siteId": "63722d1ffaf87162cc48fe46"
            }
            
            # Inserir no MongoDB
            sessoes_carga.insert_one(mongo_doc)
            
            # Atualizar JSON
            with open(JSON_FILE, 'r+') as f:
                data = json.load(f)
                data["energy_data"].append({
                    "timestamp": timestamp,
                    "power": power_value,
                    "evseId": "1"
                })
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
            
            print("Dados armazenados no MongoDB e JSON")
            
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {str(e)}")

def setup_mqtt():
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    # Configura SSL/TLS
    mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Erro na conexão MQTT: {str(e)}")

# ==================== Funções da API ====================
def get_last_entry_date():
    last_entry = sessoes_carga.find_one(sort=[("begin", -1)])
    if last_entry:
        return last_entry["begin"]
    return "2022-01-01T00:00:00.000Z"

def atualizar_dados():
    try:
        last_entry_date = get_last_entry_date()
        filtro = {
            "where": {
                "begin": {"between": ["2022-01-01T00:00:00.000Z", last_entry_date]},
                "siteId": "63722d1ffaf87162cc48fe46"
            },
            "order": "begin DESC",
            "limit": 1000
        }

        filtro_codificado = urllib.parse.quote(str(filtro).replace("'", '"'))
        url = f"https://dev-hgp-sgi.streamline.pt/api/transactions?filter={filtro_codificado}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        novos_dados = response.json()

        if novos_dados:
            # Processar e armazenar dados
            dados_processados = []
            for dado in novos_dados:
                if not all(k in dado for k in ["begin", "energyDelivered"]):
                    continue
                
                dado["evseId"] = "1"
                if "end" not in dado:
                    dado["end"] = dado["begin"]
                
                dados_processados.append(dado)
            
            # Inserir no MongoDB
            if dados_processados:
                sessoes_carga.insert_many(dados_processados)
            
            # Atualizar JSON
            json_data = []
            for doc in dados_processados:
                json_data.append({
                    "timestamp": doc["begin"],
                    "power": doc["energyDelivered"],
                    "evseId": doc["evseId"]
                })
            
            with open(JSON_FILE, 'r+') as f:
                data = json.load(f)
                data["energy_data"].extend(json_data)
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
            
            print(f"Dados atualizados: {len(dados_processados)} registros")
        else:
            print("Nenhum novo dado encontrado na API")

    except Exception as e:
        print(f"Erro ao atualizar dados: {str(e)}")

def atualizar_periodicamente():
    while True:
        atualizar_dados()
        time.sleep(1000)

# ==================== Rotas Flask ====================
@app.route('/')
def home():
    return render_template('index.html')

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

    colecao_teste.insert_one(dados)
    return jsonify({"status": "Teste registado"}), 200

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
                    "_id": "$beginDate",
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "datasFim": { "$first": "$endDate" },
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

        resultados = list(sessoes_carga.aggregate(pipeline))

        return jsonify({
            "datasInicio": [doc["dataInicio"] for doc in resultados],
            "datasFim": [doc["dataFim"] for doc in resultados],
            "evse": [doc["carregador"] for doc in resultados],
            "energias": [doc["energia"] for doc in resultados]
        })

    except Exception as e:
        print(f"Erro na rota /dados: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/dados/consumo-por-pessoa')
def consumo_por_pessoa():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "data": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$toDate": "$begin"}
                            }
                        },
                        "idTag": "$idTag"
                    },
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "registos": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.data": 1}
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

        resultados = list(sessoes_carga.aggregate(pipeline))

        usuarios = {}
        for doc in resultados:
            if doc['idTag'] not in usuarios:
                usuarios[doc['idTag']] = []
            usuarios[doc['idTag']].append({
                'data': doc['data'],
                'energia': doc['energia']
            })

        return jsonify(usuarios)

    except Exception as e:
        print(f"Erro na rota /dados/consumo-por-pessoa: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/dados_grafico')
def dados_grafico():
    data_str = request.args.get('data')
    print(f"Data recebida: {data_str}")
    
    if not data_str:
        return jsonify({"error": "Parâmetro 'data' é obrigatório"}), 400

    try:
        data_inicio = datetime.strptime(data_str, '%Y-%m-%d')
        data_fim = data_inicio + timedelta(days=1)

        inicio_iso = data_inicio.isoformat() + "Z"
        fim_iso = data_fim.isoformat() + "Z"

        query = {
            "begin": {
                "$gte": inicio_iso,
                "$lt": fim_iso
            }
        }

        dados = list(sessoes_carga.find(query, {"_id": 0, "begin": 1, "energyDelivered": 1}))

        valores_por_hora = {str(hora).zfill(2): 0 for hora in range(24)}

        for d in dados:
            try:
                hora = datetime.fromisoformat(d["begin"].replace("Z", "")).hour
                hora_str = str(hora).zfill(2)
                valores_por_hora[hora_str] += d.get("energyDelivered", 0)
            except KeyError as e:
                print(f"Documento inválido: campo {str(e)} ausente")
                continue

        horas = [f"{h}h" for h in valores_por_hora.keys()]
        valores = list(valores_por_hora.values())

        return jsonify({
            "labels": horas,
            "values": valores
        })

    except Exception as e:
        print(f"Erro interno: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/dados/consumo-por-carregador')
def consumo_por_carregador():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "data": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$toDate": "$begin"}
                            }
                        },
                        "idCarregador": "$evseId"
                    },
                    "totalEnergy": {"$sum": "$energyDelivered"},
                    "registos": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.data": 1}
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

        resultados = list(sessoes_carga.aggregate(pipeline))

        carregadores = {}
        for doc in resultados:
            if doc['idCarregador'] not in carregadores:
                carregadores[doc['idCarregador']] = []
            carregadores[doc['idCarregador']].append({
                'data': doc['data'],
                'energia': doc['energia']
            })

        return jsonify(carregadores)

    except Exception as e:
        print(f"Erro na rota /dados/consumo-por-carregador: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/dados/json')
def get_json_data():
    try:
        with open(JSON_FILE, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Execução Principal ====================
if __name__ == '__main__':
    from threading import Thread
    
    # Iniciar MQTT com configurações para HiveMQ Cloud
    setup_mqtt()
    
    # Iniciar atualização periódica em segundo plano
    Thread(target=atualizar_periodicamente, daemon=True).start()
    
    # Iniciar servidor Flask
    app.run(debug=True, use_reloader=False, port=5000)
