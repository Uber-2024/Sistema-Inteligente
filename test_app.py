# Herramientas para crear una base temporal y ejecutar pruebas automatizadas.
import tempfile
import unittest
from pathlib import Path

# Importa el motor de rutas y la persistencia que se van a comprobar.
from app import RoutePlanner, TransportDatabase


class RoutePlannerTests(unittest.TestCase):
    # Comprueba que Dijkstra elige la combinación con menor tiempo total.
    def test_finds_fastest_route(self):
        # Cada prueba usa una base temporal para no modificar la red real.
        database = TransportDatabase(Path(tempfile.mktemp(suffix=".db")))
        try:
            database.add_connection("A", "B", 5, "Bus")
            database.add_connection("B", "C", 7, "Metro")
            database.add_connection("A", "C", 20, "Bus")
            route, total = RoutePlanner().find_route(database.connections(), "A", "C")
            self.assertEqual(total, 12)
            self.assertEqual([item.destination for item in route], ["B", "C"])
        finally:
            database.close()

    def test_accessibility_rule_excludes_connection(self):
        # Verifica que una conexión no accesible sea descartada por la regla.
        database = TransportDatabase(Path(tempfile.mktemp(suffix=".db")))
        try:
            database.add_connection("A", "B", 2, "Escaleras", accessible=False)
            database.add_connection("A", "C", 5, "Ascensor", accessible=True)
            database.add_connection("C", "B", 5, "Metro", accessible=True)
            route, total = RoutePlanner().find_route(database.connections(), "A", "B", accessible_only=True)
            self.assertEqual(total, 10)
            self.assertEqual([item.destination for item in route], ["C", "B"])
        finally:
            database.close()

    # Comprueba que las alternativas se ordenen desde la más rápida.
    def test_lists_all_routes_in_time_order(self):
        database = TransportDatabase(Path(tempfile.mktemp(suffix=".db")))
        try:
            database.add_connection("A", "B", 5, "Bus")
            database.add_connection("B", "D", 7, "Metro")
            database.add_connection("A", "C", 3, "Bus")
            database.add_connection("C", "D", 20, "Bus")
            alternatives = RoutePlanner().find_all_routes(database.connections(), "A", "D")
            self.assertEqual([total for _, total in alternatives], [12, 23])
            self.assertEqual(alternatives[0][0][-1].destination, "D")
        finally:
            database.close()


if __name__ == "__main__":
    # Permite ejecutar este archivo directamente desde la terminal.
    unittest.main()