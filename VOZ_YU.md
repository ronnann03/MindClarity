# YU por voz

## Uso sin teclado ni navegador

Con Windows iniciado, el supervisor abre YU en segundo plano. Ollama y Piper funcionan localmente. Un proceso de audio independiente usa Vosk para escuchar continuamente la frase de activación, sin enviar audio a la nube. La configuración actual selecciona el micrófono Realtek mediante MME y convierte su frecuencia nativa a 16 kHz para los modelos. WASAPI recibió señal en una prueba aislada, pero falló al abrirse en el contexto del asistente; por eso se eligió MME.

1. Di **«YU, escucha»**, como una frase completa.
2. Espera **«Te escucho»** y di **«abre la calculadora»**. No juntes todavía la activación y la orden: este modo utiliza dos pasos.
3. Espera la respuesta antes de dar otra orden. Mientras YU procesa o habla, no se aceptan activaciones nuevas para evitar que interprete su propia voz como una petición.
4. Para una acción que requiera autorización, YU describe la acción y sus parámetros. Después de que termine de hablar, di **«confirmar acción»** o **«cancelar acción»**. Sin una confirmación explícita, la acción se cancela. La espera está acotada.

## Órdenes de ejemplo

Di estas peticiones después de activar con «YU, escucha» y escuchar «Te escucho»; el prefijo YU de los ejemplos también se acepta en esa segunda parte.

| Di… | Resultado implementado |
|---|---|
| YU, qué puedes hacer | Explica las funciones disponibles y sus requisitos |
| YU, abre la calculadora | Abre la calculadora de Windows |
| YU, abre el bloc de notas | Abre Bloc de notas |
| YU, pon el volumen al 30 | Ajusta el volumen, sujeto al soporte del equipo |
| YU, ajusta el brillo al 50 | Ajusta el brillo si el monitor lo permite |
| YU, minimiza Chrome | Busca una ventana de Chrome y la minimiza |
| YU, abre YouTube | Abre el sitio web; no garantiza reproducción automática |
| YU, qué tiempo hace en Arequipa | Consulta clima con conexión a internet |
| YU, anota una tarea: llamar al proveedor | Guarda una tarea localmente si Supabase no está conectado |
| YU, lista mis tareas | Lee las tareas pendientes |
| YU, completa la tarea llamar al proveedor | Completa una tarea local con ese título si es único |

También existen rutas para archivos, calendario, correo, investigación y Obsidian. Las funciones con servicios externos requieren sus credenciales o su configuración. No se presenta una simulación como una integración real. Guardar una tarea con fecha no programa todavía un aviso automático.

## Qué se cambió

- Conservación de la orden incluida en la frase de activación, en lugar de pedir que se repita.
- Detección por prefijos y palabras completas; no se activa por encontrar «yu» dentro de otra palabra.
- Captura de la frase hasta una pausa, con tiempo máximo y umbral ajustables en `.env`.
- Sensibilidad ajustada al nivel medido del micrófono y normalización de señales de baja amplitud antes del reconocimiento.
- Español fijado para reconocimiento y conversación; nombre preferido configurado como Ronaldinho.
- Whisper small con procesamiento int8 en CPU, cuatro hilos y búsqueda más ligera.
- Exclusión entre turnos de voz y texto; pausa del detector mientras YU procesa o habla.
- Reintento del micrófono cuando se desconecta o falla temporalmente.
- Confirmaciones habladas explícitas para las órdenes originadas por el micrófono de la PC. Las órdenes del navegador conservan el modal de confirmación.
- Rutas directas para órdenes frecuentes y respuestas de ejecución sin una segunda llamada innecesaria al modelo.
- Resultados de agentes fallidos reconocidos como fallos, sin anunciarlos como éxitos.
- Tareas locales en SQLite cuando Supabase está desconectado.

## Verificación y límites

Las pruebas simuladas cubren captura por silencio, activación, conservación de parámetros, exclusión de turnos, aprobación/rechazo por voz, planificación, errores y persistencia de tareas. Se ejecutó además una prueba de Piper → audio en memoria → Whisper → extracción de orden, sin ejecutar la acción. La cancelación es conservadora: cualquier frase distinta de la confirmación exacta rechaza la acción.

El dispositivo de entrada detectado fue el micrófono Realtek del equipo. La primera prueba del usuario no reaccionó; se midió una señal inferior al umbral inicial y se ajustó a 0.002. La validación con voz real sigue pendiente tras ese ajuste: la prueba sintética no sustituye hablar en el micrófono.

El arranque automático está registrado y el supervisor fue probado en la sesión actual. La comprobación de un inicio de sesión real permanece pendiente hasta que el usuario cierre sesión o reinicie Windows. No se reinició el equipo automáticamente.

La escucha permanente requiere una PC encendida, sin suspensión, con acceso al micrófono. No hay escucha de órdenes nuevas ni interrupción durante la respuesta hablada. No se garantiza ejecutar cualquier petición imaginable: YU usa únicamente las acciones implementadas y configuradas.

## Prueba real posterior
Ronaldinho confirmó que YU respondió por voz, pero intentó abrir un nombre que contenía dos repeticiones de la orden. Se corrigió la extracción para colapsar repeticiones idénticas con activación, limpiar puntuación final y conservar 1,6 segundos previos al umbral. La escucha ya no reinicia su espera cada segundo. Falta confirmar una nueva apertura por voz después del reinicio. La interfaz localhost es opcional; el proceso de Windows debe permanecer activo para escuchar.


## Historial: activación anterior por nombre
Este modo anterior se conserva con VOICE_BACKEND=whisper, pero no es el modo activo. Falló con la voz real del usuario y no se considera una solución verificada.

## Configuración vigente: detector continuo y orden separada

VOICE_BACKEND=vosk activa un detector continuo de «YU escucha». El micrófono se selecciona por VOICE_INPUT_HOSTAPI=MME, evitando índices que pueden cambiar entre procesos. El detector usa la frecuencia nativa de entrada y remuestrea a 16 kHz. La captura de la orden posterior usa la misma interfaz. El servicio de audio mantiene los modelos cargados y se comunica con YU mediante mensajes locales, sin red.

En otra PC, instala las dependencias y ejecuta `python tools/setup_vosk.py` para descargar el modelo español oficial (39 MB, Apache 2.0). VOICE_BACKEND=whisper permite volver al comportamiento anterior. No se hace ese cambio silenciosamente si Vosk falla.

La gramática incluye competidores («yo escucho», «yo quiero», «YouTube», «ayuda») para no forzar cualquier sonido a parecerse a YU. La activación exige ambas palabras, en orden, con confianza mínima de 0.80 por palabra. Una activación por sí sola no ejecuta acciones: YU dice «Te escucho» y espera la petición. No se conserva audio en disco.

Las pruebas del motor real con voz sintética comprobaron dos activaciones y nueve frases negativas, incluidas palabras parecidas. La captura WASAPI también se abrió y recibió señal real sin ejecutar órdenes. Falta confirmar el ciclo completo con la voz de Ronaldinho; estas pruebas no garantizan ausencia de falsas activaciones en todos los entornos.

