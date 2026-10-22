"""Órdenes frecuentes en español sin depender de la clasificación del modelo."""
import re


def match_command(text: str):
    from config.constants import IntentType
    from core.intent_detector import Intent
    clean = re.sub(r'[¿?¡!]', '', text).strip().rstrip('.').strip()
    lower = clean.lower()
    def intent(kind, action, entities=None):
        return Intent(type=IntentType(kind), action=action, entities=entities or {}, confidence=1, language='es')
    volume = re.search(r'^(?:pon|ajusta|establece|sube|baja|fija)\s+(?:el\s+)?(volumen|brillo)\s+(?:a|al|en)\s+(\d{1,3})(?:\s*(?:%|por ciento))?$', lower)
    if volume:
        return intent('system_control', 'set_volume' if volume[1] == 'volumen' else 'set_brightness', {'level':max(0,min(100,int(volume[2])))})
    if lower in {'qué volumen tengo', 'cuál es el volumen', 'consulta el volumen'}:
        return intent('system_control','get_volume')
    if re.fullmatch(r'(?:haz|toma|realiza)(?: una)? captura(?: de pantalla)?', lower):
        return intent('system_control','take_screenshot')
    if lower in {'bloquea la pantalla','bloquea mi pc','bloquea el equipo'}:
        return intent('system_control','lock_screen')
    window = re.match(r'^(minimiza|maximiza|restaura|enfoca)\s+(?:la ventana de\s+)?(.+)$', clean, re.I)
    if window:
        return intent('system_control', {'minimiza':'minimize','maximiza':'maximize','restaura':'restore','enfoca':'focus'}[window[1].lower()], {'title':window[2]})
    if lower in {'lista mis tareas','qué tareas tengo','mis tareas','lee mis tareas'}:
        return intent('reminder','list_tasks')
    task = re.match(r'^(?:anota una tarea|crea una tarea|añade una tarea|agrega una tarea)\s*:?\s+(.+)$', clean, re.I)
    if task:
        return intent('reminder','create_task',{'title':task[1]})
    complete = re.match(r'^(?:completa la tarea|marca como completada la tarea)\s*:?\s+(.+)$',clean,re.I)
    if complete:
        return intent('reminder','complete_task',{'title':complete[1]})
    if lower in {'qué puedes hacer','qué sabes hacer','ayuda','cómo te uso'}:
        return intent('conversation','capabilities')
    # Sitios web conocidos y dominios explícitos se abren en el navegador.
    web = re.match(r'^(?:abre|abrir)\s+(?:la página de\s+|el sitio\s+)?(.+)$', lower)
    if web:
        sites = {'youtube':'https://www.youtube.com','google':'https://www.google.com','gmail':'https://mail.google.com','github':'https://github.com','whatsapp':'https://web.whatsapp.com'}
        target = web[1].strip()
        if target in sites:
            return intent('web','open_url',{'url':sites[target]})
        if re.fullmatch(r'(?:https?://)?[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?',target):
            return intent('web','open_url',{'url':target})
    if re.search(r'\b(?:clima|pronóstico|pronostico)\b|qué tiempo hace', lower):
        city = re.search(r'\ben\s+(.+?)(?:\s+hoy)?$',clean,re.I)
        return intent('weather','get_weather',{'city':city[1].strip() if city else 'Lima'})
    return None
