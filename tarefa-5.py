import smbus2 # Biblioteca para I2C
import time # Biblioteca para delays
import json # Biblioteca para JSON
import socket # Biblioteca para obter IP
from datetime import datetime # Biblioteca para data e hora
from paho.mqtt import client as mqtt # Biblioteca MQTT

# Configurações do desafio 
DESAFIO = "03"
NOME = "matheus"
SOBRENOME = "dionisio"
DEVICE = "labrador_32b_03_matheus_dionisio"

# Configurações MQTT
BROKER = "mqtt.iot.natal.br"
PORT = 1883
USER = f"desafio{DESAFIO}"
PASSWORD = f"desafio{DESAFIO}.laica"

TOPIC = f"ha/desafio{DESAFIO}/{NOME}.{SOBRENOME}/gy_33"

#  Configurações do sensor GY-33 (TCS34725) 
I2C_BUS = 2 # Bus I2C (2 para Labrador)
GY33_ADDR = 0x29 # Endereço I2C do GY-33

# Inicializa I2C 
try:
    i2c = smbus2.SMBus(I2C_BUS) # Cria instância do bus I2C
    print("I2C inicializado no bus 2") # Confirma inicialização
except Exception as e: # Trata erro de inicialização
    print(f"Erro ao inicializar I2C: {e}") # Exibe erro
    exit(1) # Encerra programa

# Funções para ler e escrever registros do sensor
def write_reg(reg, value):
    i2c.write_byte_data(GY33_ADDR, 0x80 | reg, value)

# Função para ler palavra (2 bytes) do sensor
def read_word(reg):
    low = i2c.read_byte_data(GY33_ADDR, 0x80 | reg)
    high = i2c.read_byte_data(GY33_ADDR, 0x80 | (reg + 1))
    return (high << 8) | low

# Inicializa sensor
try:
    print("Inicializando sensor GY-33...")
    write_reg(0x00, 0x03)  # Power ON
    time.sleep(0.1)  
    write_reg(0x01, 0xEB)  # Ativa RGBC com ganho 4x 
    time.sleep(0.1)
    write_reg(0x0F, 0x01)  # Configura ganho
    time.sleep(0.1)
    print("Sensor GY-33 inicializado") # Confirma inicialização
except Exception as e:
    print(f"Erro na inicialização do sensor: {e}")
    exit(1)

# Função para detectar cor baseada em valores absolutos
def detect_color(r, g, b): 
    """Detecta as 5 cores obrigatórias baseada em valores absolutos"""
    
    # Amarelo 
    if r > 400 and g > 400 and b < 500:
        return "Amarelo"
    # Vermelho
    elif r >= 300 and g < 300 and b < 300:
        return "Vermelho"
    # Verde
    elif g > 400 and r < 300 and b < 300:
        return "Verde"
    # Azul
    elif b >= 250 and r < 300 and g < 300:
        return "Azul"
    # Preto
    elif r < 100 and g < 100 and b < 100:
        return "Preto"
    
    return "Indefinido"

# Função para obter IP da placa
def get_ip():
    """Obtém o IP real da placa na rede"""
    try:
        import subprocess
        result = subprocess.check_output(["hostname", "-I"]).decode().strip()
        return result.split()[0] if result else "0.0.0.0"
    except:
        return "0.0.0.0"

#  MQTT 
cli = mqtt.Client() # Cria cliente MQTT
cli.username_pw_set(USER, PASSWORD) # Configura usuário e senha

try:
    cli.connect(BROKER, PORT, 60) # Conecta ao broker
    print(f"Conectado ao broker MQTT: {BROKER}") # Confirma conexão
except Exception as e:
    print(f"Erro ao conectar no broker: {e}")
    exit(1)

cli.loop_start() # Inicia loop de rede MQTT

print("Iniciando sensor e MQTT...")
print(f"Publicando em: {TOPIC}")
print("Cores obrigatórias: Preto, Vermelho, Verde, Azul, Amarelo")
print("Leituras a cada 10 segundos")
print("=" * 60)

# Loop principal
while True:
    try:
        # Lê dados do sensor
        c = read_word(0x14)
        r = read_word(0x16)
        g = read_word(0x18)
        b = read_word(0x1A)

        # Detecta a cor
        cor = detect_color(r, g, b)

        # Prepara mensagem JSON
        msg = {
            "team": f"desafio{DESAFIO}",
            "device": DEVICE,
            "ip": get_ip(),
            "ssid": "TP-Link_D034",
            "sensor": "GY-33 (TCS34725)",
            "data": {
                "rgb": {"r": r, "g": g, "b": b},
                "gy33_luz": c,
                "cor": cor
            },
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }

        j = json.dumps(msg)
        
        # Exibe no console
        print(f"RGB: R={r:4d}, G={g:4d}, B={b:4d}, Clear={c:4d}")
        print(f"Cor detectada: {cor}")
        print(f"MQTT >> {j}")
        print("-" * 60)
        
        # Publica via MQTT (sem retain)
        cli.publish(TOPIC, j, qos=0, retain=False)
        
        time.sleep(10)
        
    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(5)