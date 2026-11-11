# Mi Tienda

Aplicación web de gestión de productos, categorías, marcas y clientes creada con Django.

## Requisitos

- Python 3.12
- Django 5.1.15

## Instalación en Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

La aplicación queda disponible en <http://127.0.0.1:8000/>. Las migraciones incluyen datos de ejemplo. La base local `db.sqlite3` no se incluye en el repositorio.

## Configuración

En desarrollo, Django genera una clave secreta aleatoria al iniciar. Para configurar una clave fija, establece `DJANGO_SECRET_KEY` en el entorno. En producción, también configura `DJANGO_DEBUG=False` y los hosts permitidos antes de desplegar.
