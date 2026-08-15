from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "messages.db")
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_sid TEXT NOT NULL UNIQUE,
                sender TEXT NOT NULL DEFAULT '',
                recipient TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                profile_name TEXT NOT NULL DEFAULT '',
                num_media INTEGER NOT NULL DEFAULT 0,
                media_urls TEXT NOT NULL DEFAULT '[]',
                payload TEXT NOT NULL DEFAULT '{}',
                received_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_received_at "
            "ON messages(received_at DESC)"
        )


def get_messages(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, message_sid, sender, recipient, body, profile_name,
                   num_media, media_urls, payload, received_at
            FROM messages
            ORDER BY received_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    messages = []
    for row in rows:
        message = dict(row)
        message["media_urls"] = json.loads(message["media_urls"])
        message["payload"] = json.loads(message["payload"])
        messages.append(message)
    return messages


def get_stats() -> dict[str, int]:
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        senders = connection.execute(
            "SELECT COUNT(DISTINCT sender) FROM messages WHERE sender <> ''"
        ).fetchone()[0]
        media = connection.execute(
            "SELECT COALESCE(SUM(num_media), 0) FROM messages"
        ).fetchone()[0]
    return {"total": total, "senders": senders, "media": media}


def request_url_for_twilio() -> str:
    configured_url = os.environ.get("TWILIO_WEBHOOK_URL")
    if configured_url:
        return configured_url
    return request.url


def twilio_signature_is_valid() -> bool:
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    signature = request.headers.get("X-Twilio-Signature")
    if not auth_token or not signature:
        return False

    params = request.form.to_dict(flat=True)
    data = request_url_for_twilio() + "".join(
        f"{key}{params[key]}" for key in sorted(params)
    )
    expected = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected_signature = base64.b64encode(expected).decode("ascii")
    return hmac.compare_digest(expected_signature, signature)


def signature_validation_enabled() -> bool:
    return os.environ.get("TWILIO_VALIDATE_SIGNATURE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def save_message(payload: dict[str, Any]) -> bool:
    message_sid = str(payload.get("MessageSid") or "").strip()
    if not message_sid:
        message_sid = f"anonymous-{datetime.now(timezone.utc).timestamp()}"

    num_media = int(payload.get("NumMedia") or 0)
    media_urls = [
        payload[f"MediaUrl{index}"]
        for index in range(num_media)
        if payload.get(f"MediaUrl{index}")
    ]

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO messages
                (message_sid, sender, recipient, body, profile_name, num_media,
                 media_urls, payload, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_sid,
                str(payload.get("From") or ""),
                str(payload.get("To") or ""),
                str(payload.get("Body") or ""),
                str(payload.get("ProfileName") or ""),
                num_media,
                json.dumps(media_urls),
                json.dumps(payload),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        return cursor.rowcount == 1


@app.get("/")
def dashboard() -> str:
    return render_template(
        "index.html",
        messages=get_messages(),
        stats=get_stats(),
        validation_enabled=signature_validation_enabled(),
        has_auth_token=bool(os.environ.get("TWILIO_AUTH_TOKEN")),
        webhook_path="/webhook/whatsapp",
    )


@app.get("/healthz")
def healthz() -> Response:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return jsonify(
            {
                "status": "ok",
                "service": "twilio-whatsapp-webhook",
                "signature_validation": signature_validation_enabled(),
            }
        )
    except sqlite3.Error:
        return jsonify({"status": "error", "service": "twilio-whatsapp-webhook"}), 503


@app.get("/messages")
def messages_api() -> Response:
    return jsonify({"messages": get_messages()})


@app.post("/webhook/whatsapp")
def whatsapp_webhook() -> Response:
    if signature_validation_enabled():
        if not os.environ.get("TWILIO_AUTH_TOKEN"):
            return jsonify({"error": "TWILIO_AUTH_TOKEN is not configured"}), 503
        if not twilio_signature_is_valid():
            return jsonify({"error": "Invalid Twilio signature"}), 403

    payload = request.form.to_dict(flat=True)
    if not payload:
        return jsonify({"error": "Expected Twilio form-encoded payload"}), 400

    save_message(payload)
    return Response("<Response></Response>", mimetype="application/xml")


@app.errorhandler(404)
def not_found(_error: Any) -> tuple[str, int]:
    return render_template("404.html"), 404


init_database()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)