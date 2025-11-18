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
import subprocess
from datetime import datetime
from pathlib import Path
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
MQTT_BROKER = "200.129.71.149"  # Ajuste conforme necessário
MQTT_PORT = 1883
MQTT_TOPIC = "ifpb/sala01/mensagens"
MQTT_USERNAME = "iot"
MQTT_PASSWORD = "123"
ALARM_DURATION = 30  # segundos

class ScreensaverIFPB:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.logo_image = None
        self.logo_ids = []  # Lista de IDs dos elementos do logo
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
        self.logo_visible = True  # Controla se o logo está visível
        self.animation_paused = False  # Controla se a animação está pausada
        self.mpg123_process = None  # Processo do mpg123 em execução
        
        # Criar estrutura de pastas
        self.setup_folders()
        
        # Inicializar banco de dados
        self.init_database()
        
        # Inicializar interface principal (deve ser antes de carregar logo)
        self.init_main_window()
        
        # Carregar logo (após criar a janela root)
        self.load_logo()
        
        # Desenhar logo inicial (após carregar)
        self.draw_logo()
        
        # Iniciar verificação de alarmes
        self.check_alarms()
        
        # Iniciar cliente MQTT
        if MQTT_AVAILABLE:
            self.init_mqtt()
        
        # Bind de teclas
        self.root.bind('<F2>', self.show_config_window)
        self.root.bind('<Escape>', self.on_escape)
        
        # Forçar tela cheia novamente após tudo estar carregado (garantia para Armbian)
        self.root.after(100, self.ensure_fullscreen)
        
        # Iniciar animação
        self.animate_logo()
    
    def ensure_fullscreen(self):
        """Garante que a janela está em tela cheia (útil para Armbian)"""
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Verificar se a janela está realmente em tela cheia
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()
            
            # Se não estiver em tela cheia, forçar novamente
            if current_width < screen_width or current_height < screen_height:
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")
                self.root.attributes('-fullscreen', True)
                self.root.update_idletasks()
        except Exception as e:
            print(f"Aviso ao verificar tela cheia: {e}")
    
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
                img = img.resize((self.logo_width + 100, self.logo_height + 100), Image.Resampling.LANCZOS)
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
        
        # Obter dimensões da tela antes de configurar
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Configurar fundo preto primeiro
        self.root.configure(bg='black')
        
        # Remover bordas e barra de título
        self.root.overrideredirect(True)
        
        # Configurar geometria para tela cheia (método alternativo para Armbian)
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Forçar tela cheia usando múltiplos métodos (compatibilidade Armbian)
        try:
            self.root.attributes('-fullscreen', True)
        except:
            pass
        
        try:
            # Método alternativo para Linux/Armbian
            self.root.wm_attributes('-fullscreen', True)
        except:
            pass
        
        # Sempre no topo
        try:
            self.root.attributes('-topmost', True)
        except:
            pass
        
        try:
            self.root.wm_attributes('-topmost', True)
        except:
            pass
        
        # Forçar atualização da janela
        self.root.update_idletasks()
        self.root.update()
        
        # Canvas para desenhar
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            cursor='none'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Forçar canvas a ocupar toda a tela
        self.canvas.config(width=screen_width, height=screen_height)
        
        # Posição inicial do logo (centro)
        self.logo_x = (screen_width - self.logo_width) // 2
        self.logo_y = (screen_height - self.logo_height) // 2
        
        # Forçar atualização final
        self.root.update_idletasks()
        self.root.update()
    
    def draw_logo(self):
        """Desenha o logo na tela"""
        # Deletar todos os elementos anteriores do logo
        for logo_id in self.logo_ids:
            self.canvas.delete(logo_id)
        self.logo_ids.clear()
        
        if self.logo_image:
            logo_id = self.canvas.create_image(
                self.logo_x + self.logo_width // 2,
                self.logo_y + self.logo_height // 2,
                image=self.logo_image
            )
            self.logo_ids.append(logo_id)
        else:
            # Placeholder: retângulo com texto IFPB
            rect_id = self.canvas.create_rectangle(
                self.logo_x,
                self.logo_y,
                self.logo_x + self.logo_width,
                self.logo_y + self.logo_height,
                fill='#0066CC',
                outline='white',
                width=3
            )
            text_id = self.canvas.create_text(
                self.logo_x + self.logo_width // 2,
                self.logo_y + self.logo_height // 2,
                text="IFPB",
                font=('Arial', 48, 'bold'),
                fill='white'
            )
            self.logo_ids.append(rect_id)
            self.logo_ids.append(text_id)
    
    def animate_logo(self):
        """Anima o logo pela tela (usando after() para eficiência)"""
        # Não animar se o logo estiver oculto
        if not self.logo_visible:
            self.root.after(30, self.animate_logo)
            return
        
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
    
    def hide_logo(self):
        """Oculta o logo da tela"""
        if self.logo_visible:
            self.logo_visible = False
            # Deletar todos os elementos do logo
            for logo_id in self.logo_ids:
                self.canvas.delete(logo_id)
            self.logo_ids.clear()
    
    def show_logo(self):
        """Mostra o logo na tela novamente"""
        if not self.logo_visible:
            self.logo_visible = True
            # Redesenhar o logo
            self.draw_logo()
    
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
    
    def stop_mp3(self):
        """Para a reprodução do MP3"""
        if self.mpg123_process:
            try:
                self.mpg123_process.terminate()
                self.mpg123_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.mpg123_process.kill()
            except Exception as e:
                print(f"Erro ao parar MP3: {e}")
            finally:
                self.mpg123_process = None
    
    def play_random_mp3(self):
        """Toca um arquivo MP3 aleatório por 30 segundos e exibe mensagem de mudança de aula"""
        mp3_files = list(Path(MP3_FOLDER).glob("*.mp3"))
        
        # Exibir mensagem de mudança de aula na tela
        now = datetime.now()
        hora_atual = now.strftime("%H:%M")
        mensagem = f"MUDANÇA DE AULA!\n\nHorário: {hora_atual}"
        # Exibir por 10 segundos (mais tempo que mensagens MQTT) com cor vermelha e fonte maior
        self.display_message(mensagem, duration=10000, color='red', font_size=64)
        
        if not mp3_files:
            print("Nenhum arquivo MP3 encontrado na pasta mp3/")
            return
        
        # Parar qualquer reprodução anterior
        self.stop_mp3()
        
        # Escolher arquivo aleatório
        selected_file = random.choice(mp3_files)
        
        try:
            # Tocar usando mpg123
            # -q = quiet mode (sem output)
            self.mpg123_process = subprocess.Popen(
                ['mpg123', '-q', str(selected_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Parar após 30 segundos
            self.root.after(ALARM_DURATION * 1000, self.stop_mp3)
            
            print(f"Tocando: {selected_file.name} por {ALARM_DURATION} segundos")
        except FileNotFoundError:
            print("Erro: mpg123 não encontrado. Instale com: sudo apt-get install mpg123")
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
        
        # Label de status (feedback visual)
        status_label = ttk.Label(add_frame, text="", foreground="green", font=('Arial', 9))
        status_label.pack(pady=2)
        
        def add_horario():
            hora = hora_entry.get().strip()
            if self.validate_hora(hora):
                if self.insert_horario(hora):
                    hora_entry.delete(0, tk.END)
                    hora_entry.focus_set()  # Volta o foco para o campo
                    refresh_list()
                    # Mostrar feedback visual de sucesso
                    status_label.config(text=f"✓ Horário {hora} adicionado!", foreground="green")
                    # Limpar mensagem após 2 segundos
                    self.config_window.after(2000, lambda: status_label.config(text=""))
                else:
                    status_label.config(text="", foreground="red")
            else:
                messagebox.showerror("Erro", "Formato inválido! Use HH:MM (ex: 08:30)")
                hora_entry.focus_set()
                status_label.config(text="", foreground="red")
        
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
        
        # Label de status para exclusão
        delete_status_label = ttk.Label(delete_frame, text="", foreground="red", font=('Arial', 9))
        delete_status_label.pack(side=tk.LEFT, padx=5)
        
        def delete_selected():
            selection = self.horarios_listbox.curselection()
            if selection:
                hora = self.horarios_listbox.get(selection[0])
                if self.delete_horario(hora):
                    refresh_list()
                    # Mostrar feedback visual de sucesso
                    delete_status_label.config(text=f"✓ Horário {hora} removido!", foreground="red")
                    # Limpar mensagem após 2 segundos
                    self.config_window.after(2000, lambda: delete_status_label.config(text=""))
            else:
                delete_status_label.config(text="Selecione um horário para excluir", foreground="orange")
                self.config_window.after(2000, lambda: delete_status_label.config(text=""))
        
        ttk.Button(delete_frame, text="Excluir Selecionado", command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        # Adicionar atalho: duplo clique para excluir
        def on_double_click(event):
            # Selecionar o item clicado
            widget = event.widget
            index = widget.nearest(event.y)
            if index >= 0:
                widget.selection_clear(0, tk.END)
                widget.selection_set(index)
                widget.activate(index)
                delete_selected()
        
        self.horarios_listbox.bind('<Double-Button-1>', on_double_click)
        
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
        """Insere horário no banco. Retorna True se inserido com sucesso, False caso contrário"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Verificar se já existe
        cursor.execute("SELECT id FROM horarios WHERE hora = ?", (hora,))
        if cursor.fetchone():
            messagebox.showwarning("Aviso", "Este horário já está cadastrado!")
            conn.close()
            return False
        else:
            cursor.execute("INSERT INTO horarios (hora) VALUES (?)", (hora,))
            conn.commit()
            conn.close()
            # Mensagem mais discreta ou sem messagebox para não interromper o fluxo
            # messagebox.showinfo("Sucesso", f"Horário {hora} adicionado!")
            return True
    
    def delete_horario(self, hora):
        """Remove horário do banco. Retorna True se removido com sucesso"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios WHERE hora = ?", (hora,))
        conn.commit()
        conn.close()
        return True
    
    def init_mqtt(self):
        """Inicializa cliente MQTT em thread separada"""
        if not MQTT_AVAILABLE:
            return
        
        def mqtt_thread():
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            # Configurar autenticação
            self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            
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
    
    def display_message(self, message, duration=5000, color='yellow', font_size=48):
        """Exibe mensagem na tela por alguns segundos"""
        # Remover mensagem anterior se existir
        if self.message_text_id:
            self.canvas.delete(self.message_text_id)
        if self.message_display_id:
            self.root.after_cancel(self.message_display_id)
        
        # Ocultar logo quando mensagem aparecer
        self.hide_logo()
        
        # Criar texto grande e centralizado
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        self.message_text_id = self.canvas.create_text(
            screen_width // 2,
            screen_height // 2,
            text=message,
            font=('Arial', font_size, 'bold'),
            fill=color,
            justify=tk.CENTER,
            width=screen_width - 100
        )
        
        # Remover após o tempo especificado
        self.message_display_id = self.root.after(duration, self.clear_message)
    
    def clear_message(self):
        """Remove a mensagem da tela e mostra o logo novamente"""
        if self.message_text_id:
            self.canvas.delete(self.message_text_id)
            self.message_text_id = None
        self.message_display_id = None
        
        # Mostrar logo novamente quando mensagem desaparecer
        self.show_logo()
    
    def on_escape(self, event=None):
        """Fecha o programa ao pressionar Escape"""
        if messagebox.askyesno("Sair", "Deseja realmente sair?"):
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            # Parar qualquer reprodução de MP3
            self.stop_mp3()
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

