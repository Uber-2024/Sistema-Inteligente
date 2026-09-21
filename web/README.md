# Frontend de Ruta Inteligente

Este directorio contiene la interfaz web que consume la API del backend en `web_app.py`.

## Estructura

- `index.html`: estructura principal de la interfaz.
- `app.js`: lógica del cliente, llamadas a la API y renderizado del resultado.
- `styles.css`: diseño visual, layout y responsividad.

## Flujo de la aplicación

1. La página carga la lista de estaciones desde `GET /api/stations`.
2. El usuario selecciona origen, destino y la opción de accesibilidad.
3. El formulario hace una petición `POST /api/route`.
4. El backend devuelve la ruta ganadora y todas las alternativas.
5. El frontend renderiza la ruta principal y compara las alternativas visualmente.

## Dependencias

No requiere librerías externas ni paquetes adicionales. La interfaz usa solamente:

- HTML
- CSS
- JavaScript nativo

## Uso

Se sirve desde el backend principal con:

```bash
python web_app.py
```

Luego se abre en el navegador en:

```text
http://127.0.0.1:8000
```

## Observaciones

- El archivo `index.html` no contiene lógica de negocio; solo define el layout.
- El comportamiento se mantiene en `app.js` para separar estructura, estilo y lógica.
- Los cambios visuales deben mantenerse compatibles con la API actual del backend.
