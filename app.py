from flask import Flask, render_template_string, jsonify, Response
import serial
import time
import queue
import threading

app = Flask(__name__)

# File d'attente pour partager les logs de la liaison série avec le site web
log_queue = queue.Queue(maxsize=100)

def add_log(message: str):
    """Ajoute un message horodaté dans la console du site web."""
    timestamp = time.strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    try:
        if log_queue.full():
            log_queue.get_nowait()  # Supprime le plus vieux si plein
        log_queue.put_nowait(log_line)
    except Exception:
        pass

# Initialisation de la liaison Série vers l'Arduino Uno
try:
    ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
    time.sleep(2)
    add_log("Système : Liaison Série avec Arduino établie (9600 bauds).")
except Exception as e:
    print(f"Erreur port série : {e}. Mode dégradé sans robot.")
    add_log(f"Erreur : Impossible de contacter l'Arduino ({e}).")
    ser = None

# Thread de lecture pour écouter l'Arduino en tâche de fond (les logs HuskyLens)
def serial_reader():
    while True:
        if ser and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        add_log(f"Arduino ➡️ Pi : {line}")
            except Exception:
                pass
        time.sleep(0.05)

if ser:
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

HTML = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=no" />
  <title>Robot Omnidirectionnel</title>
  <style>
    :root {
      --bg: #0f1115;
      --card: #1a1f2b;
      --accent: #4dd0e1;
      --accent2: #81c784;
      --danger: #ef5350;
      --text: #e0e0e0;
      --muted: #8b94a7;
      --terminal-bg: #05070b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      justify-content: center;
      padding: 20px;
      padding-bottom: 280px; /* Assure que le contenu reste accessible */
      user-select: none;
    }
    .container {
      width: 100%;
      max-width: 420px;
      display: grid;
      gap: 16px;
    }
    .card {
      background: var(--card);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    .title {
      text-align: center;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: var(--accent);
    }
    .toggle {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .switch {
      position: relative;
      width: 72px;
      height: 36px;
      background: #2b3242;
      border-radius: 999px;
      cursor: pointer;
      transition: 0.2s;
    }
    .switch::after {
      content: "";
      position: absolute;
      width: 28px;
      height: 28px;
      background: var(--accent);
      border-radius: 50%;
      top: 4px;
      left: 4px;
      transition: 0.2s;
      box-shadow: 0 0 10px rgba(77,208,225,0.6);
    }
    .switch.on {
      background: #25333f;
    }
    .switch.on::after {
      left: 40px;
      background: var(--accent2);
      box-shadow: 0 0 10px rgba(129,199,132,0.6);
    }
    .mode-label {
      font-weight: 700;
      color: var(--accent);
    }
    .mode-label.on {
      color: var(--accent2);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-gap: 12px;
      margin: 10px 0;
    }
    button {
      background: #263042;
      color: var(--text);
      border: 1px solid #2f3a52;
      border-radius: 12px;
      padding: 18px 8px;
      font-size: 1.4rem;
      cursor: pointer;
      transition: 0.15s;
      touch-action: manipulation;
    }
    button:hover { background: #2f3a52; }
    button:active { background: var(--accent); }
    .stop { background: var(--danger); border: none; font-weight: 700; }
    .stop:active { background: #ff7675; }
    .slider {
      width: 100%;
      margin: 10px 0;
    }
    .disabled {
      opacity: 0.25;
      pointer-events: none;
      filter: grayscale(0.6);
    }
    .muted { color: var(--muted); font-size: 12px; text-align: center; }
    
    .video-stream {
      width: 100%;
      border-radius: 8px;
      margin-top: 10px;
      background: #000;
      aspect-ratio: 4/3;
    }

    /* --- STRUCTURE DE LA ZONE MONITEUR SÉRIE --- */
    .terminal-container {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: var(--terminal-bg);
      border-top: 4px solid var(--accent);
      z-index: 1000;
      display: flex;
      flex-direction: column;
      height: 180px; /* Hauteur par défaut explicite */
      min-height: 80px;
      max-height: 80vh;
    }
    .terminal-header {
      background: #141923;
      padding: 14px 16px;
      font-size: 11px;
      font-weight: bold;
      color: var(--accent);
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: ns-resize;
      user-select: none;
      touch-action: none; /* Bloque le scroll de la page au toucher sur le bandeau */
    }
    .terminal-body {
      flex: 1;
      padding: 12px;
      font-family: 'Courier New', Courier, monospace;
      font-size: 11px;
      color: #39ff14;
      overflow-y: auto;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="title">Robot Omnidirectionnel</div>
      <div class="toggle" style="margin-top:12px;">
        <div>
          <div style="font-size: 12px; color: var(--muted);">Statut Pilote</div>
          <div id="modeLabel" class="mode-label">MANUEL</div>
        </div>
        <div id="switch" class="switch"></div>
      </div>
    </div>

    <div class="card">
      <div style="font-size: 14px; font-weight: bold; text-align: center; color: var(--accent);">Flux Vidéo HuskyLens</div>
      <img id="videoFeed" class="video-stream" src="" alt="En attente du flux vidéo..." />
    </div>

    <div id="controls" class="card">
      <div class="grid">
        <button class="hold-btn" data-cmd="a">↩️</button>
        <button class="hold-btn" data-cmd="z">⬆️</button>
        <button class="hold-btn" data-cmd="e">↪️</button>

        <button class="hold-btn" data-cmd="q">⬅️</button>
        <button class="stop hold-btn" data-cmd="x">🛑</button>
        <button class="hold-btn" data-cmd="d">➡️</button>

        <div></div>
        <button class="hold-btn" data-cmd="s">⬇️</button>
        <div></div>
      </div>
    </div>

    <div id="speedCard" class="card">
      <label id="speedLabel">Vitesse : 200</label>
      <input id="speed" class="slider" type="range" min="0" max="255" value="200" />
      <div class="muted">0 → 255</div>
    </div>

    <div id="huskyControls" class="card">
      <div class="title" style="margin-bottom:8px;">HuskyLens</div>
      <div class="grid">
        <button data-cmd="1">Visage</button>
        <button data-cmd="2">Suivi</button>
        <button data-cmd="3">Objet</button>

        <button data-cmd="4">Ligne</button>
        <button data-cmd="5">Couleur</button>
        <button data-cmd="6">Tag</button>

        <button id="setIdBtn">ID Cible</button>
        <button data-cmd="r">Reset</button>
        <div></div>
      </div>
    </div>
  </div>

  <div class="terminal-container" id="terminalContainer">
    <div class="terminal-header" id="terminalHeader">
      <span>🖥️ MONITEUR SÉRIE</span>
      <span style="font-size: 10px; color: #fff; background: #2f3a52; padding: 3px 8px; border-radius:4px;">AJUSTER</span>
    </div>
    <div class="terminal-body" id="terminalBody"></div>
  </div>

  <script>
    const switchEl = document.getElementById("switch");
    const modeLabel = document.getElementById("modeLabel");
    const controls = document.getElementById("controls");
    const speedCard = document.getElementById("speedCard");
    const speed = document.getElementById("speed");
    const speedLabel = document.getElementById("speedLabel");
    const terminalBody = document.getElementById("terminalBody");
    const terminalHeader = document.getElementById("terminalHeader");
    const terminalContainer = document.getElementById("terminalContainer");
    const setIdBtn = document.getElementById("setIdBtn");

    let autoMode = false;

    const piIP = window.location.hostname;
    document.getElementById("videoFeed").src = `http://${piIP}:8080/?action=stream`;

    function updateUI() {
      switchEl.classList.toggle("on", autoMode);
      modeLabel.textContent = autoMode ? "AUTOMATIQUE" : "MANUEL";
      modeLabel.classList.toggle("on", autoMode);
      controls.classList.toggle("disabled", autoMode);
      speedCard.classList.toggle("disabled", autoMode);
    }

    switchEl.addEventListener("click", async () => {
      autoMode = !autoMode;
      updateUI();
      const type = autoMode ? "auto" : "manuel";
      await fetch(`/mode/${type}`);
    });

    // --- Envoi répétitif si appui long ---
    const HOLD_INTERVAL_MS = 140;
    let holdTimer = null;

    function sendCmd(cmd) {
      fetch(`/commande/${cmd}`);
    }

    function startHold(cmd) {
      sendCmd(cmd);
      holdTimer = setInterval(() => sendCmd(cmd), HOLD_INTERVAL_MS);
    }

    function endHold() {
      if (holdTimer) {
        clearInterval(holdTimer);
        holdTimer = null;
      }
    }

    document.querySelectorAll("button[data-cmd]").forEach(btn => {
      const cmd = btn.getAttribute("data-cmd");

      if (btn.classList.contains("hold-btn")) {
        btn.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          startHold(cmd);
        });
        btn.addEventListener("pointerup", endHold);
        btn.addEventListener("pointerleave", endHold);
        btn.addEventListener("pointercancel", endHold);
        btn.addEventListener("click", (e) => e.preventDefault());
      } else {
        btn.addEventListener("click", async () => {
          await fetch(`/commande/${cmd}`);
        });
      }
    });

    window.addEventListener("pointerup", endHold);

    speed.addEventListener("input", async () => {
      const val = speed.value;
      speedLabel.textContent = `Vitesse : ${val}`;
      await fetch(`/vitesse/${val}`);
    });

    setIdBtn.addEventListener("click", async () => {
      const id = prompt("Entrer l'ID cible HuskyLens (ex: 1)");
      if (id !== null && id !== "") {
        await fetch(`/husky/id/${id}`);
      }
    });

    // RECEPTION EN FLUX CONTINU
    const eventSource = new EventSource("/stream-logs");
    eventSource.onmessage = function(event) {
        const shouldScroll = terminalBody.scrollTop + terminalBody.clientHeight >= terminalBody.scrollHeight - 25;
        terminalBody.textContent += event.data + "\\n";
        if (shouldScroll) {
            terminalBody.scrollTop = terminalBody.scrollHeight;
        }
    };

    // --- CORRECTION SYSTEME COMPACTE D'ÉTIREMENT SUR CONTAINER GLOBAL ---
    let isResizing = false;

    function initResize(e) {
      isResizing = true;
      if (e.cancelable) e.preventDefault();
    }

    function handleResize(e) {
      if (!isResizing) return;
      if (e.cancelable) e.preventDefault();

      const currentY = e.touches ? e.touches[0].clientY : e.clientY;
      const computedHeight = window.innerHeight - currentY;

      if (computedHeight >= 80 && computedHeight <= (window.innerHeight * 0.8)) {
        terminalContainer.style.height = `${computedHeight}px`;
      }
    }

    function endResize() {
      isResizing = false;
    }

    terminalHeader.addEventListener('mousedown', initResize);
    window.addEventListener('mousemove', handleResize, { passive: false });
    window.addEventListener('mouseup', endResize);

    terminalHeader.addEventListener('touchstart', initResize, { passive: false });
    window.addEventListener('touchmove', handleResize, { passive: false });
    window.addEventListener('touchend', endResize);

    updateUI();
  </script>
</body>
</html>
"""

def send_serial(msg: str):
    if ser:
        try:
            ser.write(msg.encode("utf-8"))
            add_log(f"Pi ➡️ Arduino : Tx '{msg}'")
        except Exception as e:
            add_log(f"Erreur d'écriture Série : {e}")
            pass

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/mode/<type>")
def mode(type):
    if type == "auto":
        send_serial("A")
    else:
        send_serial("M")
    return jsonify(ok=True)

@app.route("/vitesse/<valeur>")
def vitesse(valeur):
    try:
        v = int(valeur)
        v = max(0, min(255, v))
        send_serial(f"V{v}")
    except ValueError:
        pass
    return jsonify(ok=True)

@app.route("/commande/<direction>")
def commande(direction):
    if direction:
        send_serial(direction[0])
    return jsonify(ok=True)

@app.route("/husky/id/<valeur>")
def husky_id(valeur):
    try:
        v = int(valeur)
        v = max(0, min(999, v))
        send_serial(f"i{v}")
    except ValueError:
        pass
    return jsonify(ok=True)

@app.route("/stream-logs")
def stream_logs():
    def generate():
        while True:
            log_item = log_queue.get() 
            yield f"data: {log_item}\n\n"
    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
