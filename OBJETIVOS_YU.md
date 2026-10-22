# Objetivos de YU

Referencia incorporada el 16 de octubre de 2026: prompt de humanización aportado por el usuario.

## Visión

Convertir YU en un asistente personal cercano, discreto y disponible: fácil de usar, capaz de recordar el contexto y de ayudar en lo cotidiano sin interrumpir innecesariamente. Su personalidad puede inspirarse en Jarvis, manteniendo claro que es una IA y describiendo con honestidad lo que puede hacer.

Esta hoja de ruta adopta los objetivos del prompt. Los comandos de ejemplo se adaptan a la instalación real: Windows nativo, Ollama, Whisper y Piper. Las rutas WSL y los reemplazos de código por suposición no forman parte del procedimiento de este proyecto.

## Objetivos del prompt y estado actual

| Objetivo | Estado | Criterio de aceptación / siguiente comprobación |
|---|---|---|
| Iniciar YU al iniciar sesión en Windows | Implementado; falta comprobar un nuevo inicio de sesión | Entrada YU_Assistant registrada, acceso start_yu.bat en el Escritorio y supervisor. Se verificó recuperación del proceso y prevención de duplicados; falta observar un inicio real después de cerrar sesión o reiniciar Windows. |
| Saludar según la hora del día | Implementado | Usar hora de Lima: mañana 05:00–11:59, tarde 12:00–19:59 y noche el resto. Pruebas de límites horarios y zona horaria aprobadas. |
| Evitar saludos repetitivos | Implementado | Saludar al primer contacto conversacional, al cambiar de día o tras cuatro horas de pausa. No anteponer un saludo a cada respuesta ni a los resultados de acciones. Se usa contexto en lugar del porcentaje aleatorio del ejemplo. |
| Mantener la misma respuesta en texto y voz | Implementado; continuar evaluación de uso real | El saludo se incorpora en el orquestador antes de guardar y emitir el texto. No se aplica otra vez en TTS. Las pruebas comprueban el texto final guardado. |
| Verificar humanización y reinicio | Verificación parcial completada | Pasaron 27 pruebas dirigidas de saludos y voz, y una prueba aislada con Ollama comprobó saludo inicial y segundo turno sin repetición. Quedan sesiones reales en español para revisar consistencia del idioma, naturalidad y precisión del nombre del usuario. |
| Exportar el proyecto 07 al Escritorio para el infoproducto | Realizado | Carpeta y ZIP exportados en Escritorio/Anro IA Infoproducto/07_Humanizacion_Asistente_IA. Incluyen fuentes seleccionadas, README y pruebas; no contienen claves, perfiles, conversaciones, grabaciones ni modelos. Las ediciones posteriores se guardan en subcarpetas fechadas para conservar el trabajo previo. |

## Próximos hitos

1. **Afinar la experiencia de conversación.** Español configurado para voz y conversación; nombre preferido Ronaldinho. Tras fallar la activación corta con voz real, el usuario eligió «YU escucha» y después la orden. Se implementó Vosk continuo en un proceso de audio independiente, Whisper para la petición y Piper para voz. La captura real recibe señal por MME; la prueba sintética incluye activaciones y frases negativas parecidas. El ciclo completo con Ronaldinho sigue pendiente de validación; no se considera resuelto solo por recibir señal.
2. **Validar el inicio real de Windows.** Comprobar YU tras un próximo inicio de sesión, conservando una única instancia. No reiniciar el equipo automáticamente para hacer esta comprobación.
3. **Mantener el material del infoproducto.** Exportación educativa realizada. Actualizarla con resultados de uso real; no presentar ejemplos simulados como acciones ejecutadas.

## Bases del proyecto que acompañan estos objetivos

- IA local con Ollama y voz local con Piper; no recurrir automáticamente a APIs pagas en el modo local.
- Interfaz clara y adaptable, con texto siempre accesible, estados comprensibles y animación moderada.
- Confirmación antes de acciones de riesgo y resultados fieles al éxito o fracaso real.
- La memoria conversacional entre reinicios sigue pendiente: el contexto actual es de sesión. Las tareas ya tienen persistencia SQLite local si Supabase está desconectado; los avisos por vencimiento y las funciones simuladas siguen pendientes.
- La presencia discreta no implica vigilar pantallas, enviar mensajes ni ejecutar acciones por iniciativa propia. Cualquier futura función proactiva deberá tener controles claros de activación, silencio y permisos.

## Referencias de implementación

- `core/conversation_style.py`: horarios y frecuencia de los saludos.
- `core/orchestrator.py`: personalidad y texto final compartido.
- `START_YU_LOCAL.ps1` y `CONFIGURAR_INICIO_YU.ps1`: arranque y supervisión.
- `tests/test_conversation_style.py`: pruebas de humanización.
- `OLLAMA_LOCAL.md`, `UI_REDESIGN.md` y `DIAGNOSTICO_YU.md`: configuración, interfaz y fallas conocidas.

Un objetivo solo se marcará como completado cuando cumpla su criterio de aceptación. Una función anunciada, un proceso activo o una respuesta HTTP 200 no bastan por sí solos para demostrar que funciona de extremo a extremo.
