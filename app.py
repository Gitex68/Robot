from flask import Flask, render_template_string, jsonify, Response
import serial
import time
import queue
import threading

app = Flask(__name__)

log_queue = queue.Queue(maxsize=100)

def add_log(message: str):
    timestamp = time.strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    try:
        if log_queue.full():
            log_queue.get_nowait()
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

def send_serial(msg: str):
    if ser:
        try:
            ser.write(msg.encode("utf-8"))
            ser.flush()  # <--- CORRECTION INTÉGRÉE ICI : Force l'envoi immédiat
            add_log(f"Pi ➡️ Arduino : Tx '{msg}'")
        except Exception as e:
            add_log(f"Erreur d'écriture Série : {e}")
            pass

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
      padding-bottom: 280px;
      user-select: none;
    }
    .container { width: 100%; max-width: 420px; display: grid; gap: 16px; }
    .card { background: var(--card); border-radius: 16px; padding: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
    .title { text-align: center; font-weight: 700; letter-spacing: 0.5px; color: var(--accent); }
    .toggle { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .switch { position: relative; width: 72px; height: 36px; background: #2b3242; border-radius: 999px; cursor: pointer; transition: 0.2s; }
    .switch::after { content: ""; position: absolute; width: 28px; height: 28px; background: var(--accent); border-radius: 50%; top: 4px; left: 4px; transition: 0.2s; box-shadow: 0 0 10px rgba(77,208,225,0.6); }
    .switch.on { background: #25333f; }
    .switch.on::after { left: 40px; background: var(--accent2); box-shadow: 0 0 10px rgba(129,199,132,0.6); }
    .mode-label { font-weight: 700; color: var(--accent); }
    .mode-label.on { color: var(--accent2); }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); grid-gap: 12px; margin: 10px 0; }
    button { background: #263042; color: var(--text); border: 1px solid #2f3a52; border-radius: 12px; padding: 18px 8px; font-size: 1.1rem; cursor: pointer; transition: 0.15s; touch-action: manipulation; }
    button:hover { background: #2f3a52; }
    button:active { background: var(--accent); }
    .stop { background: var(--danger); border: none; font-weight: 700; font-size: 1.4rem; }
    .stop:active { background: #ff7675; }
    .slider { width: 100%; margin: 10px 0; }
    .disabled { opacity: 0.25; pointer-events: none; filter: grayscale(0.6); }
    .muted { color: var(--muted); font-size: 12px; text-align: center; }
    .video-stream { width: 100%; border-radius: 8px; margin-top: 10px; background: #000; aspect-ratio: 4/3; }
    
    /* Style pour les boutons HuskyLens actifs */
    .husky-btn.active { background: var(--accent2); color: #000; font-weight: bold; border-color: var(--accent2); }

    .terminal-container { position: fixed; bottom: 0; left: 0; right: 0; background: var(--terminal-bg); border-top: 4px solid var(--accent); z-index: 1000; display: flex; flex-direction: column; height: 180px; min-height: 80px; max-height: 80vh; }
    .terminal-header { background: #141923; padding: 14px 16px; font-size: 11px; font-weight: bold; color: var(--accent); display: flex; justify-content: space-between; align-items: center; cursor: ns-resize; user-select: none; touch-action: none; }
    .terminal-body { flex: 1; padding: 12px; font-family: 'Courier New', Courier, monospace; font-size: 11px; color: #39ff14; overflow-y: auto; white-space: pre-wrap; }
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
        <button class="move-btn" data-move="rotL" style="font-size: 1.4rem;">↩️</button>
        <button class="move-btn" data-move="up" style="font-size: 1.4rem;">⬆️</button>
        <button class="move-btn" data-move="rotR" style="font-size: 1.4rem;">↪️</button>

        <button class="move-btn" data-move="left" style="font-size: 1.4rem;">⬅️</button>
        <button class="stop move-btn" data-move="stop">🛑</button>
        <button class="move-btn" data-move="right" style="font-size: 1.4rem;">➡️</button>

        <div></div>
        <button class="move-btn" data-move="down" style="font-size: 1.4rem;">⬇️</button>
        <div></div>
      </div>
    </div>

    <div id="speedCard" class="card">
      <label id="speedLabel">Vitesse : 200</label>
      <input id="speed" class="slider" type="range" min="0" max="255" value="200" />
      <div class="muted">0 → 255</div>
    </div>

    <div id="huskyControls" class="card">
      <div class="title" style="margin-bottom:8px;">Modes Autonomes (Vision)</div>
      <div class="grid">
        <button class="husky-btn" data-cmd="1">Visage</button>
        <button class="husky-btn" data-cmd="2">Suivi</button>
        <button class="husky-btn" data-cmd="3">Objet</button>

        <button class="husky-btn" data-cmd="4">Ligne</button>
        <button class="husky-btn" data-cmd="5">Couleur</button>
        <button class="husky-btn" data-cmd="6">Tag</button>

        <button id="setIdBtn">ID Cible</button>
        <button class="husky-btn active" data-cmd="r">Sonar Seul</button>
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
    const huskyBtns = document.querySelectorAll(".husky-btn");

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

    const pressed = new Set();
    let lastCmd = "x";

    function computeMoveCmd() {
      if (pressed.has("up") && pressed.has("left")) return "u";
      if (pressed.has("up") && pressed.has("right")) return "i";
      if (pressed.has("down") && pressed.has("left")) return "j";
      if (pressed.has("down") && pressed.has("right")) return "k";
      if (pressed.has("up")) return "z";
      if (pressed.has("down")) return "s";
      if (pressed.has("left")) return "q";
      if (pressed.has("right")) return "d";
      if (pressed.has("rotL")) return "a";
      if (pressed.has("rotR")) return "e";
      return "x";
    }

    function updateMovement() {
      const cmd = computeMoveCmd();
      if (cmd !== lastCmd) {
        fetch(`/commande/${cmd}`);
        lastCmd = cmd;
      }
    }

    document.querySelectorAll(".move-btn").forEach(btn => {
      const move = btn.getAttribute("data-move");
      btn.addEventListener("pointerdown", (e) => { e.preventDefault(); btn.setPointerCapture(e.pointerId); pressed.add(move); updateMovement(); });
      btn.addEventListener("pointerup", (e) => { e.preventDefault(); pressed.delete(move); updateMovement(); });
      btn.addEventListener("pointercancel", (e) => { e.preventDefault(); pressed.delete(move); updateMovement(); });
    });

    // Gestion de l'état visuel des boutons HuskyLens
    huskyBtns.forEach(btn => {
      btn.addEventListener("click", async () => {
        huskyBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const cmd = btn.getAttribute("data-cmd");
        await fetch(`/commande/${cmd}`);
      });
    });

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

    const eventSource = new EventSource("/stream-logs");
    eventSource.onmessage = function(event) {
        const shouldScroll = terminalBody.scrollTop + terminalBody.clientHeight >= terminalBody.scrollHeight - 25;
        terminalBody.textContent += event.data + "\\n";
        if (shouldScroll) { terminalBody.scrollTop = terminalBody.scrollHeight; }
    };

    let isResizing = false;
    function initResize(e) { isResizing = true; if (e.cancelable) e.preventDefault(); }
    function handleResize(e) {
      if (!isResizing) return;
      if (e.cancelable) e.preventDefault();
      const currentY = e.touches ? e.touches[0].clientY : e.clientY;
      const computedHeight = window.innerHeight - currentY;
      if (computedHeight >= 80 && computedHeight <= (window.innerHeight * 0.8)) { terminalContainer.style.height = `${computedHeight}px`; }
    }
    function endResize() { isResizing = false; }

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

@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/mode/<type>")
def mode(type):
    if type == "auto": send_serial("A")
    else: send_serial("M")
    return jsonify(ok=True)

@app.route("/vitesse/<valeur>")
def vitesse(valeur):
    try:
        v = int(valeur)
        v = max(0, min(255, v))
        send_serial(f"V{v}")
    except ValueError: pass
    return jsonify(ok=True)

@app.route("/commande/<direction>")
def commande(direction):
    if direction: send_serial(direction[0])
    return jsonify(ok=True)

@app.route("/stream-logs")
def stream_logs():
    def generate():
        while True:
            log_item = log_queue.get() 
            yield f"data: {log_item}\n\n"
    return Response(generate(), mimetype="text/event-stream")

@app.route("/husky/id/<valeur>")
def husky_id(valeur):
    try:
        v = int(valeur)
        v = max(0, min(999, v))
        send_serial(f"t{v}")
    except ValueError:
        pass
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
