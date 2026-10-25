from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DATABASE = "queue.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            status TEXT DEFAULT 'Waiting'
        )
    """)

    connection.commit()
    connection.close()


def get_waiting_time(connection):
    waiting_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
    """).fetchone()["total"]

    # Demonstration estimate: 5 minutes per customer
    return waiting_count * 5


def get_congestion(waiting_count):
    if waiting_count >= 10:
        return "High"
    elif waiting_count >= 5:
        return "Moderate"
    return "Low"


@app.route("/")
def home():
    return send_from_directory(".", "index.html")
@app.route("/api/queue", methods=["GET"])
def get_queue():
    connection = get_db()

    customers = connection.execute("""
        SELECT id, name, service, status
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
        ORDER BY id
    """).fetchall()

    queue = []

    for index, customer in enumerate(customers):
        queue.append({
            "token": customer["id"],
            "name": customer["name"],
            "service": customer["service"],
            "status": customer["status"]
        })

    waiting_count = len(queue)
    estimated_wait = get_waiting_time(connection)

    connection.close()

    return jsonify({
        "queue": queue,
        "waiting_count": waiting_count,
        "estimated_wait_minutes": estimated_wait,
        "congestion": get_congestion(waiting_count)
    })


@app.route("/api/join", methods=["POST"])
def join_queue():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    service = data.get("service", "General").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    connection = get_db()

    connection.execute("""
        INSERT INTO queue (name, service, status)
        VALUES (?, ?, 'Waiting')
    """, (name, service))

    connection.commit()

    token = connection.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    waiting_time = get_waiting_time(connection)

    waiting_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
    """).fetchone()["total"]

    connection.close()

    return jsonify({
        "message": "Successfully joined the queue!",
        "token": token,
        "estimated_wait_minutes": waiting_time,
        "congestion": get_congestion(waiting_count)
    }), 201


initialize_database()

if __name__ == "__main__":
    app.run(debug=True)