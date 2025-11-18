# Proteção de Tela Inteligente IFPB

Proteção de tela inteligente com alarmes sonoros e integração MQTT, otimizada para sistemas Armbian (TV Box).

## Características

- ✅ Proteção de tela com logo IFPB animado
- ✅ Sistema de alarmes sonoros baseado em horários
- ✅ Interface gráfica para gerenciar horários
- ✅ Integração MQTT para receber mensagens
- ✅ Otimizado para baixo consumo de CPU (ideal para Armbian)

## Requisitos

- Python 3.6 ou superior
- Tkinter (geralmente incluído no Python)
- mpg123 (player de áudio - instale com: `sudo apt-get install mpg123`)
- Bibliotecas Python (ver requirements.txt)

## Instalação

1. Instale o mpg123 (player de áudio):
```bash
sudo apt-get install mpg123
```

2. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

3. Coloque o logo do IFPB como `ifpb.png` na pasta do projeto (opcional - será criado um placeholder se não existir)

4. Coloque arquivos MP3 na pasta `mp3/` (a pasta será criada automaticamente se não existir)

## Uso

Execute o programa:
```bash
python screensaver_ifpb.py
```

### Controles

- **F2**: Abre a tela de configuração de horários
- **ESC**: Fecha o programa (com confirmação)

### Configuração de Horários

1. Pressione **F2** para abrir a tela de configuração
2. Digite um horário no formato **HH:MM** (ex: 08:30)
3. Clique em **Adicionar**
4. Para excluir, selecione um horário na lista e clique em **Excluir Selecionado**

### Alarmes

O programa verifica automaticamente a cada minuto se é hora de tocar um alarme. Quando o horário atual coincide com um horário cadastrado:
- Um arquivo MP3 aleatório da pasta `mp3/` é tocado
- O som toca por 30 segundos
- O alarme não dispara duas vezes no mesmo minuto

### MQTT

O programa se conecta automaticamente ao broker MQTT configurado e se inscreve no tópico:
```
ifpb/sala101/mensagens
```

Quando uma mensagem é recebida, ela é exibida na tela por 5 segundos, sem interromper a animação do logo.

**Configuração do MQTT**: Edite as variáveis no início do arquivo `screensaver_ifpb.py`:
- `MQTT_BROKER`: Endereço do broker (padrão: "localhost")
- `MQTT_PORT`: Porta do broker (padrão: 1883)
- `MQTT_TOPIC`: Tópico para se inscrever (padrão: "ifpb/sala101/mensagens")

## Estrutura de Arquivos

```
.
├── screensaver_ifpb.py    # Programa principal
├── config.db              # Banco SQLite (criado automaticamente)
├── mp3/                   # Pasta com arquivos MP3 (criada automaticamente)
├── ifpb.png               # Logo do IFPB (opcional)
├── requirements.txt       # Dependências Python
└── README.md              # Este arquivo
```

## Otimizações para Armbian

- Uso de `after()` em vez de loops pesados
- Animação leve (~33 FPS)
- Thread única para MQTT (não bloqueia interface)
- Verificação de alarmes a cada minuto (não polling constante)
- Recursos gráficos leves

## Notas

- Se o arquivo `ifpb.png` não existir, será exibido um placeholder com o texto "IFPB"
- Se a pasta `mp3/` estiver vazia, os alarmes não tocarão (mas não causarão erro)
- O banco de dados SQLite é criado automaticamente na primeira execução
- A biblioteca `paho-mqtt` é opcional - o programa funciona sem ela, mas sem funcionalidade MQTT

## Solução de Problemas

**Problema**: MQTT não conecta
- Verifique se o broker está rodando
- Verifique as configurações de `MQTT_BROKER` e `MQTT_PORT`
- Verifique se a biblioteca `paho-mqtt` está instalada

**Problema**: MP3 não toca
- Verifique se há arquivos `.mp3` na pasta `mp3/`
- Verifique se o sistema tem suporte a áudio
- Verifique se o `mpg123` está instalado: `which mpg123` ou `mpg123 --version`

**Problema**: Logo não aparece
- Coloque o arquivo `ifpb.png` na pasta do projeto
- Ou instale a biblioteca `Pillow` para melhor suporte a imagens

