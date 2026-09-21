"""Lógica principal del planificador de rutas del transporte.

Este módulo contiene la base de datos y la lógica de búsqueda de rutas que usa
la aplicación web.
"""

from __future__ import annotations

import heapq
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "transport.db"
NETWORK_PATH = BASE_DIR / "network.json"


@dataclass(frozen=True)
class Connection:
    """Representa un tramo individual entre dos estaciones del sistema de transporte."""

    origin: str
    destination: str
    minutes: int
    line: str
    accessible: bool = True


class TransportDatabase:
    """Gestiona la base de datos SQLite con estaciones y conexiones del transporte."""

    def __init__(self, path: Path = DATABASE_PATH):
        # Inicializa la base de datos en la ruta indicada y crea las tablas necesarias.
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        # Crea las tablas de estaciones y conexiones si aún no existen.
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                accessible INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin_id INTEGER NOT NULL REFERENCES stations(id),
                destination_id INTEGER NOT NULL REFERENCES stations(id),
                minutes INTEGER NOT NULL CHECK (minutes > 0),
                line TEXT NOT NULL,
                accessible INTEGER NOT NULL DEFAULT 1,
                UNIQUE(origin_id, destination_id, line)
            );
            """
        )
        self.connection.commit()

    def seed(self, network_path: Path = NETWORK_PATH) -> None:
        # Carga la red de ejemplo desde network.json solo si la base todavía está vacía.
        if self.connection.execute("SELECT 1 FROM stations LIMIT 1").fetchone():
            return

        data = json.loads(network_path.read_text(encoding="utf-8"))
        for station in data["stations"]:
            self.connection.execute(
                "INSERT INTO stations(name, accessible) VALUES (?, ?)",
                (station["name"], int(station.get("accessible", True))),
            )

        for item in data["connections"]:
            self.add_connection(
                item["origin"],
                item["destination"],
                item["minutes"],
                item["line"],
                item.get("accessible", True),
                commit=False,
            )
        self.connection.commit()

    def add_connection(
        self,
        origin: str,
        destination: str,
        minutes: int,
        line: str,
        accessible: bool = True,
        commit: bool = True,
    ) -> None:
        # Inserta una nueva conexión en la base de datos creando estaciones si hace falta.
        for station in (origin, destination):
            self.connection.execute(
                "INSERT OR IGNORE INTO stations(name) VALUES (?)",
                (station,),
            )

        ids = {
            row["name"]: row["id"]
            for row in self.connection.execute(
                "SELECT id, name FROM stations WHERE name IN (?, ?)",
                (origin, destination),
            )
        }

        self.connection.execute(
            """
            INSERT OR IGNORE INTO connections
                (origin_id, destination_id, minutes, line, accessible)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ids[origin], ids[destination], minutes, line, int(accessible)),
        )
        if commit:
            self.connection.commit()

    def stations(self) -> list[str]:
        # Devuelve todas las estaciones ordenadas para que la API y la interfaz puedan mostrarlas.
        rows = self.connection.execute(
            "SELECT name FROM stations ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

    def connections(self) -> list[Connection]:
        # Recupera todas las conexiones como objetos Connection para usarlas en el cálculo de rutas.
        rows = self.connection.execute(
            """
            SELECT a.name origin, b.name destination, c.minutes, c.line, c.accessible
            FROM connections c
            JOIN stations a ON a.id = c.origin_id
            JOIN stations b ON b.id = c.destination_id
            """
        ).fetchall()
        return [Connection(**dict(row)) for row in rows]

    def close(self) -> None:
        # Cierra la conexión con SQLite al finalizar la ejecución del servidor.
        self.connection.close()


class RuleEngine:
    """Aplica reglas de negocio sobre las conexiones antes de calcular una ruta."""

    def filter_connections(
        self,
        connections: list[Connection],
        accessible_only: bool,
    ) -> list[Connection]:
        # Si la opción de accesibilidad está desactivada, conserva todas las conexiones.
        # Si está activada, elimina los tramos marcados como no accesibles.
        if not accessible_only:
            return connections
        return [connection for connection in connections if connection.accessible]


class RoutePlanner:
    """Calcula la ruta más corta y recoge alternativas válidas entre dos estaciones."""

    def __init__(self, rule_engine: RuleEngine | None = None):
        # Guarda el motor de reglas para aplicar filtros antes de buscar rutas.
        self.rule_engine = rule_engine or RuleEngine()

    def find_route(
        self,
        connections: list[Connection],
        origin: str,
        destination: str,
        accessible_only: bool = False,
    ) -> tuple[list[Connection], int]:
        # Busca la ruta de menor tiempo entre dos estaciones usando un algoritmo tipo Dijkstra.
        if origin == destination:
            return [], 0

        usable = self.rule_engine.filter_connections(connections, accessible_only)
        graph: dict[str, list[Connection]] = {}
        for connection in usable:
            graph.setdefault(connection.origin, []).append(connection)

        queue: list[tuple[int, str]] = [(0, origin)]
        distances = {origin: 0}
        previous: dict[str, Connection] = {}

        while queue:
            total, current = heapq.heappop(queue)
            if total != distances[current]:
                continue
            if current == destination:
                break

            for connection in graph.get(current, []):
                new_total = total + connection.minutes
                if new_total < distances.get(connection.destination, float("inf")):
                    distances[connection.destination] = new_total
                    previous[connection.destination] = connection
                    heapq.heappush(queue, (new_total, connection.destination))

        if destination not in distances:
            raise ValueError("No existe una ruta con las condiciones seleccionadas.")

        route: list[Connection] = []
        current = destination
        while current != origin:
            connection = previous[current]
            route.append(connection)
            current = connection.origin
        route.reverse()
        return route, distances[destination]

    def find_all_routes(
        self,
        connections: list[Connection],
        origin: str,
        destination: str,
        accessible_only: bool = False,
        max_routes: int = 1000,
    ) -> list[tuple[list[Connection], int]]:
        # Genera todas las rutas simples válidas hasta un límite máximo y las ordena por duración.
        if origin == destination:
            return [([], 0)]

        usable = self.rule_engine.filter_connections(connections, accessible_only)
        graph: dict[str, list[Connection]] = {}
        for connection in usable:
            graph.setdefault(connection.origin, []).append(connection)

        alternatives: list[tuple[list[Connection], int]] = []

        def explore(
            current: str,
            visited: set[str],
            route: list[Connection],
            total: int,
        ) -> None:
            # Recorre el grafo explorando caminos sin repetir estaciones para construir alternativas.
            if len(alternatives) >= max_routes:
                return
            if current == destination:
                alternatives.append((route.copy(), total))
                return

            for connection in graph.get(current, []):
                if connection.destination not in visited:
                    explore(
                        connection.destination,
                        visited | {connection.destination},
                        route + [connection],
                        total + connection.minutes,
                    )

        explore(origin, {origin}, [], 0)
        alternatives.sort(key=lambda item: (item[1], len(item[0])))
        return alternatives
