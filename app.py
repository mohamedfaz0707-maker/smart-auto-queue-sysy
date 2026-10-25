from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "queue.db"
)


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Waiting',
            created_at TEXT
        )
    """)

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(queue)"
        ).fetchall()
    }

    if "created_at" not in columns:
        conn.execute(
            "ALTER TABLE queue ADD COLUMN created_at TEXT"
        )

        conn.execute(
            "UPDATE queue SET created_at = ? WHERE created_at IS NULL",
            (datetime.now().isoformat(timespec="seconds"),)
        )

    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def queue_stats(conn):
    total = conn.execute("""
        SELECT COUNT(*) AS n
        FROM queue
        WHERE status IN ('Waiting', 'Serving')
    """).fetchone()["n"]

    waiting = conn.execute("""
        SELECT COUNT(*) AS n
        FROM queue
        WHERE status = 'Waiting'
    """).fetchone()["n"]

    serving = conn.execute("""
        SELECT COUNT(*) AS n
        FROM queue
        WHERE status = 'Serving'
    """).fetchone()["n"]

    congestion = (
        "High" if total >= 10
        else "Moderate" if total >= 5
        else "Low"
    )

    return {
        "waiting_count": total,
        "waiting_only": waiting,
        "serving_count": serving,
        "estimated_wait_minutes": waiting * 5,
        "congestion": congestion
    }


# ================= FRONTEND =================

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>QueueFlow | AI Smart Queue System</title>

<style>

:root {
    --bg: #07111f;
    --panel: #101e32;
    --panel2: #162944;
    --blue: #5688ff;
    --cyan: #42ead1;
    --purple: #a18aff;
    --white: #f1f6ff;
    --muted: #9aacc5;
    --border: rgba(255,255,255,0.10);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background:
        radial-gradient(
            circle at 10% 0%,
            #1a3157 0,
            transparent 35%
        ),
        radial-gradient(
            circle at 100% 20%,
            #123b43 0,
            transparent 30%
        ),
        var(--bg);
    color: var(--white);
    min-height: 100vh;
}

button,
input,
select {
    font: inherit;
}

button {
    cursor: pointer;
}

.topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(7,17,31,0.92);
    backdrop-filter: blur(15px);
    border-bottom: 1px solid var(--border);
}

.nav {
    max-width: 1180px;
    margin: auto;
    padding: 15px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 850;
    font-size: 20px;
}

.logo {
    width: 44px;
    height: 44px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    background: linear-gradient(
        135deg,
        var(--blue),
        var(--cyan)
    );
    color: #07111f;
    font-size: 25px;
    box-shadow: 0 5px 25px #5688ff44;
}

.navlinks {
    display: flex;
    gap: 7px;
    flex-wrap: wrap;
}

.navlinks button {
    padding: 11px 15px;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--muted);
    font-weight: 700;
}

.navlinks button:hover,
.navlinks button.active {
    background: #ffffff10;
    color: white;
    border-color: var(--border);
}

.wrap {
    max-width: 1180px;
    margin: auto;
    padding: 30px 22px 50px;
}

.page {
    display: none;
    animation: appear 0.3s ease;
}

.page.active {
    display: block;
}

@keyframes appear {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 22px;
    margin: 10px 0 25px;
}

.panel {
    background: linear-gradient(
        145deg,
        #162944,
        #0d192b
    );
    border: 1px solid var(--border);
    border-radius: 23px;
    box-shadow: 0 15px 45px #00000020;
}

.hero-copy {
    padding: clamp(25px, 5vw, 50px);
}

.eyebrow {
    display: inline-block;
    padding: 9px 13px;
    border-radius: 30px;
    background: #42ead115;
    border: 1px solid #42ead133;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 850;
    letter-spacing: 1px;
}

h1 {
    font-size: clamp(35px, 5vw, 58px);
    line-height: 1.08;
    letter-spacing: -1.5px;
    margin: 23px 0 17px;
}

.gradient {
    background: linear-gradient(
        90deg,
        #ffffff,
        var(--cyan),
        #94b4ff
    );
    color: transparent;
    background-clip: text;
    -webkit-background-clip: text;
}

.lead {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.8;
}

.actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 25px;
}

.btn {
    padding: 13px 18px;
    border-radius: 12px;
    border: none;
    font-weight: 800;
    transition: 0.2s;
}

.btn:hover {
    transform: translateY(-2px);
    filter: brightness(1.1);
}

.primary {
    background: linear-gradient(
        120deg,
        var(--blue),
        #7b9fff
    );
    color: white;
    box-shadow: 0 8px 25px #5688ff30;
}

.secondary {
    background: #ffffff0c;
    border: 1px solid var(--border);
    color: var(--white);
}

.full {
    width: 100%;
}

.hero-visual {
    padding: 28px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 330px;
    background:
        radial-gradient(
            circle at 70% 20%,
            #5688ff35,
            transparent 40%
        ),
        linear-gradient(145deg, #162c4a, #101b30);
}

.visual-top,
.visual-foot {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    color: var(--muted);
    font-size: 12px;
}

.live {
    color: var(--cyan);
    font-weight: 850;
}

.orbit {
    height: 190px;
    display: grid;
    place-items: center;
    position: relative;
}

.orbit::before,
.orbit::after {
    content: "";
    position: absolute;
    width: 175px;
    height: 175px;
    border: 1px solid #7ca7ff55;
    border-radius: 50%;
}

.orbit::after {
    width: 130px;
    height: 130px;
    border-style: dashed;
    animation: spin 20s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.orbit-core {
    width: 95px;
    height: 95px;
    border-radius: 27px;
    display: grid;
    place-items: center;
    font-size: 38px;
    font-weight: 900;
    background: linear-gradient(
        135deg,
        var(--blue),
        var(--cyan)
    );
    color: #07111f;
    box-shadow: 0 0 45px #42ead155;
    z-index: 1;
}

.float-tag {
    position: absolute;
    background: #1a3151;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px;
    font-size: 12px;
}

.tag1 {
    top: 20px;
    left: 0;
}

.tag2 {
    bottom: 18px;
    right: 0;
}

.stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin: 20px 0 30px;
}

.stat-card {
    padding: 21px;
    background: #ffffff08;
    border: 1px solid var(--border);
    border-radius: 18px;
}

.stat-label {
    color: var(--muted);
    font-size: 13px;
}

.stat-value {
    font-size: 30px;
    font-weight: 900;
    margin: 10px 0 6px;
}

.stat-note {
    color: #7f96b7;
    font-size: 12px;
}

.section-head {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 15px;
    margin: 30px 0 20px;
}

.section-head h2 {
    margin: 12px 0 8px;
    font-size: 29px;
}

.section-head p {
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
}

.grid2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.card {
    padding: 25px;
}

.card h2 {
    margin-top: 0;
}

.field {
    margin: 18px 0;
}

.field label {
    display: block;
    color: #c7d6eb;
    font-weight: 750;
    font-size: 13px;
    margin-bottom: 9px;
}

.field input,
.field select {
    width: 100%;
    padding: 14px;
    border-radius: 12px;
    border: 1px solid #ffffff20;
    background: #091629;
    color: white;
    outline: none;
}

.field input:focus,
.field select:focus {
    border-color: var(--cyan);
    box-shadow: 0 0 0 3px #42ead119;
}

.field select option {
    background: #101e32;
}

.hint {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.7;
}

.resultbox {
    display: none;
    margin-top: 20px;
    padding: 20px;
    background: #42ead10c;
    border: 1px solid #42ead144;
    border-radius: 15px;
}

.token-big {
    font-size: 44px;
    font-weight: 950;
    color: var(--cyan);
    margin: 10px 0;
}

.result-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 15px;
}

.result-mini {
    background: #ffffff08;
    padding: 13px;
    border-radius: 12px;
}

.result-mini small {
    display: block;
    color: var(--muted);
    margin-bottom: 7px;
}

.steps,
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
}

.step,
.feature {
    padding: 21px;
    background: #ffffff07;
    border: 1px solid var(--border);
    border-radius: 17px;
}

.step p,
.feature p {
    color: var(--muted);
    line-height: 1.7;
    font-size: 14px;
}

.step-num {
    color: var(--cyan);
    font-weight: 900;
    font-size: 12px;
    letter-spacing: 1px;
}

.feature-icon {
    width: 46px;
    height: 46px;
    display: grid;
    place-items: center;
    background: #5688ff20;
    border-radius: 14px;
    font-size: 22px;
    margin-bottom: 15px;
}

.table-tools {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 18px;
}

.table-tools input {
    flex: 1;
    min-width: 180px;
    background: #091629;
    border: 1px solid var(--border);
    padding: 13px;
    border-radius: 11px;
    color: white;
}

.queue-list {
    display: grid;
    gap: 10px;
}

.queue-row {
    display: grid;
    grid-template-columns: 75px 1fr auto;
    gap: 12px;
    align-items: center;
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #ffffff05;
}

.queue-token {
    color: var(--cyan);
    font-weight: 900;
    font-size: 19px;
}

.queue-name {
    font-weight: 800;
    overflow-wrap: anywhere;
}

.queue-sub {
    color: var(--muted);
    font-size: 12px;
    margin-top: 5px;
}

.pill {
    display: inline-block;
    padding: 7px 11px;
    border-radius: 30px;
    font-size: 11px;
    font-weight: 900;
}

.waiting {
    color: #ffd27e;
    background: #ffbd5918;
}

.serving {
    color: var(--cyan);
    background: #42ead118;
}

.empty {
    text-align: center;
    padding: 30px 12px;
    color: var(--muted);
    border: 1px dashed #ffffff25;
    border-radius: 15px;
}

.notice {
    margin-top: 20px;
    padding: 15px;
    background: #ffbd5912;
    border: 1px solid #ffbd5930;
    border-radius: 12px;
    color: #ffda9c;
    line-height: 1.7;
}

.footer {
    border-top: 1px solid var(--border);
    margin-top: 40px;
    padding-top: 20px;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    color: var(--muted);
    font-size: 12px;
}

.toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translate(-50%, 20px);
    opacity: 0;
    pointer-events: none;
    background: #162944;
    border: 1px solid var(--border);
    padding: 14px 20px;
    border-radius: 12px;
    z-index: 20;
    transition: 0.25s;
    max-width: 90%;
}

.toast.show {
    opacity: 1;
    transform: translate(-50%, 0);
}

@media(max-width: 850px) {
    .hero {
        grid-template-columns: 1fr;
    }

    .stats {
        grid-template-columns: repeat(2, 1fr);
    }

    .feature-grid,
    .steps {
        grid-template-columns: 1fr 1fr;
    }
}

@media(max-width: 580px) {
    .nav {
        flex-direction: column;
        align-items: flex-start;
        padding: 14px;
    }

    .navlinks {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        width: 100%;
    }

    .navlinks button {
        padding: 10px 3px;
        font-size: 12px;
    }

    .wrap {
        padding: 20px 13px 40px;
    }

    .hero-copy,
    .card {
        padding: 20px;
    }

    .grid2,
    .feature-grid,
    .steps {
        grid-template-columns: 1fr;
    }

    .stats {
        gap: 9px;
    }

    .stat-card {
        padding: 14px;
    }

    .stat-value {
        font-size: 25px;
    }

    .queue-row {
        grid-template-columns: 55px 1fr;
    }

    .queue-row .pill {
        grid-column: 2;
        justify-self: start;
    }

    .section-head {
        align-items: flex-start;
        flex-direction: column;
    }
}

</style>
</head>

<body>

<header class="topbar">
    <nav class="nav">

        <div class="brand">
            <span class="logo">Q</span>

            <span>
                Queue<span style="color:var(--cyan)">Flow</span>
                <small style="display:block;color:var(--muted);
                font-size:10px;letter-spacing:1px">
                    SMART QUEUE MANAGEMENT
                </small>
            </span>
        </div>

        <div class="navlinks">
            <button class="active" data-page="home"
                    onclick="showPage('home')">Home</button>

            <button data-page="join"
                    onclick="showPage('join')">Join Queue</button>

            <button data-page="status"
                    onclick="showPage('status')">Live Status</button>

            <button data-page="about"
                    onclick="showPage('about')">About</button>
        </div>

    </nav>
</header>


<main class="wrap">

<!-- ================= HOME PAGE ================= -->

<section class="page active" id="page-home">

    <div class="hero">

        <div class="panel hero-copy">

            <span class="eyebrow">
                ✦ SMARTER WAITING STARTS HERE
            </span>

            <h1>
                Less waiting.<br>
                <span class="gradient">More living.</span>
            </h1>

            <p class="lead">
                Join a service queue online, receive your token,
                and check the estimated waiting time.
                Everything you need in one simple dashboard.
            </p>

            <div class="actions">
                <button class="btn primary"
                        onclick="showPage('join')">
                    + Join the Queue
                </button>

                <button class="btn secondary"
                        onclick="showPage('status')">
                    View Live Status ↗
                </button>
            </div>

        </div>

        <div class="panel hero-visual">

            <div class="visual-top">
                <span>QUEUE OVERVIEW</span>
                <span class="live">● SYSTEM ONLINE</span>
            </div>

            <div class="orbit">

                <span class="float-tag tag1">
                    ⚡ Quick token
                </span>

                <div class="orbit-core">Q</div>

                <span class="float-tag tag2">
                    ◷ Wait estimate
                </span>

            </div>

            <div class="visual-foot">
                <span>Simple • Clear • Convenient</span>
                <span>Live refresh</span>
            </div>

        </div>

    </div>


    <div class="stats">

        <div class="stat-card">
            <div class="stat-label">People in queue</div>
            <div class="stat-value" id="homeTotal">—</div>
            <div class="stat-note">Waiting + serving</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Currently waiting</div>
            <div class="stat-value" id="homeWaiting">—</div>
            <div class="stat-note">Waiting for service</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Estimated wait</div>
            <div class="stat-value" id="homeWait">—</div>
            <div class="stat-note">Minutes (estimate)</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Congestion</div>
            <div class="stat-value" id="homeCongestion"
                 style="font-size:24px">—</div>
            <div class="stat-note">Active queue status</div>
        </div>

    </div>


    <div class="section-head">
        <div>
            <h2>Built for a smoother visit</h2>
            <p>Queue information made simpler and easier to understand.</p>
        </div>
    </div>


    <div class="feature-grid">

        <article class="feature">
            <div class="feature-icon">🎟️</div>
            <h3>Easy token system</h3>
            <p>
                Join online and receive a unique token
                without waiting to register in person.
            </p>
        </article>

        <article class="feature">
            <div class="feature-icon">⏱️</div>
            <h3>Wait-time estimate</h3>
            <p>
                View an estimated waiting time based on
                the number of customers ahead in the queue.
            </p>
        </article>

        <article class="feature">
            <div class="feature-icon">📡</div>
            <h3>Live queue view</h3>
            <p>
                Check the active queue and refresh
                customer information automatically.
            </p>
        </article>

    </div>

</section>


<!-- ================= JOIN QUEUE PAGE ================= -->

<section class="page" id="page-join">

    <div class="section-head">
        <div>
            <span class="eyebrow">GET YOUR TOKEN</span>
            <h2>Join the queue</h2>
            <p>Enter your name and choose the service you need.</p>
        </div>
    </div>


    <div class="grid2">

        <div class="panel card">

            <h2>📝 Your details</h2>

            <form id="queueForm">

                <div class="field">
                    <label for="name">Full name</label>

                    <input
                        id="name"
                        type="text"
                        placeholder="Enter your name"
                        maxlength="100"
                        required
                        autocomplete="name"
                    >
                </div>

                <div class="field">
                    <label for="service">Choose a service</label>

                    <select id="service">
                        <option value="General">General Service</option>
                        <option value="Billing">Billing</option>
                        <option value="Enquiry">Enquiry</option>
                    </select>
                </div>

                <button class="btn primary full"
                        id="joinBtn"
                        type="submit">
                    Generate My Token →
                </button>

            </form>

            <p class="hint">
                Your name and service will appear in the active queue.
            </p>

        </div>


        <div class="panel card">

            <h2>✨ What happens next?</h2>

            <div class="steps" style="grid-template-columns:1fr">

                <div class="step">
                    <span class="step-num">STEP 01</span>
                    <h3>Submit your details</h3>
                    <p>Choose a service and join the queue.</p>
                </div>

                <div class="step">
                    <span class="step-num">STEP 02</span>
                    <h3>Get your token</h3>
                    <p>Your unique token appears after registration.</p>
                </div>

                <div class="step">
                    <span class="step-num">STEP 03</span>
                    <h3>Check queue status</h3>
                    <p>Visit Live Status to check active entries.</p>
                </div>

            </div>


            <div class="resultbox" id="resultbox">

                <div class="hint">YOUR TOKEN NUMBER</div>

                <div class="token-big" id="token">—</div>

                <div id="message">
                    Successfully joined!
                </div>

                <div class="result-grid">

                    <div class="result-mini">
                        <small>Estimated wait</small>
                        <strong id="waiting">—</strong>
                    </div>

                    <div class="result-mini">
                        <small>Congestion</small>
                        <strong id="congestion">—</strong>
                    </div>

                </div>

            </div>

        </div>

    </div>

</section>


<!-- ================= LIVE STATUS PAGE ================= -->

<section class="page" id="page-status">

    <div class="section-head">

        <div>
            <span class="eyebrow">QUEUE MONITOR</span>
            <h2>Live queue status</h2>
            <p>Queue information refreshes automatically every 10 seconds.</p>
        </div>

        <button class="btn secondary" onclick="loadQueue()">
            ↻ Refresh now
        </button>

    </div>


    <div class="stats">

        <div class="stat-card">
            <div class="stat-label">Active queue</div>
            <div class="stat-value" id="statusTotal">—</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Waiting</div>
            <div class="stat-value" id="statusWaiting">—</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Serving</div>
            <div class="stat-value" id="statusServing">—</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Congestion</div>
            <div class="stat-value" id="statusCongestion"
                 style="font-size:24px">—</div>
        </div>

    </div>


    <div class="panel card">

        <div class="table-tools">

            <input
                type="search"
                id="searchQueue"
                placeholder="Search by name, token, or service..."
                aria-label="Search queue"
            >

            <span class="hint" id="lastUpdated">
                Not updated yet
            </span>

        </div>

        <div id="queueList" class="queue-list">
            <div class="empty">Loading queue data...</div>
        </div>

        <p class="hint" style="margin-top:18px">
            Waiting time is estimated using five minutes per waiting
            customer. Actual service time may differ.
        </p>

    </div>

</section>


<!-- ================= ABOUT PAGE ================= -->

<section class="page" id="page-about">

    <div class="section-head">
        <div>
            <span class="eyebrow">ABOUT THE PROJECT</span>
            <h2>Queue management, made clearer.</h2>
            <p>
                An online queue registration and waiting-time
                estimation prototype.
            </p>
        </div>
    </div>


    <div class="panel hero-copy">

        <h2>What is QueueFlow?</h2>

        <p class="lead">
            QueueFlow is a smart queue management prototype.
            Customers can register for General Service, Billing,
            or Enquiry, receive a token, and view active queue
            information through a responsive website.
        </p>

    </div>


    <div class="feature-grid" style="margin-top:20px">

        <article class="feature">
            <div class="feature-icon">🧾</div>
            <h3>Token registration</h3>
            <p>
                Every successful registration receives
                a unique database-generated token number.
            </p>
        </article>

        <article class="feature">
            <div class="feature-icon">📊</div>
            <h3>Congestion indicator</h3>
            <p>
                Queue size is classified as Low, Moderate,
                or High using simple thresholds.
            </p>
        </article>

        <article class="feature">
            <div class="feature-icon">🗄️</div>
            <h3>Database storage</h3>
            <p>
                SQLite stores queue entries so the application
                can retrieve active customers.
            </p>
        </article>

    </div>


    <div class="notice">
        Project note: this version uses a fixed five-minute-per-waiting-
        customer estimate. A trained AI/ML prediction model is not
        integrated yet.
    </div>

</section>


<footer class="footer">
    <span>© 2026 QueueFlow · AI Smart Queue System</span>
    <span>Designed for desktop and mobile</span>
</footer>

</main>


<div class="toast" id="toast" role="status" aria-live="polite"></div>


<!-- ================= JAVASCRIPT ================= -->

<script>

const form = document.getElementById("queueForm");

let cachedQueue = [];


function showPage(name) {

    document.querySelectorAll(".page").forEach(page => {
        page.classList.toggle(
            "active",
            page.id === "page-" + name
        );
    });

    document.querySelectorAll(".navlinks button").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.page === name
        );
    });

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    if (name === "status" || name === "home") {
        loadQueue();
    }
}


function setText(id, value) {
    document.getElementById(id).textContent = value;
}


function toast(message) {

    const element = document.getElementById("toast");

    element.textContent = message;
    element.classList.add("show");

    setTimeout(() => {
        element.classList.remove("show");
    }, 3000);
}


async function safeJson(response) {

    const contentType =
        response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
        throw new Error(
            "Server response error. Check the backend."
        );
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || "Request failed"
        );
    }

    return data;
}


async function loadQueue() {

    try {

        const response = await fetch("/api/queue");

        const data = await safeJson(response);

        cachedQueue = data.queue || [];

        setText(
            "homeTotal",
            data.waiting_count
        );

        setText(
            "homeWaiting",
            data.waiting_only
        );

        setText(
            "homeWait",
            data.estimated_wait_minutes + " min"
        );

        setText(
            "homeCongestion",
            data.congestion
        );


        setText(
            "statusTotal",
            data.waiting_count
        );

        setText(
            "statusWaiting",
            data.waiting_only
        );

        setText(
            "statusServing",
            data.serving_count
        );

        setText(
            "statusCongestion",
            data.congestion
        );

        setText(
            "lastUpdated",
            "Updated " + new Date().toLocaleTimeString()
        );

        renderQueue();

    } catch (error) {

        document.getElementById("queueList").textContent =
            "Could not load queue. Please refresh.";

        setText("lastUpdated", "Connection issue");

    }

}


function renderQueue() {

    const list = document.getElementById("queueList");

    const query = (
        document.getElementById("searchQueue").value || ""
    ).toLowerCase().trim();

    const rows = cachedQueue.filter(customer => {

        return [
            customer.name,
            customer.service,
            String(customer.token),
            customer.status
        ].some(value =>
            String(value || "").toLowerCase().includes(query)
        );

    });

    list.replaceChildren();

    if (rows.length === 0) {

        const empty = document.createElement("div");

        empty.className = "empty";

        empty.textContent = query
            ? "No matching queue entries."
            : "No customers in the queue yet.";

        list.appendChild(empty);

        return;
    }


    rows.forEach(customer => {

        const row = document.createElement("div");

        row.className = "queue-row";


        const token = document.createElement("div");

        token.className = "queue-token";

        token.textContent = "#" + customer.token;


        const info = document.createElement("div");


        const name = document.createElement("div");

        name.className = "queue-name";

        name.textContent = customer.name;


        const subtitle = document.createElement("div");

        subtitle.className = "queue-sub";

        subtitle.textContent =
            customer.service + " · " + customer.status;


        info.append(name, subtitle);


        const status = document.createElement("span");

        status.className =
            "pill " +
            (
                customer.status === "Serving"
                    ? "serving"
                    : "waiting"
            );

        status.textContent = customer.status.toUpperCase();


        row.append(token, info, status);

        list.appendChild(row);

    });

}


document.getElementById("searchQueue").addEventListener(
    "input",
    renderQueue
);


form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const name =
        document.getElementById("name").value.trim();

    const service =
        document.getElementById("service").value;

    const button =
        document.getElementById("joinBtn");


    if (!name) {
        toast("Please enter your name.");
        return;
    }


    button.disabled = true;

    button.textContent = "Creating token...";


    try {

        const response = await fetch("/api/join", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                name: name,
                service: service
            })

        });


        const data = await safeJson(response);


        setText("token", "#" + data.token);

        setText("message", data.message);

        setText(
            "waiting",
            data.estimated_wait_minutes + " min"
        );

        setText(
            "congestion",
            data.congestion
        );


        document.getElementById("resultbox").style.display =
            "block";


        form.reset();

        toast("Your token has been created!");

        await loadQueue();


    } catch (error) {

        toast(error.message || "Unable to join queue.");

    } finally {

        button.disabled = false;

        button.textContent = "Generate My Token →";

    }

});


loadQueue();

setInterval(loadQueue, 10000);

</script>

</body>
</html>
"""


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/queue", methods=["GET"])
def get_queue():

    conn = get_connection()

    try:

        rows = conn.execute("""
            SELECT id, name, service, status
            FROM queue
            WHERE status IN ('Waiting', 'Serving')
            ORDER BY id
        """).fetchall()

        queue = [
            {
                "token": row["id"],
                "name": row["name"],
                "service": row["service"],
                "status": row["status"]
            }
            for row in rows
        ]

        stats = queue_stats(conn)

        return jsonify({
            "queue": queue,
            **stats
        })

    finally:
        conn.close()


@app.route("/api/join", methods=["POST"])
def join_queue():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()

    service = str(
        data.get("service", "General")
    ).strip()


    if not name:
        return jsonify({
            "error": "Please enter your name."
        }), 400


    if len(name) > 100:
        return jsonify({
            "error": "Name must be 100 characters or fewer."
        }), 400


    if service not in [
        "General",
        "Billing",
        "Enquiry"
    ]:
        return jsonify({
            "error": "Please select a valid service."
        }), 400


    conn = get_connection()

    try:

        cursor = conn.execute("""
            INSERT INTO queue (
                name,
                service,
                status,
                created_at
            )
            VALUES (?, ?, 'Waiting', ?)
        """, (
            name,
            service,
            datetime.now().isoformat(timespec="seconds")
        ))

        token = cursor.lastrowid

        conn.commit()

        stats = queue_stats(conn)

        return jsonify({
            "message": "Successfully joined the queue!",
            "token": token,
            "estimated_wait_minutes":
                stats["estimated_wait_minutes"],
            "congestion": stats["congestion"]
        }), 201

    finally:
        conn.close()


# ================= START SERVER =================

init_db()


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
