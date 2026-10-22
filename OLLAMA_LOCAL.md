# YU con Ollama local

Configurado el 16 de octubre de 2026.

- Motor instalado: Ollama 0.40.5, instalador oficial con firma digital válida de Ollama Inc.
- Modelo descargado: `qwen2.5:3b` (aproximadamente 1.9 GB).
- GPU comprobada: RTX 3050 Laptop, modelo ejecutándose 100 % en GPU.
- API local de Ollama: `http://127.0.0.1:11434`.
- Interfaz YU: `http://localhost:8000`.
- Proveedor de IA: `AI_PROVIDER=ollama`; sin fallback a OpenAI/Gemini.
- Voz: `TTS_PROVIDER=piper`; no utiliza ElevenLabs.
- Historial: contexto de sesión en memoria. Los embeddings de OpenAI y la memoria semántica de Supabase están desactivados en este modo. No se añadió persistencia local en esta integración.

## Arranque manual

Desde PowerShell, en la carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_YU_LOCAL.ps1
```

El script inicia Ollama en segundo plano si es necesario, verifica que esté disponible el modelo y ejecuta YU. Usa Python y las dependencias ya instaladas en el equipo. Evita instancias duplicadas. Con `-Supervise`, comprueba el proceso cada 30 segundos y vuelve a iniciarlo si termina.

## Inicio automático y saludos

`CONFIGURAR_INICIO_YU.ps1` crea `start_yu.bat` en el Escritorio real de Windows y registra `YU_Assistant` en `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. El registro ejecuta el supervisor de forma oculta al iniciar sesión, con la ruta completa del Python instalado. Se usa Windows nativo y Ollama; WSL no es necesario. Se puede ejecutar nuevamente el configurador para actualizar las rutas.

Para desactivar futuros inicios automáticos:

```powershell
Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name YU_Assistant
```

Esto no detiene el supervisor ya activo. Para detenerlo en la sesión actual, hay que cerrar primero el proceso de PowerShell correspondiente a `START_YU_LOCAL.ps1 -Supervise` y luego el proceso de YU; de lo contrario se relanzará.

Los saludos usan la hora de Lima: buenos días de 05:00 a 11:59, buenas tardes de 12:00 a 19:59 y buenas noches el resto del día. Se añaden al primer contacto conversacional, al cambiar de día o después de cuatro horas sin conversar. No se anteponen a cada respuesta ni a los resultados de acciones. La memoria, la web y la voz reciben el mismo texto final. Existe una copia previa del orquestador en `core/orchestrator.py.backup`.

El inicio automático se produce al iniciar sesión; la computadora debe permanecer encendida y sin suspensión para que YU pueda responder.

## Validación realizada

- Humanización: 27 pruebas de saludos y pipeline de voz aprobadas; comprobados los límites horarios, hora de Lima, ausencia de saludos duplicados y texto final guardado en memoria.
- Prueba real aislada con Ollama: primer turno con «Buenas tardes» y segundo sin repetir el saludo.
- Inicio automático registrado y leído de vuelta; el reinicio por cierre del proceso y la prevención de duplicados se comprobaron en la sesión actual. No se reinició Windows para probar un nuevo inicio de sesión.

- Pruebas de integración Ollama, JSON validado, streaming, errores de conexión/modelo y ausencia de llamadas de nube.
- Pruebas existentes de planificador, agentes y pipeline de voz aprobadas en ejecuciones dirigidas.
- Prueba adicional del contexto local sin embeddings aprobada.
- Prueba de selección de Piper con una clave de ElevenLabs presente aprobada.
- Conversación real por POST `/api/command`: «YU funciona con IA local».
- Clasificación real de «Abre la calculadora»: generó `app_launcher.open_app`; no se ejecutó esa acción.
- Dos turnos consecutivos recordaron correctamente un dato de prueba en 3.53 y 4.63 segundos con el modelo cargado. Son mediciones puntuales, no una garantía de rendimiento.
- La primera carga tardó considerablemente más. El modelo se mantiene cargado durante 30 minutos tras cada petición.

El funcionamiento local requiere la computadora encendida y recursos disponibles. Las integraciones de internet conservan sus requisitos y limitaciones anteriores. Ollama no corrige por sí solo las fallas de confirmación, persistencia de tareas o integraciones simuladas documentadas en DIAGNOSTICO_YU.md.
