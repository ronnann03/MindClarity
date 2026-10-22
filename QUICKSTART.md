# 🚀 YU - Guía Rápida de Inicio

## Instalación Rápida

```bash
# 1. Clonar/descargar el proyecto
cd "Yu IA"

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Configuración Inicial

### 1. Variables de Entorno (`.env`)

```bash
# Copiar template
copy .env.example .env

# Editar .env con tus claves
```

**Claves recomendadas:**

```env
# OpenAI (proveedor principal)
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o

# Gemini (fallback si OpenAI falla o no hay OPENAI_API_KEY)
GEMINI_API_KEY=...
GEMINI_MODEL_NAME=gemini-3.6-flash

# Voz
ELEVENLABS_API_KEY=...  # Opcional, fallback a Piper offline
VOICE_ID=...

# Integraciones
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
DISCORD_WEBHOOK_URL=...
TELEGRAM_BOT_TOKEN=...
SLACK_BOT_TOKEN=...
HOMEASSISTANT_URL=http://homeassistant.local:8123
HOMEASSISTANT_TOKEN=...

# Base de datos (opcional)
SUPABASE_URL=...
SUPABASE_KEY=...
```

## Uso

```bash
python main.py
```

Esto arranca en un solo proceso el pipeline de voz (wake word + micrófono) y
la interfaz web + API REST + WebSocket:

- **Web**: http://localhost:8000 (elige/crea tu perfil, chatea por texto o voz)
- **Documentación**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/stream

Para acceder desde otro dispositivo de la red, usa la IP local de la PC
donde corre YU en vez de `localhost`.

### Ejemplos de Comandos

```
"¿Qué tiempo hace?"                           → Clima
"Abre Spotify"                                → Office + Spotify
"Reproduce Bohemian Rhapsody"                 → Spotify
"Envía un mensaje a Discord"                  → Discord
"Enciende las luces de la sala"               → Home Assistant
"Sube un archivo a Google Drive"              → Google Drive
"Registra un gasto de 50 en comida"          → Finanzas
"¿Cuál es el tipo de cambio euro-dólar?"     → Finanzas
"Busca recetas de pasta"                      → Web (Búsqueda)
"Envía un mensaje a mamá por WhatsApp"       → WhatsApp
"Abre un documento de Word"                   → Office
"Crea una presentación PowerPoint"            → Office
"Notifica en Slack que terminé el proyecto"  → Slack
"Envía una foto a Telegram"                   → Telegram
```

## Características Disponibles

### 🎙️ Voz
- **STT**: Faster Whisper (local o cloud)
- **TTS**: ElevenLabs (cloud) → Piper (local, ligero)
- **Wake Word**: OpenWakeWord o energía+Whisper

### 🧠 Agentes (13)
1. Sistema (apps, ventanas, archivos, PC)
2. Investigación (búsqueda web)
3. Email (Gmail)
4. Calendario (Google Calendar)
5. Productividad (tareas, recordatorios)
6. **Finanzas** (conversiones, gastos)
7. **Hogar Inteligente** (IoT, luces, termostato)
8. **Web** (navegador, WhatsApp)
9. **Office + Spotify** (Word, Excel, PowerPoint, Outlook, Spotify)
10. **Integraciones** (Discord, Telegram, Slack, Home Assistant, Google Drive)
11. Sistema base

### 🔌 Integraciones (11)
- YouTube, Clima
- **Navegador web** (abrir URLs, búsquedas)
- **WhatsApp** (enviar mensajes)
- **Spotify** (reproducción, control)
- **Microsoft Office** (Word, Excel, PowerPoint, Outlook)
- **Discord** (mensajes, notificaciones)
- **Telegram** (mensajes, fotos)
- **Slack** (mensajes, notificaciones)
- **Home Assistant** (control IoT)
- **Google Drive** (upload, download)

### 📊 Características Avanzadas

| Feature | Descripción |
|---------|-------------|
| **Perfiles de Usuario** | Multi-usuario, elegidos desde la web |
| **Interfaz web** | Accesible desde cualquier dispositivo de la red |
| **API REST** | HTTP + WebSocket para acceso remoto |
| **Auditoría** | Registro de todas las acciones (JSONL) |
| **Sistema de Plugins** | Extensibilidad mediante plugins dinámicos |
| **TTS Offline** | Piper (sin internet) |
| **Fallback Automático** | IA: OpenAI→Gemini, TTS: ElevenLabs→Piper |

## Archivos Importantes

```
├── main.py                      # Punto de entrada (agentes + voz + servidor web)
├── api/server.py                # Backend FastAPI (API REST + WebSocket)
├── ui_web/index.html            # Interfaz web
├── config/
│   ├── settings.py            # Configuración (Pydantic)
│   └── profiles.py            # Gestión de perfiles
├── core/
│   ├── logger.py              # Logging
│   ├── audit.py               # Auditoría
│   ├── plugins.py             # Sistema de plugins
│   ├── orchestrator.py        # Orquestador de agentes
│   └── permissions.py         # Control de permisos
├── agents/                     # 11 agentes especializados
├── integrations/               # 11 integraciones
├── voice/                      # Pipeline de voz
├── logs/                       # Logs y auditoría
├── memory/                     # Memoria y embeddings
└── database/                   # Supabase (opcional)
```

## Troubleshooting

### "No se puede abrir el micrófono"
- Verifica que sounddevice está instalado: `pip install sounddevice`
- Comprueba permisos de micrófono en Windows

### "Error en ElevenLabs TTS"
- YU automáticamente usa Piper (offline)
- Para forzar offline: no configures `ELEVENLABS_API_KEY`

### "Home Assistant no conecta"
- Verifica que `HOMEASSISTANT_URL` es correcto
- Genera token largo en Home Assistant → Settings → Users

### "Discord/Telegram no envía mensajes"
- Comprueba que el token/webhook está en `.env`
- Verifica permisos del bot en las plataformas

## Next Steps

1. **Mejoras de IA** - Sentimientos, contexto a largo plazo
2. **Empaquetado .exe** - Actualizar `yu.spec` para el nuevo entry point web
3. **Más agentes** - Google Sheets, Notion, etc.

## Soporte

Para dudas o problemas:
- Revisa `logs/` para ver qué pasó
- Consulta el README.md para información detallada
- Verifica tu `.env` y permisos

---

**¡YU está listo! Enjoy! 🚀**
