# GluteOS

Repositorio del proyecto de Ingeniería de Software 1. Se trata de una aplicación web construida con Django para apoyar la operación diaria de un gimnasio: registro de socios, cobros, control de acceso, rutinas de entrenamiento y planes nutricionales. 

## Contenido principal

- `Project/`: proyecto Django con `manage.py`, apps internas y plantillas.
- `Project/apps/`: módulos de dominio (`socios`, `pagos`, `control_acceso`, `seguridad`) más sus pruebas.
- `Project/templates/`: interfaces básicas para administradores, entrenadores y socios.
- `Documentation/`: entregables, diagramas y casos de uso en PDF.
- `Assignments/`: otros ejercicios de la materia.
- `create_test_data.py`: script que crea socios, ejercicios, rutinas y membresías de ejemplo.
- `setup.sh` y `setup.bat`: automatizan instalación, migraciones, pruebas y ejecución

## Requisitos previos

- Python 3.11 o superior y `pip`.
- Entorno virtual opcional (`python -m venv .venv`).
- Docker + Docker Compose si quieres levantar PostgreSQL con el `docker-compose.yml` incluido, o bien una instancia local de PostgreSQL 15 con las credenciales `midb` / `miuser` / `mipass`.
- Git (solo para clonar) y make opcional.

## Puesta en marcha rápida

1. Crear y activar un entorno virtual.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # En Windows: .venv\Scripts\activate
   ```
2. Instalar dependencias.
   ```bash
   pip install -r Project/requirements.txt
   ```
3. Iniciar PostgreSQL con Docker 
   ```bash
   cd Project
   docker compose up -d
   ```
   Si ya tienes PostgreSQL, ajusta los datos de conexión en `Project/Project/settings.py`.
4. Aplicar migraciones y crear un superusuario para el panel de administración.
   ```bash
   cd Project
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. (Opcional) Cargar datos de ejemplo.
   ```bash
   cd ..
   python create_test_data.py
   ```
   Este script genera un socio con usuario, planes, rutinas y mediciones para que puedas navegar la interfaz sin registrar nada manualmente.
6. Ejecutar la aplicación.
   ```bash
   cd Project
   python manage.py runserver
   ```
   Abre `http://127.0.0.1:8000/` para la aplicación y `http://127.0.0.1:8000/admin/` para el panel de Django usando el superusuario creado.

## Pruebas automatizadas

Las pruebas unitarias básicas viven dentro de cada app (`apps/*/tests`). Ejecútalas cada vez que cambies el modelo de datos:

```bash
cd Project
python manage.py test
```

El `settings.py` cambia automáticamente a SQLite en memoria cuando detecta `test` en el comando, así que no necesitas tocar la base de datos real para correr las pruebas.

## Módulos de la aplicación

- **socios**: CRUD de socios, mediciones corporales y registro diario de comidas.
- **pagos**: planes de membresía, estados de las membresías, pagos y alertas de morosidad.
- **control_acceso**: ejercicios, rutinas semanales, sesiones, planes nutricionales, comidas y asistencias al gimnasio.
- **seguridad**: roles, usuarios internos y bitácora de acciones para auditoría.

Cada módulo expone servicios, vistas y templates propios. La configuración global (idioma, zona horaria, apps instaladas) está en `Project/Project/settings.py`.

## Documentación de apoyo

Los entregables del curso (arquitectura, casos de uso, pruebas y patrones) están en `Documentation/Project`. Revísalos si necesitas contexto antes de tocar el código o justificar decisiones de diseño.

## Scripts útiles

- `setup.sh` (Linux / macOS) y `setup.bat` (Windows) encadenan instalación de dependencias, migraciones, pruebas y `runserver`. Úsalos solo si revisas antes las rutas internas.
- `create_test_data.py` puede ejecutarse cuantas veces quieras; usa `get_or_create`, así que no duplica registros ya existentes.
