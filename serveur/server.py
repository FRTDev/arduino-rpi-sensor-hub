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


def format_chart_ts(value):
    """Format court pour axe X des graphiques."""
    if not value:
        return ""
    try:
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return str(value)


def normaliser_consigne(arduino_id, valeur):
    if valeur is None:
        return None
    cmd = str(valeur).strip().upper()
    if cmd in COMMANDES_VALIDES.get(arduino_id, set()):
        return cmd
    return None


def parse_float(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def build_chart_series(rows):
    labels = []
    values = []
    for valeur, timestamp in rows:
        parsed = parse_float(valeur)
        if parsed is None:
            continue
        labels.append(format_chart_ts(timestamp))
        values.append(parsed)
    return labels, values


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
<html lang="fr">
<head>
    <title>TP2 IoT - Tableau de bord</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="30">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-1: #f7fbff;
            --bg-2: #eaf4ff;
            --surface: #ffffff;
            --surface-soft: #f8fbff;
            --text: #1e293b;
            --muted: #64748b;
            --line: #dbe7f3;
            --accent: #0f766e;
            --accent-2: #2563eb;
            --warn: #f59e0b;
            --temp: #0ea5e9;
            --radius: 14px;
            --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: "Poppins", "Segoe UI", Tahoma, sans-serif;
            color: var(--text);
            background: linear-gradient(160deg, var(--bg-1), var(--bg-2));
            min-height: 100vh;
            padding: 28px 16px;
        }

        .container {
            max-width: 1080px;
            margin: 0 auto;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: calc(var(--radius) + 4px);
            box-shadow: var(--shadow);
            padding: 24px;
            animation: fadein 320ms ease-out;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            color: var(--muted);
            font-size: 0.92rem;
        }

        .topbar a {
            color: var(--accent-2);
            text-decoration: none;
            font-weight: 600;
        }

        h1 {
            margin: 0 0 18px;
            color: var(--text);
            font-size: 1.9rem;
            letter-spacing: 0.01em;
        }

        h2 {
            margin: 26px 0 12px;
            font-size: 1.15rem;
            color: var(--text);
        }

        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        .sensor {
            background: var(--surface-soft);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 16px;
        }

        .sensor h3 {
            margin: 0 0 12px;
            font-size: 1rem;
        }

        .metric {
            font-size: 1.35rem;
            font-weight: 700;
            margin: 0 0 6px;
        }

        .meta {
            color: var(--muted);
            margin: 4px 0;
            font-size: 0.92rem;
        }

        .charts {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        .chart-card {
            background: var(--surface-soft);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 12px;
        }

        .chart-card h3 {
            margin: 0 0 10px;
            font-size: 0.98rem;
            color: var(--text);
        }

        .chart-wrap { position: relative; height: 220px; }
        canvas { display: block; width: 100% !important; height: 220px !important; }

        .table-panel {
            background: var(--surface-soft);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 10px;
            overflow-x: auto;
        }

        table { width: 100%; border-collapse: collapse; min-width: 680px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid var(--line); }
        th {
            color: var(--muted);
            font-weight: 600;
            font-size: 0.88rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        tr:hover { background: #eef6ff; }

        .badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            color: white;
            font-size: 0.84rem;
            font-weight: 600;
        }
        .ard1 { background: var(--warn); }
        .ard2 { background: var(--temp); }

        .form-panel {
            background: var(--surface-soft);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 14px;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 10px;
            align-items: center;
        }

        select, input, button {
            width: 100%;
            border-radius: 10px;
            border: 1px solid #c7d7ea;
            padding: 10px 12px;
            font-size: 0.95rem;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--accent-2);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }

        button {
            width: auto;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: white;
            border: none;
            font-weight: 600;
            cursor: pointer;
            min-width: 120px;
        }

        button:hover { filter: brightness(1.04); }

        .help {
            color: var(--muted);
            font-size: 0.88rem;
            margin: 10px 0 0;
            line-height: 1.5;
        }

        @keyframes fadein {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 900px) {
            .sensor-grid, .charts { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; }
            button { width: 100%; }
            table { min-width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="topbar">
            <div>Connecte: <strong>admin</strong></div>
            <a href="/logout">Deconnexion</a>
        </div>

        <h1>TP2 IoT - Tableau de bord</h1>

        <div class="sensor-grid">
            <div class="sensor">
                <h3>Arduino 1 - Luminosite (LDR)</h3>
                <p class="metric">{{ val1 if val1 else 'Aucune donnee' }}</p>
                <p class="meta">Derniere mise a jour: {{ time1 }}</p>
                <p class="meta">Consigne LED: <strong>{{ consigne1 }}</strong></p>
            </div>

            <div class="sensor">
                <h3>Arduino 2 - Temperature (TMP36)</h3>
                <p class="metric">{{ val2 if val2 else 'Aucune donnee' }} degC</p>
                <p class="meta">Derniere mise a jour: {{ time2 }}</p>
                <p class="meta">Consigne LED: <strong>{{ consigne2 }}</strong></p>
            </div>
        </div>

        <h2>Graphiques des mesures</h2>
        <div class="charts">
            <div class="chart-card">
                <h3>Arduino 1 - Luminosite</h3>
                <div class="chart-wrap">
                    <canvas id="chartArduino1"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h3>Arduino 2 - Temperature</h3>
                <div class="chart-wrap">
                    <canvas id="chartArduino2"></canvas>
                </div>
            </div>
        </div>

        <h2>Historique (20 dernieres mesures)</h2>
        <div class="table-panel">
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
                    <td>
                        <span class="badge {% if row["arduino_id"] == 'arduino1' %}ard1{% else %}ard2{% endif %}">
                            {{ 'Luminosite' if row["arduino_id"] == 'arduino1' else 'Temperature' }}
                        </span>
                    </td>
                    <td>{{ row["valeur"] }}</td>
                    <td>{{ row["timestamp_humain"] }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <h2>Envoyer une consigne LED</h2>
        <div class="form-panel">
            <form action="/consigne" method="post">
                <div class="form-row">
                    <select name="arduino_id" required>
                        <option value="arduino1">Arduino 1 (Photorésistance)</option>
                        <option value="arduino2">Arduino 2 (Température)</option>
                    </select>
                    <input type="text" name="valeur" placeholder="Ex: ON, OFF, AUTO, RED..." required>
                    <button type="submit">Envoyer</button>
                </div>
                <p class="help"></br> - Arduino 1: AUTO / ON / OFF </br> - Arduino 2: AUTO / OFF / RED / GREEN / BLUE</p>
            </form>
        </div>
    </div>

    <script>
        const labelsArduino1 = {{ labels_arduino1 | tojson }};
        const valuesArduino1 = {{ values_arduino1 | tojson }};
        const labelsArduino2 = {{ labels_arduino2 | tojson }};
        const valuesArduino2 = {{ values_arduino2 | tojson }};

        function buildChart(canvasId, labels, data, label, color) {
            if (typeof Chart === "undefined") return;
            const ctx = document.getElementById(canvasId);
            if (!ctx || data.length === 0) return;

            new Chart(ctx, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: label,
                        data: data,
                        borderColor: color,
                        backgroundColor: color + "33",
                        fill: true,
                        tension: 0.25,
                        pointRadius: 1.5,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { maxTicksLimit: 8 }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: "rgba(148, 163, 184, 0.25)" }
                        }
                    }
                }
            });
        }

        buildChart("chartArduino1", labelsArduino1, valuesArduino1, "Luminosite", "#f59e0b");
        buildChart("chartArduino2", labelsArduino2, valuesArduino2, "Temperature (degC)", "#0ea5e9");
    </script>
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

    c.execute(
        "SELECT valeur, timestamp FROM mesures WHERE arduino_id='arduino1' ORDER BY id DESC LIMIT 30"
    )
    chart_rows_1 = c.fetchall()

    c.execute(
        "SELECT valeur, timestamp FROM mesures WHERE arduino_id='arduino2' ORDER BY id DESC LIMIT 30"
    )
    chart_rows_2 = c.fetchall()

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

    chart_rows_1 = list(reversed(chart_rows_1))
    chart_rows_2 = list(reversed(chart_rows_2))

    labels_arduino1, values_arduino1 = build_chart_series(chart_rows_1)
    labels_arduino2, values_arduino2 = build_chart_series(chart_rows_2)

    return render_template_string(
        HTML_TEMPLATE,
        val1=row1[0] if row1 else None,
        time1=format_ts(row1[1]) if row1 else "Jamais",
        val2=row2[0] if row2 else None,
        time2=format_ts(row2[1]) if row2 else "Jamais",
        consigne1=consignes["arduino1"],
        consigne2=consignes["arduino2"],
        historique=historique,
        labels_arduino1=labels_arduino1,
        values_arduino1=values_arduino1,
        labels_arduino2=labels_arduino2,
        values_arduino2=values_arduino2,
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
