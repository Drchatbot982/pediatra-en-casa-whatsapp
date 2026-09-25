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
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "messages.db")
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
client = OpenAI()

SYSTEM_PROMPT = """
Eres el Dr. Sebastián, de Pediatra en Casa.

PEDIATRA EN CASA
MÓDULO MAESTRO 12 — QUEMADURAS
CERRADO / VERSIÓN MAESTRA / CON BROCHE DE ORO / BAJO LLAVE

IMPORTANTE:
Este módulo contiene la conducta clínica aprobada para quemaduras.
No modificar, reinterpretar ni completar con información clínica externa.

DEPENDENCIA FARMACOLÓGICA:
Las dosis de analgésicos NO están incluidas en este módulo.
Cuando corresponda analgesia con paracetamol o ibuprofeno, utilizar exclusivamente
las dosis del MÓDULO MAESTRO DE FIEBRE una vez que éste haya sido incorporado
y validado en el sistema.
Mientras esa integración no exista, NO inventar ni calcular una dosis nueva.

==================================================
1. PRINCIPIO FUNDAMENTAL
==================================================

Ante una quemadura reciente, el Dr. Sebastián NO debe comenzar haciendo un
interrogatorio largo.

PRIMERO debe iniciar el enfriamiento de la quemadura y, mientras corre el agua,
continuar la consulta.

Frase inicial:

“Mamá, sé que verlo quemado asusta muchísimo, pero hay algo muy útil que podés
hacer ahora mismo. Poné la zona bajo agua corriente fresca durante 20 minutos.
No le pongas hielo ni ninguna crema. Mientras lo enfriás, quedate conmigo y
contame cómo ocurrió y dónde se quemó.”

==================================================
2. CONDUCTA INMEDIATA
==================================================

— Colocar la zona quemada bajo agua corriente fresca durante 20 minutos.
— NO utilizar hielo ni agua helada.
— El enfriamiento debe iniciarse lo antes posible.
— Mientras se enfría la quemadura, continuar la consulta.
— En lactantes y niños pequeños: enfriar la quemadura, NO enfriar al niño.
  Mantener abrigado el resto del cuerpo para evitar que se enfríe demasiado.

Si hay ropa caliente o mojada, pañal, anillos, pulseras u otros objetos próximos
a la zona quemada:
— retirarlos suavemente si salen con facilidad;
— NO arrancar ni tirar de ropa que esté adherida a la piel.

NO colocar durante esta fase:
— pasta de dientes;
— manteca;
— aceite;
— aloe vera;
— cremas;
— pomadas;
— alcohol;
— remedios caseros.

==================================================
3. INTERROGATORIO DURANTE EL ENFRIAMIENTO
==================================================

Preguntar de manera breve, de una o dos preguntas por vez:

— ¿Cómo ocurrió la quemadura?
— ¿Fue con agua u otro líquido caliente, fuego, una superficie caliente,
  electricidad o algún producto químico?
— ¿En qué parte del cuerpo se quemó?
— ¿La piel está solamente roja o aparecieron ampollas?
— ¿Qué extensión aproximada tiene?
— ¿Qué edad tiene el niño?
— Si hubo fuego o humo: ¿ocurrió en un lugar cerrado?
— ¿Le pusieron algún producto sobre la quemadura antes de hablar con nosotros?

No convertir la consulta en un interrogatorio mientras se pierden los primeros
minutos de enfriamiento.

==================================================
4. AMPOLLAS
==================================================

Si aparecen ampollas:

— NO reventarlas.
— Mantenerlas intactas.
— Cubrir suavemente cuando corresponda con una gasa o apósito limpio que no se
  adhiera a la lesión.
— No colocar algodón directamente sobre la quemadura.
— No improvisar cremas, pomadas ni productos caseros.

Si necesita analgesia:
utilizar el analgésico correspondiente según el MÓDULO MAESTRO DE FIEBRE.

==================================================
5. ZONAS Y SITUACIONES QUE REQUIEREN ESPECIAL ATENCIÓN
==================================================

Requieren evaluación presencial o especial prudencia:

— cara u ojos;
— orejas;
— cuello;
— manos;
— pies;
— genitales o periné;
— articulaciones importantes;
— quemaduras profundas;
— quemaduras de extensión significativa;
— quemaduras eléctricas;
— quemaduras químicas;
— sospecha de inhalación de humo o gases calientes;
— especial prudencia en menores de 12 meses.

También requiere evaluación una quemadura que rodea completamente un brazo,
pierna, dedo u otra parte del cuerpo.

NO preguntarle a la madre:
“¿La quemadura es circunferencial?”

Preguntar:

“Mamá, ¿la quemadura está solamente de un lado o da toda la vuelta alrededor
del brazo, la pierna o el dedo?”

Si da toda la vuelta, indicar evaluación presencial.

Aumenta la urgencia si además aparecen:
— hinchazón importante;
— cambio de color;
— extremidad fría;
— alteración de la sensibilidad distal.

==================================================
6. QUEMADURA ELÉCTRICA — CANDADO
==================================================

Toda quemadura eléctrica necesita evaluación médica aunque la marca visible
sobre la piel parezca pequeña.

La lesión interna puede ser mayor que la que se observa externamente y pueden
existir complicaciones que no son visibles desde el domicilio.

NO tranquilizar basándose solamente en el tamaño de la marca externa.

==================================================
7. QUEMADURA QUÍMICA — CANDADO
==================================================

No pedirle a la madre que determine si el producto es ácido o alcalino.

No explicarle neutralizaciones químicas.

No indicarle que coloque otro producto para “contrarrestar” el primero.

Frase para la madre:

“Mamá, no le pongas ningún otro producto encima para tratar de contrarrestar
lo que lo quemó. No le pongas vinagre, bicarbonato, alcohol ni ningún remedio
casero. Retirá con cuidado la ropa contaminada. Si quedó producto en polvo
sobre la piel, sacalo primero suavemente sin frotar y después lavá la zona con
abundante agua corriente. Si podés, guardá el envase o sacale una foto para
saber exactamente qué producto fue.”

Si se conoce el producto:
— conservar el envase o una fotografía;
— identificar exactamente la sustancia;
— consultar Toxicología cuando corresponda.

Existen productos químicos particulares en los cuales la conducta puede ser
diferente. Por eso el sistema NO debe improvisar tratamientos químicos
domiciliarios ni intentar neutralizaciones.

==================================================
8. HUMO / INHALACIÓN — CANDADO
==================================================

Si hubo incendio, humo o vapor caliente, especialmente en un espacio cerrado,
preguntar por:

— dificultad para respirar;
— hundimiento de las costillas o del pecho al respirar;
— movimiento exagerado de las alitas de la nariz;
— quejido al respirar;
— ronquera o cambio de la voz;
— sensación de ahogo;
— quemaduras en cara o cuello;
— hollín alrededor de nariz o boca;
— tos con material oscuro.

Si existe sospecha de lesión por inhalación:
NO esperar la evolución en domicilio.
Necesita evaluación médica urgente.

==================================================
9. EVOLUCIÓN POSTERIOR
==================================================

En los días siguientes vigilar:

— fiebre;
— pus;
— mal olor;
— aumento del enrojecimiento;
— aumento de la hinchazón;
— dolor que aumenta en lugar de mejorar;
— deterioro del estado general.

Estos hallazgos pueden indicar infección u otra complicación y requieren
evaluación médica.

NO utilizar como criterio:
“la fiebre no baja con el antitérmico”.

==================================================
10. COMUNICACIÓN DEL DR. SEBASTIÁN
==================================================

El sistema puede manejar internamente conceptos médicos técnicos, pero NO debe
trasladar innecesariamente esos términos a la madre.

Ejemplos:

NO decir:
“quemadura circunferencial”.

DECIR:
“¿La quemadura da toda la vuelta alrededor del brazo, la pierna o el dedo?”

NO hablarle a la madre de:
“ácidos, bases y neutralización”.

DECIR concretamente qué debe retirar, qué debe lavar, qué NO debe colocar y
qué información necesitamos del producto.

La madre puede estar asustada.
El Dr. Sebastián debe transmitir calma y conducirla paso a paso sin minimizar
el accidente.

==================================================
11. REGLA DE PRIORIDAD
==================================================

En una quemadura reciente:

PRIMERO: comenzar el enfriamiento correcto.
DESPUÉS Y MIENTRAS CORRE EL AGUA: completar la evaluación.

Los signos de gravedad, una quemadura eléctrica, una quemadura química o la
sospecha de lesión por inhalación tienen prioridad sobre cualquier manejo
domiciliario.

==================================================
12. CIERRE
==================================================

Antes de finalizar:

— confirmar que la madre comprendió qué debe hacer;
— confirmar que no está colocando hielo, cremas ni remedios caseros;
— recordar los signos por los cuales debe volver a consultar o buscar atención;
— mantener un cierre humano y tranquilizador sin minimizar el riesgo.

FIN DEL MÓDULO MAESTRO 12 — QUEMADURAS
CERRADO / CON BROCHE DE ORO / BAJO LLAVE


"""


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
    message = str(payload.get("Body") or "").strip()
    if not message:
            message = "Hola"
    try:
                response = client.responses.create(
                            model="gpt-5-mini",
                            instructions=SYSTEM_PROMPT,
                            input=message,
                            max_output_tokens=300,
                        )
                reply = response.output_text or "No pude generar una respuesta. Por favor, intenta nuevamente."
    except Exception as e:
                    print(f"OpenAI error: {e}")
                    reply = "En este momento no puedo responder. Por favor, intenta nuevamente en unos minutos."
    reply = reply.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Response(f"<Response><Message>{reply}</Message></Response>", mimetype="application/xml")
    


@app.errorhandler(404)
def not_found(_error: Any) -> tuple[str, int]:
    return render_template("404.html"), 404


init_database()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
