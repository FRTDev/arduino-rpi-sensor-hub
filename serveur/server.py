#!/usr/bin/env python3
"""
Serveur IoT - TP2
Flask + SQLite
"""

from datetime import datetime
import os
import sqlite3

from flask import Flask, jsonify, render_template_string, request
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

DB_PATH = os.path.join(os.path.dirname(__file__), "iot_data.db")
UTILISATEURS = {"admin": "iot2026"}
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "gateway2026")

consignes = {"arduino1": "AUTO", "arduino2": "AUTO"}
ARDUINOS = set(consignes.keys())
COMMANDES_VALIDES = {
    "arduino1": {"AUTO", "ON", "OFF"},
    "arduino2": {"AUTO", "OFF", "RED", "GREEN", "BLUE"},
}


@auth.get_password
def get_password(username):
    return UTILISATEURS.get(username)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arduino_id TEXT NOT NULL,
            valeur TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    print("[DB] Base initialisee")


def verifier_gateway():
    return request.headers.get("X-API-Key") == GATEWAY_API_KEY


def format_ts(value):
    """Convertit ISO 8601 en format lisible: DD/MM/YYYY HH:MM:SS."""
    if not value:
        return "Jamais"
    try:
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return value


def normaliser_consigne(arduino_id, valeur):
    if valeur is None:
        return None
    cmd = str(valeur).strip().upper()
    if cmd in COMMANDES_VALIDES.get(arduino_id, set()):
        return cmd
    return None


@app.route("/api/data", methods=["POST"])
def recevoir_donnees():
    if not verifier_gateway():
        return jsonify({"error": "Acces refuse"}), 401

    data = request.get_json(silent=True)
    if not data or "arduino_id" not in data or "valeur" not in data:
        return jsonify({"error": "Donnees invalides"}), 400
    if data["arduino_id"] not in ARDUINOS:
        return jsonify({"error": "Arduino inconnu"}), 400

    timestamp = data.get("timestamp") or datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO mesures (arduino_id, valeur, timestamp) VALUES (?, ?, ?)",
        (data["arduino_id"], str(data["valeur"]), timestamp),
    )
    conn.commit()
    conn.close()

    print(f"[API] {data['arduino_id']} = {data['valeur']}")
    return jsonify({"status": "ok"}), 201


@app.route("/api/data", methods=["GET"])
@auth.login_required
def get_donnees():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    limite = request.args.get("limit", default=50, type=int)
    limite = min(max(limite, 1), 500)
    c.execute("SELECT * FROM mesures ORDER BY id DESC LIMIT ?", (limite,))
    rows = c.fetchall()
    conn.close()
    data = [
        {
            "id": row[0],
            "arduino_id": row[1],
            "valeur": row[2],
            "timestamp": row[3],
            "timestamp_humain": format_ts(row[3]),
        }
        for row in rows
    ]
    return jsonify(data)


@app.route("/api/consignes", methods=["GET"])
def get_consignes():
    if not verifier_gateway():
        return jsonify({"error": "Acces refuse"}), 401
    return jsonify(consignes)


