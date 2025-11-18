#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script auxiliar para testar o envio de mensagens MQTT
Útil para verificar se a integração MQTT está funcionando
"""

import paho.mqtt.client as mqtt
import sys

MQTT_BROKER = "200.129.71.149"
MQTT_PORT = 1883
MQTT_TOPIC = "ifpb/sala01/mensagens"
MQTT_USERNAME = "iot"
MQTT_PASSWORD = "123"
def main():
    if len(sys.argv) < 2:
        print("Uso: python test_mqtt.py <mensagem>")
        print("Exemplo: python test_mqtt.py 'Aula de Matemática começou!'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    try:
        print(f"Conectando ao broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(MQTT_TOPIC)
        
        print(f"Enviando mensagem para o tópico '{MQTT_TOPIC}'...")
        client.publish(MQTT_TOPIC, message)
        
        print(f"✓ Mensagem enviada: '{message}'")
        client.disconnect()
        
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

