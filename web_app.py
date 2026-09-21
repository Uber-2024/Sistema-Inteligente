"""Servidor web local para el planificador de rutas del transporte.

Este archivo conserva la API HTTP y el comportamiento actual del cliente,
pero organiza el servidor con una estructura más limpia y mantenible.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app import DATABASE_PATH, RoutePlanner, TransportDatabase

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


class RequestHandler(BaseHTTPRequestHandler):
    """Atiende las peticiones HTTP de la interfaz y de la API REST del sistema."""

    database = TransportDatabase(DATABASE_PATH)
    database.seed()
    planner = RoutePlanner()

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        # Envía una respuesta HTTP genérica con cuerpo, tipo de contenido y código de estado.
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: object, status: int = 200) -> None:
        # Serializa un objeto Python a JSON y lo devuelve como respuesta HTTP.
        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        # Maneja las peticiones GET para devolver estaciones, recursos web y la página principal.
        path = urlparse(self.path).path
        if path == "/api/stations":
            self._send_json({"stations": self.database.stations()})
        elif path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._serve_file("app.js", "text/javascript; charset=utf-8")
        else:
            self._send_json({"error": "Recurso no encontrado"}, 404)

    def do_POST(self) -> None:
        # Procesa la petición POST para calcular una ruta con sus alternativas desde el frontend.
        if urlparse(self.path).path != "/api/route":
            self._send_json({"error": "Recurso no encontrado"}, 404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
            origin = str(payload["origin"])
            destination = str(payload["destination"])

            if origin == destination:
                raise ValueError("Origen y destino son iguales. Verifica la selección antes de continuar.")

            alternatives = self.planner.find_all_routes(
                self.database.connections(),
                origin,
                destination,
                bool(payload.get("accessible_only", False)),
            )
            if not alternatives:
                raise ValueError("No existe una ruta con las condiciones seleccionadas.")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error) or "Solicitud inválida"}, 400)
            return

        origin = str(payload["origin"])
        destination = str(payload["destination"])
        route, total = alternatives[0]
        self._send_json({
            "origin": origin,
            "destination": destination,
            "total_minutes": total,
            "stops": [origin] + [item.destination for item in route],
            "segments": [
                {"destination": item.destination, "line": item.line, "minutes": item.minutes}
                for item in route
            ],
            "alternatives": [
                {
                    "total_minutes": alternative_total,
                    "stops": [origin] + [item.destination for item in alternative_route],
                    "segments": [
                        {"destination": item.destination, "line": item.line, "minutes": item.minutes}
                        for item in alternative_route
                    ],
                }
                for alternative_route, alternative_total in alternatives
            ],
        })

    def _serve_file(self, filename: str, content_type: str) -> None:
        # Lee un archivo del directorio web y lo devuelve al navegador como recurso estático.
        try:
            body = (WEB_DIR / filename).read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "Archivo web no encontrado"}, 500)
            return
        self._send(body, content_type)

    def log_message(self, format: str, *args: object) -> None:
        # Muestra mensajes de depuración del servidor en la consola para seguimiento del tráfico HTTP.
        print(f"[web] {self.address_string()} - {format % args}")


def main() -> None:
    # Inicia el servidor HTTP local en el puerto 8000 y deja la aplicación disponible en el navegador.
    server = HTTPServer(("127.0.0.1", 8000), RequestHandler)
    print("Ruta Inteligente disponible en http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")
    finally:
        RequestHandler.database.close()
        server.server_close()


if __name__ == "__main__":
    main()