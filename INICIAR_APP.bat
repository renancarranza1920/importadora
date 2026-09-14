@echo off
cd /d "%~dp0"
set "APP_ENV=local"
python -c "import streamlit, sqlalchemy, PIL, tzdata" >nul 2>&1
if errorlevel 1 (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)
python scripts\setup_local.py
if errorlevel 1 (
    pause
    exit /b 1
)
echo Abre http://localhost:8501 y consulta ACCESO_LOCAL.txt para la clave.
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
pause