@app.route("/api/consignes", methods=["POST"])
@auth.login_required
def set_consigne_api():
    data = request.get_json(silent=True)
    if not data or "arduino_id" not in data or "valeur" not in data:
        return jsonify({"error": "Parametres invalides"}), 400

    arduino_id = data["arduino_id"]
    if arduino_id not in consignes:
        return jsonify({"error": "Arduino inconnu"}), 400

    cmd = normaliser_consigne(arduino_id, data["valeur"])
    if cmd is None:
        return jsonify({"error": "Consigne invalide"}), 400

    consignes[arduino_id] = cmd
    print(f"[CONSIGNE] {arduino_id} = {cmd}")
    return jsonify({"status": "consigne enregistree"}), 200


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TP2 IoT - Tableau de bord</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .sensor { background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .sensor h3 { margin-top: 0; color: #1976d2; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .badge { padding: 5px 10px; border-radius: 3px; color: white; }
        .ard1 { background: #ff9800; }
        .ard2 { background: #2196f3; }
        .login-info { text-align: right; color: #666; font-size: 0.9em; }
        .help { color: #666; font-size: 0.9em; margin-top: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-info">Connecte: admin | <a href="/logout">Deconnexion</a></div>
        <h1>TP2 IoT - Tableau de bord</h1>

        <div class="sensor">
            <h3>Arduino 1 - Luminosite (LDR)</h3>
            <p><strong>Valeur actuelle:</strong> {{ val1 if val1 else 'Aucune donnee' }}</p>
            <p><small>Derniere mise a jour: {{ time1 }}</small></p>
            <p><small>Consigne LED: {{ consigne1 }}</small></p>
        </div>

        <div class="sensor">
            <h3>Arduino 2 - Temperature (TMP36)</h3>
            <p><strong>Temperature:</strong> {{ val2 if val2 else 'Aucune donnee' }} degC</p>
            <p><small>Derniere mise a jour: {{ time2 }}</small></p>
            <p><small>Consigne LED: {{ consigne2 }}</small></p>
        </div>

        <h2>Historique (20 dernieres mesures)</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Arduino</th>
                <th>Valeur</th>
                <th>Date/Heure</th>
            </tr>
            {% for row in historique %}
            <tr>
                <td>{{ row["id"] }}</td>
                <td><span class="badge {% if row["arduino_id"] == 'arduino1' %}ard1{% else %}ard2{% endif %}">
                    {{ 'Luminosite' if row["arduino_id"] == 'arduino1' else 'Temperature' }}
                </span></td>
                <td>{{ row["valeur"] }}</td>
                <td>{{ row["timestamp_humain"] }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Envoyer une consigne LED</h2>
        <form action="/consigne" method="post">
            <select name="arduino_id" required>
                <option value="arduino1">Arduino 1 (LDR LED)</option>
                <option value="arduino2">Arduino 2 (TMP36 RGB)</option>
            </select>
            <input type="text" name="valeur" placeholder="Ex: ON, OFF, AUTO, RED..." required>
            <button type="submit">Envoyer</button>
            <p class="help">Arduino1: AUTO/ON/OFF | Arduino2: AUTO/OFF/RED/GREEN/BLUE</p>
        </form>
    </div>
</body>
</html>
"""


@app.route("/")
@auth.login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, arduino_id, valeur, timestamp FROM mesures ORDER BY id DESC LIMIT 20")
    hist_rows = c.fetchall()

    c.execute("SELECT valeur, timestamp FROM mesures WHERE arduino_id='arduino1' ORDER BY id DESC LIMIT 1")
    row1 = c.fetchone()

    c.execute("SELECT valeur, timestamp FROM mesures WHERE arduino_id='arduino2' ORDER BY id DESC LIMIT 1")
    row2 = c.fetchone()
    conn.close()

    historique = [
        {
            "id": row[0],
            "arduino_id": row[1],
            "valeur": row[2],
            "timestamp_humain": format_ts(row[3]),
        }
        for row in hist_rows
    ]

    return render_template_string(
        HTML_TEMPLATE,
        val1=row1[0] if row1 else None,
        time1=format_ts(row1[1]) if row1 else "Jamais",
        val2=row2[0] if row2 else None,
        time2=format_ts(row2[1]) if row2 else "Jamais",
        consigne1=consignes["arduino1"],
        consigne2=consignes["arduino2"],
        historique=historique,
    )


@app.route("/consigne", methods=["POST"])
@auth.login_required
def web_consigne():
    arduino_id = request.form.get("arduino_id")
    valeur = request.form.get("valeur")
    if arduino_id in consignes:
        cmd = normaliser_consigne(arduino_id, valeur)
        if cmd:
            consignes[arduino_id] = cmd
    return '<script>window.location="/"</script>'


@app.route("/logout")
def logout():
    return "Deconnecte", 401


if __name__ == "__main__":
    init_db()
    print("[SERVEUR] Demarrage sur http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
