/* YU: interfaz local sin librerías, fuentes remotas ni bucles de animación. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const input = $('message-input'), feed = $('chat-feed'), workspace = document.querySelector('.workspace');
  const profileDialog = $('profile-dialog'), confirmDialog = $('confirmation-dialog');
  let socket, reconnectTimer, reconnectDelay = 1500, connected = false, state = 'idle';
  let activeConfirmation = null, recognition = null, listening = false, submitting = false;
  let assistantName = 'YU', selectedProfile = '', lastStatus = null, pendingText = '';
  const icon = name => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#i-' + name); svg.append(use); return svg;
  };
  function toast(text) {
    const el = document.createElement('div'); el.className = 'toast'; el.textContent = text;
    $('toasts').append(el); setTimeout(() => el.remove(), 5000);
  }
  function resizeInput() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 145) + 'px'; }
  function updateControls() {
    $('send-btn').disabled = !connected || submitting || ['processing', 'speaking'].includes(state) || !input.value.trim();
    $('mic-btn').disabled = (!recognition && lastStatus?.voice_backend !== 'vosk') || !connected || submitting || ['processing', 'speaking'].includes(state);
    $('clear-chat-btn').disabled = submitting || ['processing', 'speaking'].includes(state);
  }
  function setState(next) {
    state = next;
    if (next === 'idle' || next === 'error') submitting = false;
    const busy = next === 'processing' || next === 'speaking';
    $('activity').hidden = !busy;
    $('activity-text').textContent = next === 'speaking' ? 'YU está hablando en tu PC…' : 'YU está pensando…';
    const activation = lastStatus?.activation_phrase || 'YU';
    const labels = {idle: `Esperando “${activation}” · escucha automática`, processing: 'Pensando contigo…', speaking: 'Hablando en tu PC', listening: 'Te escucho · termina tu orden', error: 'Hubo un problema. Inténtalo de nuevo.'};
    $('voice-status-text').textContent = connected ? (labels[next] || labels.idle) : 'Reconectando con YU…';
    updateControls();
  }
  function appendMessage(role, text) {
    if (typeof text !== 'string' || !text.trim()) return;
    const nearBottom = workspace.scrollHeight - workspace.scrollTop - workspace.clientHeight < 140;
    $('welcome').hidden = true; feed.hidden = false;
    const article = document.createElement('article'); article.className = 'message ' + (role === 'user' ? 'user' : 'assistant');
    const avatar = document.createElement('span'); avatar.className = 'message-avatar'; avatar.setAttribute('aria-hidden', 'true'); avatar.textContent = role === 'user' ? 'TÚ' : 'y';
    const content = document.createElement('div'); content.className = 'message-content';
    const header = document.createElement('div'); header.className = 'message-header';
    const author = document.createElement('span'); author.textContent = role === 'user' ? 'Tú' : assistantName;
    const time = document.createElement('time'); time.dateTime = new Date().toISOString(); time.textContent = new Intl.DateTimeFormat('es-PE', {hour:'2-digit',minute:'2-digit',timeZone:'America/Lima'}).format(new Date());
    const copy = document.createElement('button'); copy.className = 'icon-button copy-button'; copy.setAttribute('aria-label', 'Copiar mensaje'); copy.title = 'Copiar mensaje'; copy.append(icon('copy'));
    copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(text); toast('Mensaje copiado.'); } catch { toast('No se pudo copiar. Puedes seleccionar el texto.'); } });
    const body = document.createElement('div'); body.className = 'message-text'; body.textContent = text;
    header.append(author, time, copy); content.append(header, body); article.append(avatar, content); feed.append(article);
    // Mantén acotado el DOM en conversaciones largas.
    while (feed.children.length > 120) feed.firstElementChild.remove();
    if (nearBottom || role === 'user') workspace.scrollTop = workspace.scrollHeight;
  }
  function sendText(text) {
    text = text.trim();
    if (!text) return;
    if (!connected) { toast('Espera a que YU vuelva a conectarse. Tu texto sigue aquí.'); return; }
    if (submitting || ['processing', 'speaking'].includes(state)) { toast('YU está terminando la respuesta anterior.'); return; }
    if (text.length > 8000) { toast('El mensaje es demasiado largo. Prueba con menos de 8000 caracteres.'); return; }
    try { socket.send(JSON.stringify({text})); pendingText = text; submitting = true; setState('processing'); input.value = ''; resizeInput(); }
    catch { submitting = false; toast('No se pudo enviar. Tu texto sigue aquí.'); updateControls(); }
  }
  function connect() {
    clearTimeout(reconnectTimer);
    if (socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)) return;
    socket = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/stream');
    socket.onopen = () => {
      connected = true; reconnectDelay = 1500; $('conn-banner').hidden = true;
      $('status-dot').classList.add('online'); refreshStatus(); setState('idle');
    };
    socket.onclose = () => {
      if (pendingText && !input.value.trim()) { input.value = pendingText; resizeInput(); toast('La conexión se perdió. Dejamos tu mensaje listo para volver a enviarlo si hace falta.'); }
      pendingText = '';
      connected = false; submitting = false; $('conn-banner').hidden = false;
      $('status-dot').classList.remove('online'); $('engine-dot').classList.remove('online');
      $('engine-title').textContent = 'Conexión interrumpida'; $('privacy-label').textContent = 'Sin conexión';
      $('activity').hidden = true; activeConfirmation = null;
      if (confirmDialog.open) confirmDialog.close();
      setState('idle'); reconnectTimer = setTimeout(connect, reconnectDelay); reconnectDelay = Math.min(reconnectDelay * 1.6, 15000);
    };
    socket.onerror = () => socket.close();
    socket.onmessage = event => {
      let data; try { data = JSON.parse(event.data); } catch { return; }
      switch (data.type) {
        case 'message': if (data.role === 'assistant') pendingText = ''; appendMessage(data.role, data.text); break;
        case 'state': setState(data.state); break;
        case 'error': submitting = false; setState('error'); toast(data.message || 'No se pudo completar la petición.'); break;
        case 'confirmation':
          if (activeConfirmation) { toast('Hay otra solicitud de confirmación pendiente.'); return; }
          activeConfirmation = data.id;
          $('confirm-description').textContent = data.description || 'Revisa esta acción antes de continuar.';
          $('confirm-risk-tag').textContent = 'RIESGO ' + (data.risk === 'critical' ? 'CRÍTICO' : 'ALTO');
          confirmDialog.showModal(); $('confirm-deny').focus(); break;
      }
    };
  }
  async function refreshStatus() {
    if (document.hidden) return;
    try {
      const response = await fetch('/api/status'); if (!response.ok) throw new Error();
      lastStatus = await response.json(); assistantName = lastStatus.assistant_name || 'YU';
      if (lastStatus.voice_backend === 'vosk') {
        $('mic-btn').title = 'Escucha automática: di «YU, escucha»';
        $('mic-btn').setAttribute('aria-label', 'Instrucciones de escucha automática');
      }
      $('engine-title').textContent = lastStatus.ai_provider === 'ollama' ? 'IA local configurada' : 'IA en la nube';
      $('engine-model').textContent = lastStatus.ai_model || 'Modelo configurado';
      $('engine-dot').classList.toggle('online', connected);
      $('privacy-label').textContent = lastStatus.ai_provider === 'ollama' ? 'Conversación local' : 'Proveedor de nube';
      if (connected && state === 'idle') {
        const level = lastStatus.microphone_level || {};
        const ready = lastStatus.voice_enabled && level.ready;
        $('voice-status-text').textContent = ready ? `Esperando “${lastStatus.activation_phrase || 'YU'}” · escucha automática` : 'Preparando el micrófono de la PC…';
      }
      updateControls();
    } catch { if (connected) $('privacy-label').textContent = 'Estado no disponible'; }
  }
  function updateDate() {
    const now = new Date();
    const hour = Number(new Intl.DateTimeFormat('en', {hour:'numeric',hourCycle:'h23',timeZone:'America/Lima'}).format(now));
    const greeting = hour >= 5 && hour < 12 ? 'Buenos días' : hour >= 12 && hour < 20 ? 'Buenas tardes' : 'Buenas noches';
    $('greeting').textContent = greeting + ', qué bueno verte.';
    $('today-date').textContent = new Intl.DateTimeFormat('es-PE', {weekday:'short',day:'numeric',month:'short',timeZone:'America/Lima'}).format(now).replaceAll('.', '');
    $('today-date').dateTime = now.toISOString().slice(0, 10);
  }
  async function loadProfiles() {
    $('profile-list').replaceChildren(); $('profile-error').textContent = '';
    try {
      const response = await fetch('/api/profiles'); if (!response.ok) throw new Error();
      const data = await response.json();
      for (const name of data.profiles || []) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'profile-item';
        const label = document.createElement('span'); label.textContent = name;
        button.append(icon('user'), label, icon('arrow')); button.addEventListener('click', () => selectProfile(name));
        $('profile-list').append(button);
      }
      if (!$('profile-list').children.length) $('profile-error').textContent = 'Crea tu primer perfil para personalizar YU.';
    } catch { $('profile-error').textContent = 'No se pudieron cargar los perfiles. Inténtalo de nuevo.'; }
  }
  async function selectProfile(name, notify = true) {
    try {
      const response = await fetch('/api/profiles/select', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
      if (!response.ok) throw new Error(); const data = await response.json();
      selectedProfile = name; assistantName = data.profile.assistant_name || 'YU';
      $('current-profile-name').textContent = name; $('profile-initial').textContent = name.slice(0,1).toUpperCase();
      try { sessionStorage.setItem('yu-profile', name); } catch { /* Almacenamiento opcional. */ }
      profileDialog.close(); if (notify) toast('Tu perfil está listo.');
    } catch { $('profile-error').textContent = 'No se pudo activar ese perfil. Inténtalo de nuevo.'; }
  }
  $('profile-form').addEventListener('submit', async event => {
    event.preventDefault(); const name = $('new-profile-name').value.trim(); if (!name) return;
    const button = event.submitter; button.disabled = true; $('profile-error').textContent = '';
    try {
      const response = await fetch('/api/profiles', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
      if (response.status === 409) { $('profile-error').textContent = 'Ya existe un perfil con ese nombre.'; return; }
      if (!response.ok) throw new Error(); $('new-profile-name').value = ''; await loadProfiles(); await selectProfile(name);
    } catch { $('profile-error').textContent = 'No se pudo crear el perfil. Inténtalo de nuevo.'; }
    finally { button.disabled = false; }
  });
  function resolveConfirmation(granted) {
    if (!activeConfirmation || !connected) return;
    socket.send(JSON.stringify({type:'confirmation_response',id:activeConfirmation,granted})); activeConfirmation = null; confirmDialog.close();
  }
  $('confirm-grant').addEventListener('click', () => resolveConfirmation(true));
  $('confirm-deny').addEventListener('click', () => resolveConfirmation(false));
  confirmDialog.addEventListener('cancel', event => { event.preventDefault(); resolveConfirmation(false); });
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
  $('profile-btn').addEventListener('click', () => { loadProfiles(); profileDialog.showModal(); });
  $('guide-btn').addEventListener('click', () => $('guide-dialog').showModal());
  $('guide-mobile-btn').addEventListener('click', () => $('guide-dialog').showModal());
  $('conversation-nav').addEventListener('click', () => input.focus());
  document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => { input.value = button.dataset.prompt; resizeInput(); updateControls(); input.focus(); }));
  input.addEventListener('input', () => { resizeInput(); updateControls(); });
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendText(input.value); } });
  $('chat-form').addEventListener('submit', event => { event.preventDefault(); sendText(input.value); });
  $('clear-chat-btn').addEventListener('click', () => { feed.replaceChildren(); feed.hidden = true; $('welcome').hidden = false; toast('Vista limpia. El contexto de la sesión se conserva.'); input.focus(); });

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (Recognition) {
    recognition = new Recognition(); recognition.lang = 'es-PE'; recognition.interimResults = true; recognition.continuous = false;
    recognition.onstart = () => { listening = true; $('mic-btn').setAttribute('aria-pressed','true'); $('mic-btn').setAttribute('aria-label','Detener micrófono'); $('live-transcript').hidden = false; $('live-transcript').textContent = 'Te escucho. Habla cuando quieras…'; };
    recognition.onresult = event => {
      let final = '', interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) final += event.results[i][0].transcript; else interim += event.results[i][0].transcript;
      }
      $('live-transcript').textContent = final || interim;
      if (final.trim()) {
        recognition.stop();
        const activation = final.trim().match(/^[¿¡]?(?:yu|yú|iu|hiu)\b[\s,.!?¿¡:;-]*(.*)$/i);
        if (!activation || !activation[1].trim()) { toast('Comienza por «YU», seguido de tu orden.'); return; }
        input.value = activation[1].trim(); resizeInput(); updateControls(); sendText(input.value);
      }
    };
    recognition.onerror = event => { toast(event.error === 'not-allowed' ? 'El navegador no tiene permiso para usar el micrófono. Puedes escribir a YU.' : 'No se pudo reconocer la voz. Inténtalo de nuevo o escribe tu mensaje.'); };
    recognition.onend = () => { listening = false; $('mic-btn').setAttribute('aria-pressed','false'); $('mic-btn').setAttribute('aria-label','Activar micrófono'); $('live-transcript').hidden = true; updateControls(); };
  } else { $('mic-btn').title = 'Este navegador no admite reconocimiento de voz. Puedes escribir o usar la palabra de activación en la PC.'; }
  $('mic-btn').addEventListener('click', () => {
    if (lastStatus?.voice_backend === 'vosk') { toast('Di «YU, escucha», espera «Te escucho» y después da tu orden. La PC ya escucha automáticamente.'); return; }
    if (!recognition) return;
    try { if (listening) recognition.stop(); else recognition.start(); } catch { toast('El micrófono aún se está preparando.'); }
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { updateDate(); refreshStatus(); } });
  const statusTimer = setInterval(() => { if (connected && !document.hidden) refreshStatus(); }, 2000);
  window.addEventListener('pagehide', () => { clearTimeout(reconnectTimer); clearInterval(statusTimer); if (recognition && listening) recognition.stop(); });
  updateDate(); connect(); updateControls();
  try { selectedProfile = sessionStorage.getItem('yu-profile') || ''; } catch { /* Opcional. */ }
  if (selectedProfile) selectProfile(selectedProfile, false);
})();
