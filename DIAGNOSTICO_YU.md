# Diagnóstico de YU — 16 de octubre de 2026

Revisión del código, registros de arranque y una petición real e inocua a la API local. No se ejecutaron acciones de archivos, mensajes, correo ni control del equipo. Las capacidades descritas como implementadas no equivalen a una validación de extremo a extremo.

## Fallas confirmadas en ejecución

1. **OpenAI sin saldo.** La petición de conversación devolvió errores 429 `insufficient_quota` / `credit_balance_exhausted` para clasificación, conversación y embeddings.
2. **Gemini no puede validar el esquema de intención actual.** El SDK rechaza `additionalProperties` al recibir el esquema de Intent, que contiene diccionarios abiertos. La clasificación termina como UNKNOWN. En la misma prueba, el chat de respaldo devolvió además 503 por alta demanda; ese segundo error puede ser temporal.
3. **La API comunica éxito ante un fallo.** POST `/api/command` devolvió `success: true` con el mensaje «Lo siento, he tenido un problema al procesar la respuesta». El campo se fija a True sin propagar el resultado real.
4. **Lista de agentes vacía.** GET `/api/agents` devuelve `[]`: consulta `orchestrator._executors`, pero el registro está en `orchestrator.engine._registry`.
5. **Integraciones desconectadas.** Los registros confirman falta de configuración para Supabase, Discord, Google Drive, Home Assistant, Slack, Telegram y Spotify; WhatsApp indica dependencia ausente.

## Defectos encontrados por inspección

- **Bloqueo de confirmación por WebSocket:** el receptor espera a `process_text_input`; si este espera autorización, el mismo receptor no vuelve a leer `confirmation_response`. Una segunda conexión podría resolverla, pero la conexión solicitante queda bloqueada. Tampoco hay plazo ni cancelación automática al desconectar.
- **Operaciones fallidas marcadas como completadas:** DecisionEngine considera éxito cualquier retorno sin excepción, incluso `AgentResult(success=False)`.
- **Tareas que aparentan guardarse:** Supabase desconectado devuelve los datos recibidos en insert/update sin persistirlos; ProductivityAgent anuncia creación o finalización. Al listar devuelve vacío. Guardar `due_at` tampoco implementa una alarma que avise al vencer.
- **Funciones sin ruta desde lenguaje natural:** el enum de intenciones y Planner no tienen rutas para los agentes de finanzas, web/WhatsApp, Office/Spotify, hogar inteligente ni integraciones, aunque main los registre.
- **WhatsApp simulado:** envío solo escribe un log; lectura y chats retornan datos de ejemplo. Instalar la dependencia no completa esta integración.
- **Hogar inteligente simulado:** SmartHomeAgent cambia un diccionario local de dispositivos; no llama a Home Assistant. Existe otro controlador HTTP, pero esta implementación no lo usa.
- **YouTube no garantiza reproducción:** abre resultados de búsqueda; `play_music` afirma estar reproduciendo aunque solo abrió esa página.
- **Búsqueda limitada:** usa respuestas instantáneas de DuckDuckGo; cuando no encuentra datos consulta al modelo sin avisar claramente que dejó de usar información web.
- **Texto interpolado como HTML:** transcripciones y nombres de perfil se insertan mediante innerHTML. Deben renderizarse como texto para evitar interpretar marcado introducido por el usuario.
- **Exposición de control del PC:** servidor en `0.0.0.0`, CORS abierto y endpoints/WebSocket sin autenticación. La accesibilidad efectiva desde otros equipos depende de la red y del firewall.

## Qué puede hacer según la implementación

| Área | Implementación y estado |
|---|---|
| Conversación ES/EN | Historial de sesión, personalidad y proveedores OpenAI/Gemini. La prueba real falló por los problemas anteriores. |
| Voz | Whisper medium se cargó y produjo transcripciones; Piper cargó una voz española. No se verificó precisión ni reproducción audible. Hay reconocimiento adicional en el navegador. |
| Windows | Rutas para abrir/cerrar aplicaciones, listar procesos, controlar ventanas, volumen, brillo, capturas, teclado, ratón y bloqueo. Dependen de permisos, hardware y librerías. No ejecutadas durante la auditoría. |
| Archivos | Crear, listar, buscar, copiar, mover y borrar; planificador con confirmaciones para acciones de riesgo. El bloqueo de confirmación afecta ese flujo. |
| Automatización | Organización de descargas, renombrado por lotes, accesos directos y tareas de Windows. No probadas sobre archivos reales. |
| YouTube | Abrir YouTube y sus resultados de búsqueda de música/vídeo. |
| Clima e investigación | Controladores HTTP y resumen por IA; dependen de red y del proveedor. |
| Obsidian | Crear, leer, buscar notas y escribir en diario; requiere un vault válido. |
| Gmail y Calendar | Lectura/envío de correo y eventos; requieren OAuth y credenciales. No configurados/verificados aquí. |
| Tareas y memoria persistente | Código para Supabase; actualmente desconectado. Los recordatorios no tienen un sistema de aviso al vencer. |
| Finanzas | Código para cálculo, conversión, gastos y presupuesto; sin ruta en el planificador. |
| Office, Spotify y mensajería | Controladores y agentes parciales, con requisitos externos; sin rutas normales desde el planificador. |
| WhatsApp y hogar inteligente | Simulaciones en los agentes revisados; no deben presentarse como control real. |

## Orden recomendado de reparación

1. Recuperar una conversación funcional: corregir el esquema de Gemini y gestionar los errores de cuota/disponibilidad sin repetir llamadas innecesarias.
2. Propagar los errores reales y corregir la confirmación por WebSocket.
3. Evitar confirmaciones falsas de guardado; habilitar persistencia real y avisos programados.
4. Conectar capacidades al planificador, diferenciando las simuladas de las operativas.
5. Restringir acceso al control del equipo y sustituir interpolaciones HTML inseguras.

## Pruebas automatizadas

La suite detectó 63 pruebas. Una ejecución llegó a completar 14 pruebas de agentes y mostró al menos dos fallos en test_file_manager.py antes de interrumpirse por duración excesiva. No se obtuvo el detalle de esos fallos ni un resultado completo; requieren diagnóstico separado. No se considera aprobada la suite.

El servidor se dejó en localhost:8000. No se modificó el código funcional durante esta auditoría.

## Actualización: voz con activación separada
El modo Whisper falló con voz real al transcribir el nombre corto YU. Se evaluó el motor nativo español de Windows y no pasó la prueba positiva completa. Vosk con el nombre aislado produjo confusiones con yo y YouTube; no se habilitó esa variante. El usuario aceptó YU escucha y después una orden separada.
Se implementó Vosk continuo con gramática y competidores acústicos, sin umbral de energía de activación, y un proceso dedicado de audio. WASAPI falló en el contexto del servicio; MME recibió señal real y se dejó configurado por nombre. El micrófono no estaba silenciado y su volumen era 89 %. Las pruebas del motor con audio sintético incluyeron dos casos positivos y nueve negativos; las pruebas de turnos, reglas, permisos y ciclo del proceso también pasaron. Falta la confirmación de uso real del nuevo flujo. Ver VOZ_YU.md.

