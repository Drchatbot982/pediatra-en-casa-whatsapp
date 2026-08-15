"""Development launcher kept for the existing Replit workflow."""

from app import app


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(__import__("os").environ.get("PORT", "5000")),
        debug=False,
    )