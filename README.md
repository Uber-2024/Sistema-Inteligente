# Sistema de Ruta Inteligente

Sistema local para calcular la ruta más eficiente entre dos estaciones de una red de transporte, basado en el algoritmo de Dijkstra que se utiliza para encontrar la ruta o el camino más corto desde un punto de partida (nodo de origen) hasta los demás puntos en un mapa o red de conexiones.

## Autor y derechos

Ruta Inteligente fue creado por Uber Torres.

Copyright © 2026 Uber Torres. Todos los derechos reservados.

## Arquitectura general

La aplicación está organizada en capas:

- `app.py`: lógica de negocio, persistencia y motor de rutas.
- `web_app.py`: servidor HTTP local que expone la API y sirve la interfaz.
- `web/`: frontend estático en HTML, CSS y JavaScript.
- `network.json`: datos iniciales de la red de transporte.
- `test_app.py`: pruebas automatizadas del algoritmo y reglas de negocio.

### Capa de negocio (`app.py`)

Este archivo contiene:

- la conexión a SQLite
- la inicialización de la base de datos
- la carga del grafo desde `network.json`
- la definición de `Connection`
- la regla de accesibilidad
- el algoritmo de rutas basado en Dijkstra
- la enumeración de rutas alternativas ordenadas por tiempo

La pieza central es `RoutePlanner`, que devuelve la mejor ruta y todas las rutas posibles.

### Capa HTTP (`web_app.py`)

Este archivo lanza un servidor local con Python estándar.

Endpoints principales:

- `GET /api/stations`: devuelve la lista de estaciones disponibles.
- `POST /api/route`: recibe origen, destino y accesibilidad, y responde con:
  - la ruta ganadora
  - el tiempo total
  - todas las alternativas comparadas

Además sirve la interfaz web desde la carpeta `web/`.

### Frontend (`web/`)

La parte visual está separada en:

- `index.html`: estructura principal de la página
- `app.js`: lógica del cliente, peticiones a la API y renderizado
- `styles.css`: diseño y responsividad

## Estructura del repositorio

```text
Sistema Inteligente/
├── app.py
├── web_app.py
├── test_app.py
├── network.json
├── transport.db            # generado automáticamente
├── README.md
├── web/
│   ├── README.md
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── .venv/                  # opcional, entorno local
```

## Requisitos

- Python 3.10 o superior
- navegador moderno

No requiere paquetes externos ni dependencias adicionales.

## Cómo arrancar el sistema

### 1. Crear entorno virtual (opcional)

En Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Iniciar la aplicación web

Desde la raíz del proyecto:

```bash
python web_app.py
```

Luego abre en el navegador:

```text
http://127.0.0.1:8000
```

### 3. Ejecutar pruebas

```bash
python -m unittest -v
```

## Estructura de datos de la red

El archivo `network.json` representa la red de transporte del sistema. Su formato es:

```json
{
  "stations": [
    { "name": "Estacion A", "accessible": true },
    { "name": "Estacion B" }
  ],
  "connections": [
    {
      "origin": "Estacion A",
      "destination": "Estacion B",
      "minutes": 12,
      "line": "Metro Azul",
      "accessible": true
    }
  ]
}
```

Cada elemento de `stations` es una estación del grafo. Cada elemento de `connections` define un tramo entre dos estaciones con:

- `origin`: estación de salida
- `destination`: estación de llegada
- `minutes`: tiempo estimado del trayecto
- `line`: nombre de la línea o servicio
- `accessible`: si la conexión se considera accesible

Además, el archivo incluye una clave `"_descripcion"` con metadatos que documentan la estructura y el objetivo del dataset. Esto evita los comentarios nativos de JSON y mantiene el archivo válido y autoexplicativo.

## Flujo de datos de la aplicación

La aplicación sigue este flujo de ejecución:

```text
network.json
    ↓
app.py -> TransportDatabase.seed()
    ↓
SQLite (transport.db)
    ↓
web_app.py -> API REST / HTTP
    ↓
web/index.html + web/app.js + web/styles.css
    ↓
Usuario selecciona origen y destino
    ↓
RoutePlanner calcula rutas y alternativas
    ↓
Frontend muestra la ruta más eficiente y las comparativas
```

Este patrón mantiene la lógica de negocio separada de la interfaz y facilita pruebas, mantenimiento y futuras ampliaciones.

## Ejemplos de uso de la API

### 1. Consultar estaciones disponibles

```bash
curl http://127.0.0.1:8000/api/stations
```

Respuesta esperada:

```json
{
  "stations": [
    "Aeropuerto",
    "Centro Historico",
    "Hospital Central",
    "Terminal Norte",
    "Terminal Sur",
    "Universidad"
  ]
}
```

### 2. Consultar una ruta entre dos estaciones

```bash
curl -X POST http://127.0.0.1:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Aeropuerto",
    "destination": "Centro Historico",
    "accessible_only": false
  }'
```

Salida esperada:

```json
{
  "origin": "Aeropuerto",
  "destination": "Centro Historico",
  "total_minutes": 33,
  "stops": ["Aeropuerto", "Terminal Norte", "Centro Historico"],
  "segments": [
    {"destination": "Terminal Norte", "line": "Bus A1", "minutes": 25},
    {"destination": "Centro Historico", "line": "Metro Azul", "minutes": 8}
  ],
  "alternatives": [
    {
      "total_minutes": 33,
      "stops": ["Aeropuerto", "Terminal Norte", "Centro Historico"],
      "segments": [
        {"destination": "Terminal Norte", "line": "Bus A1", "minutes": 25},
        {"destination": "Centro Historico", "line": "Metro Azul", "minutes": 8}
      ]
    }
  ]
}
```

## Solución de problemas

### El puerto 8000 ya está ocupado

Si aparece un error de puerto en uso, cambia la configuración en `web_app.py` o cierra el proceso que lo está usando.

### La base de datos no carga correctamente

Borra el archivo `transport.db` y vuelve a arrancar la aplicación. El sistema lo regenerará con la red de ejemplo desde `network.json`.

### No hay ruta disponible

Esto puede ocurrir si:

- la estación de origen o destino es incorrecta
- la red conectada no permite ese recorrido
- se ha activado el filtro por accesibilidad y no existe una ruta accesible

### La app no sirve la interfaz web

Comprueba que has ejecutado el servidor desde la carpeta correcta:

```bash
python web_app.py
```

Y luego accede a:

```text
http://127.0.0.1:8000
```

## Datos iniciales

La red base se carga desde `network.json` y se guarda en `transport.db` la primera vez que se ejecuta la aplicación.

Si cambias la red, puedes borrar `transport.db` para reinicializar la base.

## Notas de mantenimiento

- La lógica de negocio está en `app.py` y debe mantenerse separada del frontend.
- El punto de entrada actual del sistema es `web_app.py`.
- La UI solo consume la API y no debería duplicar la lógica del backend.
- Se recomienda mantener la estructura actual para facilitar evolución y pruebas futuras.
