"""
WSGI entry point for Liara deployment
"""
from app import app

if __name__ == "__main__":
    app.run()
