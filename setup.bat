@echo off
REM --------------------------------------------------
REM SCRIPT DE PREPARACIÓN Y EJECUCIÓN (Windows)
REM Proyecto: GluteOS
REM Asignatura: Ingeniería de Software 1
REM --------------------------------------------------

echo "Iniciando script de configuracion..."

REM --- Bloque 1: Instalación de Dependencias ---
REM Se instalan las dependencias desde la carpeta /project/
echo "Instalando dependencias (py -m pip install -r project/requirements.txt)..."
py -m pip install -r project/requirements.txt

REM --- Bloque 2: Preparación de la Base de Datos (Migraciones) ---
REM Se ejecuta migrate usando el manage.py dentro de /project/
echo "Aplicando migraciones de la BD (py project/manage.py migrate)..."
py project/manage.py migrate

REM --- Bloque 3: Ejecución de Pruebas Básicas ---
REM Se ejecutan tests usando el manage.py dentro de /project/
echo "Ejecutando pruebas (py project/manage.py test)..."
py project/manage.py test

REM --- Bloque 4: Ejecución Inicial ---
REM Se levanta el servidor usando el manage.py dentro de /project/
echo "Iniciando la aplicacion (py project/manage.py runserver)..."
py project/manage.py runserver

echo "Script finalizado."
pause