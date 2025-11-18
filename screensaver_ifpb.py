#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proteção de Tela Inteligente IFPB
Otimizado para sistemas Armbian (TV Box)
Com alarmes sonoros e integração MQTT
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import random
import threading
import time
from datetime import datetime
from pathlib import Path
import pygame
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Aviso: paho-mqtt não instalado. Funcionalidade MQTT desabilitada.")

# Configurações
DB_NAME = "config.db"
MP3_FOLDER = "mp3"
LOGO_FILE = "ifpb.png"
MQTT_BROKER = "localhost"  # Ajuste conforme necessário
MQTT_PORT = 1883
MQTT_TOPIC = "ifpb/sala101/mensagens"
ALARM_DURATION = 30  # segundos

class ScreensaverIFPB:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.logo_image = None
        self.logo_id = None
        self.logo_x = 0
        self.logo_y = 0
        self.logo_dx = 2  # velocidade horizontal
        self.logo_dy = 2  # velocidade vertical
        self.logo_width = 200
        self.logo_height = 200
        
        self.config_window = None
        self.horarios_listbox = None
        
        self.last_alarm_minute = None
        self.mqtt_client = None
        self.mqtt_connected = False
        self.message_display_id = None
        self.message_text_id = None
        
        # Inicializar pygame mixer
        pygame.mixer.init()
        
        # Criar estrutura de pastas
        self.setup_folders()
        
        # Inicializar banco de dados
        self.init_database()
        
        # Carregar logo
        self.load_logo()
        
        # Inicializar interface principal
        self.init_main_window()
        
        # Iniciar verificação de alarmes
        self.check_alarms()
        
        # Iniciar cliente MQTT
        if MQTT_AVAILABLE:
            self.init_mqtt()
        
        # Bind de teclas
        self.root.bind('<F2>', self.show_config_window)
        self.root.bind('<Escape>', self.on_escape)
        
        # Iniciar animação
        self.animate_logo()
    
    def setup_folders(self):
        """Cria as pastas necessárias se não existirem"""
        Path(MP3_FOLDER).mkdir(exist_ok=True)
    
    def init_database(self):
        """Inicializa o banco de dados SQLite"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS horarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hora TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def load_logo(self):
        """Carrega o logo do IFPB ou cria um placeholder"""
        if os.path.exists(LOGO_FILE):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_FILE)
                img = img.resize((self.logo_width, self.logo_height), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
            except ImportError:
                # Se PIL não estiver disponível, usar imagem simples
                self.logo_image = None
            except Exception as e:
                print(f"Erro ao carregar logo: {e}")
                self.logo_image = None
        else:
            self.logo_image = None
    
    def init_main_window(self):
        """Inicializa a janela principal (proteção de tela)"""
        self.root = tk.Tk()
        self.root.title("Proteção de Tela IFPB")
        
        # Configurar tela cheia sem bordas
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        self.root.overrideredirect(True)
        
        # Canvas para desenhar
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            cursor='none'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Posição inicial do logo (centro)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.logo_x = (screen_width - self.logo_width) // 2
        self.logo_y = (screen_height - self.logo_height) // 2
        
        # Desenhar logo inicial
        self.draw_logo()
    
    def draw_logo(self):
        """Desenha o logo na tela"""
        if self.logo_id:
            self.canvas.delete(self.logo_id)
        
        if self.logo_image:
            self.logo_id = self.canvas.create_image(
                self.logo_x + self.logo_width // 2,
                self.logo_y + self.logo_height // 2,
                image=self.logo_image
            )
        else:
            # Placeholder: retângulo com texto IFPB
            self.logo_id = self.canvas.create_rectangle(
                self.logo_x,
                self.logo_y,
                self.logo_x + self.logo_width,
                self.logo_y + self.logo_height,
                fill='#0066CC',
                outline='white',
                width=3
            )
            self.canvas.create_text(
                self.logo_x + self.logo_width // 2,
                self.logo_y + self.logo_height // 2,
                text="IFPB",
                font=('Arial', 48, 'bold'),
                fill='white'
            )
    
    def animate_logo(self):
        """Anima o logo pela tela (usando after() para eficiência)"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Atualizar posição
        self.logo_x += self.logo_dx
        self.logo_y += self.logo_dy
        
        # Verificar colisões com bordas
        if self.logo_x <= 0 or self.logo_x + self.logo_width >= screen_width:
            self.logo_dx = -self.logo_dx
            self.logo_x = max(0, min(self.logo_x, screen_width - self.logo_width))
        
        if self.logo_y <= 0 or self.logo_y + self.logo_height >= screen_height:
            self.logo_dy = -self.logo_dy
            self.logo_y = max(0, min(self.logo_y, screen_height - self.logo_height))
        
        # Redesenhar logo
        self.draw_logo()
        
        # Agendar próxima animação (30ms = ~33 FPS, leve para Armbian)
        self.root.after(30, self.animate_logo)
    
    def get_horarios(self):
        """Retorna lista de horários do banco"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT hora FROM horarios ORDER BY hora")
        horarios = [row[0] for row in cursor.fetchall()]
        conn.close()
        return horarios
    
    def check_alarms(self):
        """Verifica se é hora de tocar alarme"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_minute = now.strftime("%H:%M")
        
        # Evitar disparar duas vezes no mesmo minuto
        if current_minute == self.last_alarm_minute:
            self.root.after(60000, self.check_alarms)  # Verificar novamente em 1 minuto
            return
        
        horarios = self.get_horarios()
        
        if current_time in horarios:
            self.last_alarm_minute = current_minute
            self.play_random_mp3()
        
        # Agendar próxima verificação em 1 minuto
        self.root.after(60000, self.check_alarms)
    
    def play_random_mp3(self):
        """Toca um arquivo MP3 aleatório por 30 segundos"""
        mp3_files = list(Path(MP3_FOLDER).glob("*.mp3"))
        
        if not mp3_files:
            print("Nenhum arquivo MP3 encontrado na pasta mp3/")
            return
        
        # Escolher arquivo aleatório
        selected_file = random.choice(mp3_files)
        
        try:
            # Carregar e tocar
            pygame.mixer.music.load(str(selected_file))
            pygame.mixer.music.play()
            
            # Parar após 30 segundos
            self.root.after(ALARM_DURATION * 1000, pygame.mixer.music.stop)
            
            print(f"Tocando: {selected_file.name} por {ALARM_DURATION} segundos")
        except Exception as e:
            print(f"Erro ao tocar MP3: {e}")
    
    def show_config_window(self, event=None):
        """Mostra a janela de configuração de horários"""
        if self.config_window and self.config_window.winfo_exists():
            self.config_window.lift()
            return
        
        self.config_window = tk.Toplevel(self.root)
        self.config_window.title("Configuração de Horários")
        self.config_window.geometry("400x500")
        self.config_window.attributes('-topmost', True)
        self.config_window.configure(bg='#f0f0f0')
        
        # Frame principal
        main_frame = ttk.Frame(self.config_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(
            main_frame,
            text="Gerenciar Horários de Alarme",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=10)
        
        # Frame para adicionar horário
        add_frame = ttk.LabelFrame(main_frame, text="Adicionar Horário", padding="10")
        add_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(add_frame, text="Horário (HH:MM):").pack(anchor=tk.W)
        hora_entry = ttk.Entry(add_frame, width=10, font=('Arial', 12))
        hora_entry.pack(pady=5)
        
        def add_horario():
            hora = hora_entry.get().strip()
            if self.validate_hora(hora):
                self.insert_horario(hora)
                hora_entry.delete(0, tk.END)
                refresh_list()
            else:
                messagebox.showerror("Erro", "Formato inválido! Use HH:MM (ex: 08:30)")
        
        ttk.Button(add_frame, text="Adicionar", command=add_horario).pack(pady=5)
        
        # Frame para listar horários
        list_frame = ttk.LabelFrame(main_frame, text="Horários Cadastrados", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Listbox com scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.horarios_listbox = tk.Listbox(
            list_frame,
            font=('Arial', 11),
            yscrollcommand=scrollbar.set
        )
        self.horarios_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.horarios_listbox.yview)
        
        # Frame para botão excluir
        delete_frame = ttk.Frame(main_frame)
        delete_frame.pack(fill=tk.X, pady=10)
        
        def delete_selected():
            selection = self.horarios_listbox.curselection()
            if selection:
                hora = self.horarios_listbox.get(selection[0])
                self.delete_horario(hora)
                refresh_list()
            else:
                messagebox.showwarning("Aviso", "Selecione um horário para excluir")
        
        ttk.Button(delete_frame, text="Excluir Selecionado", command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        def close_config():
            self.config_window.destroy()
            self.config_window = None
        
        ttk.Button(delete_frame, text="Fechar", command=close_config).pack(side=tk.RIGHT, padx=5)
        
        def refresh_list():
            """Atualiza a lista de horários"""
            self.horarios_listbox.delete(0, tk.END)
            horarios = self.get_horarios()
            for hora in horarios:
                self.horarios_listbox.insert(tk.END, hora)
        
        refresh_list()
    
    def validate_hora(self, hora):
        """Valida formato HH:MM"""
        try:
            parts = hora.split(':')
            if len(parts) != 2:
                return False
            h, m = int(parts[0]), int(parts[1])
            return 0 <= h <= 23 and 0 <= m <= 59
        except:
            return False
    
    def insert_horario(self, hora):
        """Insere horário no banco"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Verificar se já existe
        cursor.execute("SELECT id FROM horarios WHERE hora = ?", (hora,))
        if cursor.fetchone():
            messagebox.showwarning("Aviso", "Este horário já está cadastrado!")
        else:
            cursor.execute("INSERT INTO horarios (hora) VALUES (?)", (hora,))
            conn.commit()
            messagebox.showinfo("Sucesso", f"Horário {hora} adicionado!")
        
        conn.close()
    
    def delete_horario(self, hora):
        """Remove horário do banco"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios WHERE hora = ?", (hora,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Sucesso", f"Horário {hora} removido!")
    
    def init_mqtt(self):
        """Inicializa cliente MQTT em thread separada"""
        if not MQTT_AVAILABLE:
            return
        
        def mqtt_thread():
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            try:
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
            except Exception as e:
                print(f"Erro ao conectar MQTT: {e}")
        
        mqtt_thread_obj = threading.Thread(target=mqtt_thread, daemon=True)
        mqtt_thread_obj.start()
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT"""
        if rc == 0:
            self.mqtt_connected = True
            client.subscribe(MQTT_TOPIC)
            print(f"Conectado ao MQTT broker. Inscrito em: {MQTT_TOPIC}")
        else:
            print(f"Falha na conexão MQTT. Código: {rc}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback de mensagem MQTT recebida"""
        try:
            message = msg.payload.decode('utf-8')
            print(f"Mensagem MQTT recebida: {message}")
            self.display_message(message)
        except Exception as e:
            print(f"Erro ao processar mensagem MQTT: {e}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Callback de desconexão MQTT"""
        self.mqtt_connected = False
        print("Desconectado do MQTT broker")
    
    def display_message(self, message):
        """Exibe mensagem MQTT na tela por alguns segundos"""
        # Remover mensagem anterior se existir
        if self.message_text_id:
            self.canvas.delete(self.message_text_id)
        if self.message_display_id:
            self.root.after_cancel(self.message_display_id)
        
        # Criar texto grande e centralizado
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        self.message_text_id = self.canvas.create_text(
            screen_width // 2,
            screen_height // 2,
            text=message,
            font=('Arial', 48, 'bold'),
            fill='yellow',
            justify=tk.CENTER,
            width=screen_width - 100
        )
        
        # Remover após 5 segundos
        self.message_display_id = self.root.after(5000, self.clear_message)
    
    def clear_message(self):
        """Remove a mensagem da tela"""
        if self.message_text_id:
            self.canvas.delete(self.message_text_id)
            self.message_text_id = None
        self.message_display_id = None
    
    def on_escape(self, event=None):
        """Fecha o programa ao pressionar Escape"""
        if messagebox.askyesno("Sair", "Deseja realmente sair?"):
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            pygame.mixer.quit()
            self.root.quit()
    
    def run(self):
        """Inicia o loop principal"""
        self.root.mainloop()


def main():
    """Função principal"""
    app = ScreensaverIFPB()
    app.run()


if __name__ == "__main__":
    main()

