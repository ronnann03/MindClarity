# 🚀 YU v2.0.0 - GUÍA DE INSTALACIÓN PASO A PASO

## ⚡ Instalación Rápida (Recomendado)

### Opción 1: Automática (Más fácil)

1. **Haz doble clic en `SETUP.bat`**
   - Se instalarán automáticamente todas las dependencias
   - Se creará el archivo `.env` con valores por defecto
   - ¡Listo!

### Opción 2: Manual

1. **Abre PowerShell o CMD en esta carpeta**
2. **Copia y pega:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

---

## 🎮 Ahora, ¡Inicia YU!

### GUI (Interfaz Gráfica) - RECOMENDADO PARA PRINCIPIANTES

**Opción A: Doble clic rápido**
- Haz doble clic en `START_YU_GUI.bat`
- Se abrirá YU automáticamente

**Opción B: Por terminal**
```bash
python main.py
```

### API REST (Para Acceso Remoto)

**Opción A: Doble clic rápido**
- Haz doble clic en `START_YU_API.bat`
- Se abrirá en: http://localhost:8000

**Opción B: Por terminal**
```bash
python -m uvicorn api.server:app --reload
```

---

## 📋 Primera vez: Crear Perfil

Cuando inicies YU por primera vez:

1. Se abrirá un **Selector de Perfil**
2. Haz clic en **"+ Crear nuevo perfil"**
3. Rellena:
   - Nombre: Tu nombre (ej: "Ronaldo")
   - Asistente: Nombre del asistente (ej: "YU")
   - Idioma: "auto" (detecta automáticamente)
4. Haz clic en **"Crear"**
5. Selecciona tu perfil y la pantalla
6. ¡Haz clic en "Continuar"!

---

## 🎤 Primeros Comandos

Una vez YU esté abierto, prueba:

```
"¿Hola, cómo estás?"          → YU te responde
"¿Qué hora es?"               → Hora del sistema
"Sube el volumen a 70"        → Control de PC
"Abre Chrome"                 → Abre navegador
"Busca cuál es la capital de Francia"  → Búsqueda web
```

---

## 🔑 APIs Opcionales (Para Funcionalidades Extra)

### Para usar CUALQUIERA de estas, necesitas editar `.env`

**Recomendadas (Totalmente opcionales):**

1. **OpenAI** (para mejor IA)
   - Obtén clave: https://platform.openai.com/api-keys
   - Edita `.env` → `OPENAI_API_KEY=sk-...`

2. **Spotify** (para reproducción)
   - Obtén credenciales: https://developer.spotify.com
   - Edita `.env` → `SPOTIFY_CLIENT_ID=...` y `SPOTIFY_CLIENT_SECRET=...`

3. **Discord** (para enviar mensajes)
   - Crea bot: https://discord.com/developers
   - Edita `.env` → `DISCORD_WEBHOOK_URL=...`

4. **Telegram** (para mensajes/fotos)
   - Crea bot con @BotFather
   - Edita `.env` → `TELEGRAM_BOT_TOKEN=...`

5. **Home Assistant** (para control IoT)
   - URL local: `http://homeassistant.local:8123`
   - Edita `.env` → `HOMEASSISTANT_URL=...` y `HOMEASSISTANT_TOKEN=...`

**Sin ninguna API key, YU funciona 100% offline con Ollama local.**

---

## 🐛 Solucionar Problemas

### "Python no se encuentra"
- Instala Python 3.12+ desde: https://www.python.org
- Marca "Add Python to PATH" durante la instalación

### "No puedo hablar (micrófono no funciona)"
- Verifica que has permitido micrófono en Windows
- Settings → Privacy → Microphone → Permite a YU

### "No escucha mi voz"
- Di **"YU"** claramente para activar escucha
- O escribe directamente en el cuadro de texto

### "Error instalando dependencias"
- Abre PowerShell como **Administrador**
- Ejecuta: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### "Quiero usar IA mejorada (OpenAI)"
- Edita `.env` y añade tu `OPENAI_API_KEY`
- Si no lo haces, YU usa Ollama local

---

## 📁 Estructura de Archivos

```
Yu IA/
├── main.py                    ← Inicia GUI
├── api/
│   └── server.py             ← Inicia API REST
├── SETUP.bat                 ← Instalación automática
├── START_YU_GUI.bat        ← Inicia GUI
├── START_YU_API.bat        ← Inicia API
├── .env                      ← TUS CONFIGURACIONES (editar)
├── .env.example              ← Template de configuración
├── requirements.txt          ← Dependencias
├── README.md                 ← Documentación completa
├── QUICKSTART.md             ← Guía rápida
└── CHANGELOG.md              ← Historial de cambios
```

---

## 💡 Consejos

✅ **Haz:** Prueba comandos simples primero
✅ **Haz:** Mantén `.env` actualizado con tus claves
✅ **Haz:** Revisa `logs/` si algo falla
✅ **Haz:** Di "YU" claramente para activar

❌ **No hagas:** Deletrear palabras
❌ **No hagas:** Cambiar rutas de archivos
❌ **No hagas:** Ejecutar múltiples instancias

---

## 🎓 Próximos Pasos

1. **Explora comandos**: Prueba diferentes cosas
2. **Personaliza**: Añade APIs en `.env` según necesites
3. **Integra**: Conecta Discord, Telegram, etc.
4. **Automatiza**: Crea perfiles para diferentes usos

---

## 📞 Ayuda

- **Problema técnico**: Revisa `logs/` para ver detalles
- **Preguntas**: Consulta `README.md` o `QUICKSTART.md`
- **API keys**: Cada integración tiene instrucciones en `.env`

---

## 🎉 ¡LISTO!

Ya está todo configurado. Solo:

1. Haz doble clic en `SETUP.bat` (si aún no lo hiciste)
2. Haz doble clic en `START_YU_GUI.bat`
3. ¡Disfruta!

**¡YU está listo para usar! 🚀**
