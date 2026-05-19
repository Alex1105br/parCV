"""Entrypoint for the application."""
from src.app import create_app

app = create_app()

if __name__ == "__main__":
    print("http://localhost:5005")
    app.run(host="0.0.0.0", port=5005, debug=True)
