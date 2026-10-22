# Rediseño de YU — 16 de octubre de 2026

Interfaz local con tonos verde oscuro y salvia, tipografía del sistema, identidad visual propia y composición adaptable a escritorio, móvil y paneles de poca altura.

## Cambios

- Campo de texto permanente: Enter envía y Shift+Enter añade una línea.
- Accesos rápidos que preparan el texto para revisarlo antes de enviarlo.
- Conversación legible, marcas de hora de Lima y copia de mensajes.
- Perfiles, guía de uso y confirmaciones mediante diálogos accesibles por teclado.
- Estados de conexión, procesamiento, voz y reconexión; conserva un borrador si se pierde la conexión durante el envío.
- Selección de perfil conservada durante la sesión del navegador.
- Sin fuentes, iconos ni bibliotecas desde CDN. Iconos SVG incluidos y esfera decorativa en CSS.
- Se eliminaron los dos canvas y sus bucles continuos de animación. Solo se animan los puntos de actividad mientras se procesa una petición, respetando la preferencia de movimiento reducido.
- Los textos del usuario, perfiles y respuestas se insertan con textContent en lugar de interpretarse como HTML.
- El receptor WebSocket sigue disponible mientras una orden espera confirmación. Se cancela la tarea pendiente al desconectar y se rechazan entradas inválidas.

## Verificación

- Sintaxis JavaScript comprobada con `node --check` y Python compilado.
- Tres pruebas automatizadas aprobadas para confirmación en la misma conexión, cancelación al desconectar y mensajes inválidos.
- Navegador real: envío y respuesta de Ollama, estados de actividad, copia, limpieza de vista, sugerencias, lista de perfiles y guía.
- Revisiones visuales en escritorio de 1440×900, móvil de 390×844 y el panel compacto del navegador de Codex.
- Capturas en `artifacts/yu-ui/`.

El micrófono del navegador conserva sus requisitos de soporte y permisos; no se solicitó acceso al micrófono durante la validación visual. La voz de la PC sigue utilizando Piper. Limpiar la vista no elimina el contexto de la sesión del asistente.

La interfaz anterior se conserva en `ui_web/index.previous.html` para consulta. El diseño no modifica las capacidades ni las limitaciones de las integraciones externas.
