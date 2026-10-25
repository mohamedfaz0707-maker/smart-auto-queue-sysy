from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
DATABASE = "queue.db"


# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            status TEXT DEFAULT 'Waiting'
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- FRONTEND ----------------

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>AI Smart Queue Prediction System</title>

<style>
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #eef3f9;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 700px;
    margin: auto;
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 5px 20px #d0d8e2;
}

h1 {
    color: #173b68;
    text-align: center;
    font-size: 32px;
}

.subtitle {
    text-align: center;
    color: #555;
    margin-bottom: 30px;
}

h2 {
    text-align: center;
    color: #222;
}

input, select, button {
    width: 100%;
    padding: 14px;
    margin: 8px 0;
    border-radius: 8px;
    border: 1px solid #ccc;
    font-size: 16px;
}

button {
    background: #1769aa;
    color: white;
    border: none;
    cursor: pointer;
}

button:hover {
    background: #104d80;
}

.card {
    background: #e8f3ff;
    padding: 20px;
    border-radius: 12px;
    margin-top: 25px;
}

.stat {
    display: inline-block;
    background: white;
    padding: 12px;
    margin: 5px;
    border-radius: 8px;
    width: 42%;
}

#message {
    text-align: center;
    font-weight: bold;
    overflow-wrap: anywhere;
}

.customer {
    background: #f5f7fa;
    padding: 12px;
    margin: 8px 0;
    border-radius: 8px;
    overflow-wrap: anywhere;
}

footer {
    text-align: center;
    margin-top: 20px;
    color: #777;
}

@media (max-width: 480px) {
    body {
        padding: 10px;
    }

    .container {
        padding: 18px;
    }

    h1 {
        font-size: 27px;
    }
}
</style>
</head>

<body>

<div class="container">

    <h1>AI Smart Queue Prediction System</h1>

    <p class="subtitle">
        Smart Queue Management and Waiting Time Prediction
    </p>

    <h2>Join the Queue</h2>

    <form id="queueForm">

        <input
            type="text"
            id="name"
            placeholder="Enter your name"
            required
            maxlength="100"
        >

        <select id="service">
            <option value="General">General Service</option>
            <option value="Billing">Billing</option>
            <option value="Enquiry">Enquiry</option>
        </select>

        <button type="submit" id="joinBtn">
            Join Queue
        </button>

    </form>

    <div class="card">

        <h2>Your Queue Details</h2>

        <p id="message">Join the queue to get your token.</p>

        <div class="stat">
            <strong>Token</strong>
            <p id="token">--</p>
        </div>

        <div class="stat">
            <strong>Waiting Time</strong>
            <p id="waiting">--</p>
        </div>

        <p>
            Congestion Level:
            <strong id="congestion">--</strong>
        </p>

    </div>

    <div class="card">

        <h2>Current Queue Status</h2>

        <button onclick="loadQueue()">
            Refresh Queue
        </button>

        <p id="summary">Loading queue...</p>

        <div id="queueList"></div>

    </div>

    <footer>
        AI Smart Queue Prediction System
    </footer>

</div>

<script>
const form = document.getElementById("queueForm");

form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const name = document.getElementById("name").value.trim();
    const service = document.getElementById("service").value;
    const button = document.getElementById("joinBtn");

    if (!name) {
        document.getElementById("message").textContent =
            "Please enter your name.";
        return;
    }

    button.disabled = true;
    button.textContent = "Please wait...";

    try {

        const response = await fetch("/api/join", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({name, service})
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to join queue");
        }

        document.getElementById("message").textContent =
            data.message;

        document.getElementById("token").textContent =
            data.token;

        document.getElementById("waiting").textContent =
            data.estimated_wait_minutes + " minutes";

        document.getElementById("congestion").textContent =
            data.congestion;

        form.reset();

        await loadQueue();

    } catch (error) {

        document.getElementById("message").textContent =
            "Error: " + error.message;

    } finally {

        button.disabled = false;
        button.textContent = "Join Queue";

    }
});


async function loadQueue() {

    try {

        const response = await fetch("/api/queue");
        const data = await response.json();

        if (!response.ok) {
            throw new Error("Unable to load queue");
        }

        document.getElementById("summary").textContent =
            "Customers in queue: " + data.waiting_count;

        const list = document.getElementById("queueList");
        list.replaceChildren();

        if (data.queue.length === 0) {

            list.textContent = "No customers in queue.";

            return;
        }

        data.queue.forEach(customer => {

            const item = document.createElement("div");

            item.className = "customer";

            item.textContent =
                "Token " + customer.token +
                " | " + customer.name +
                " | " + customer.service +
                " | " + customer.status;

            list.appendChild(item);

        });

    } catch (error) {

        document.getElementById("summary").textContent =
            "Unable to load queue. Please refresh.";

    }
}

loadQueue();

setInterval(loadQueue, 10000);
</script>

</body>
</html>
"""


# ---------------- FRONTEND ROUTE ----------------

@app.route("/")
def home():
    return render_template_string(HTML)


# ---------------- BACKEND: QUEUE DETAILS ----------------

@app.route("/api/queue", methods=["GET"])
def get_queue():

    conn = get_connection()

    rows = conn.execute("""
        SELECT id, name, service, status
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
        ORDER BY id
    """).fetchall()

    queue = []

    for row in rows:
        queue.append({
            "token": row["id"],
            "name": row["name"],
            "service": row["service"],
            "status": row["status"]
        })

    waiting_count = sum(
        1 for customer in queue
        if customer["status"] == "Waiting"
    )

    serving_count = sum(
        1 for customer in queue
        if customer["status"] == "Serving"
    )

    total_count = waiting_count + serving_count

    estimated_wait = total_count * 5

    if total_count >= 10:
        congestion = "High"
    elif total_count >= 5:
        congestion = "Moderate"
    else:
        congestion = "Low"

    conn.close()

    return jsonify({
        "queue": queue,
        "waiting_count": total_count,
        "estimated_wait_minutes": estimated_wait,
        "congestion": congestion
    })


# ---------------- BACKEND: JOIN QUEUE ----------------

@app.route("/api/join", methods=["POST"])
def join_queue():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    service = str(data.get("service", "General")).strip()

    if not name:
        return jsonify({
            "error": "Please enter your name"
        }), 400

    if len(name) > 100:
        return jsonify({
            "error": "Name is too long"
        }), 400

    if service not in ["General", "Billing", "Enquiry"]:
        return jsonify({
            "error": "Invalid service selected"
        }), 400

    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO queue (name, service, status)
        VALUES (?, ?, 'Waiting')
    """, (name, service))

    token = cursor.lastrowid

    total = conn.execute("""
        SELECT COUNT(*) AS total
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
    """).fetchone()["total"]

    conn.commit()
    conn.close()

    estimated_wait = total * 5

    if total >= 10:
        congestion = "High"
    elif total >= 5:
        congestion = "Moderate"
    else:
        congestion = "Low"

    return jsonify({
        "message": "Successfully joined the queue!",
        "token": token,
        "estimated_wait_minutes": estimated_wait,
        "congestion": congestion
    }), 201


# ---------------- START SERVER ----------------

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
