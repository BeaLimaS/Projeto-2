#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

const char* ssid = "Bea Lima";
const char* password = "123456789";
const char* serverUrl = "http://192.168.1.100:5000/enviar-rfid";  // IP do teu PC

// Configuração do NTP
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;       // Ajusta conforme teu fuso horário
const int daylightOffset_sec = 3600; // Ex: +1h de verão

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("A ligar ao WiFi...");
  }

  Serial.println("WiFi ligado!");

  // Sincronizar data/hora com NTP
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  // Esperar sincronização
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Erro ao obter hora!");
  }
}

void loop() {
  // Gerar valor aleatório (entre 0 e 100)
  int valor = random(0, 101);

  // Obter data e hora atual
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Erro ao obter hora!");
    delay(1000);
    return;
  }

  char horaFormatada[25];
  strftime(horaFormatada, sizeof(horaFormatada), "%Y-%m-%d %H:%M:%S", &timeinfo);

  // Preparar JSON
  String json = "{\"codigo\":\"leitura_teste\", \"data_hora\":\"" + String(horaFormatada) + "\", \"valor\":" + String(valor) + "}";

  // Enviar HTTP POST
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(json);

  Serial.print("Enviado: ");
  Serial.println(json);
  Serial.print("Resposta: ");
  Serial.println(httpResponseCode);

  http.end();

  delay(5000);  // Esperar 5 segundos antes de nova leitura
}
