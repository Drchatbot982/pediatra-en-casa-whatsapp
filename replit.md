# Twilio WhatsApp Webhook Inbox

A Flask web application that receives WhatsApp messages from Twilio, stores them in SQLite, and displays a lightweight inbox.

## Run & Operate

- `python main.py` — run the Flask webhook inbox locally
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `TWILIO_AUTH_TOKEN` — optional secret used to validate incoming Twilio signatures
- `TWILIO_VALIDATE_SIGNATURE=true` — require valid Twilio signatures
- `TWILIO_WEBHOOK_URL` — optional public webhook URL override for signature validation behind a proxy

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Web: Flask 3
- DB: SQLite (Python standard library)
- Runtime: Python 3.11
- Production server: Gunicorn

## Where things live

- `main.py` — Flask app, Twilio signature validation, SQLite persistence, and JSON API
- `templates/` — inbox dashboard and error page
- `static/styles.css` — dashboard presentation
- `data/messages.db` — local message store, created on first run

## Architecture decisions

- The webhook accepts Twilio's standard `application/x-www-form-urlencoded` payload and returns an empty TwiML response.
- MessageSid is unique so Twilio retries do not create duplicate inbox entries.
- Signature validation is opt-in for local setup and can be enforced with `TWILIO_VALIDATE_SIGNATURE=true`.

## Product

- Receive WhatsApp messages sent to a Twilio number.
- Persist message body, sender, recipient, profile name, media URLs, and the original payload.
- View recent messages and basic inbox metrics in a browser.
- Check service and database health at `/healthz`.

## User preferences

- Keep Twilio credentials in Replit Secrets or environment variables; never commit them.

## Gotchas

- When signature validation is enabled behind a proxy, set `TWILIO_WEBHOOK_URL` to the exact public URL Twilio calls.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
