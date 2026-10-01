@echo off
setlocal
cd /d "%~dp0"

REM =====================================================================
REM  CONTROLE DE TINTA E TONER - FILIAIS
REM  Iniciador do sistema (versao Reflex - web local).
REM  -------------------------------------------------------------------
REM  O que este arquivo faz:
REM    1. Localiza o Python no computador (pythonw, python ou py).
REM    2. Instala o Reflex se ele ainda nao estiver instalado
REM       (somente na primeira vez; precisa de internet).
REM    3. Cria a estrutura do app Reflex (reflex init) se ainda nao
REM       existir - somente na primeira vez.
REM    4. Abre o navegador em http://localhost:3000 apos ~4 segundos.
REM    5. Inicia o servidor do sistema (py -m reflex run).
REM
REM  Para fechar o sistema: feche esta janela ou pressione Ctrl+C.
REM  O banco de dados fica em: controle_suprimentos.db (faca backup).
REM =====================================================================

:: 1) Encontrar Python
set "PYTHON_CMD="

where pythonw >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=pythonw"
    goto :found_python
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto :found_python
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
    goto :found_python
)

:: Nenhum Python encontrado: orienta o usuario
echo.
echo  Python nao foi encontrado neste computador.
echo  Instale o Python em https://www.python.org/downloads/
echo  (marque a opcao "Add python.exe to PATH" durante a instalacao)
echo  e tente novamente.
echo.
pause
exit /b 1

:found_python
echo.
echo  ====================================
echo   Controle de Tinta e Toner - Filiais
echo  ====================================
echo.

:: 2) Garantir que o Reflex esta instalado (primeira execucao)
%PYTHON_CMD% -c "import reflex" >nul 2>nul
if %errorlevel% neq 0 (
    echo  Instalando Reflex (primeira vez, precisa de internet)...
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo.
        echo  Erro ao instalar Reflex. Verifique sua conexao com a internet.
        echo  Ou instale manualmente: pip install reflex
        echo.
        pause
        exit /b 1
    )
    echo  Reflex instalado com sucesso!
    echo.
)

:: 3) Criar a estrutura do app na primeira execucao (arquivo rxconfig.py)
if not exist rxconfig.py (
    echo  Inicializando o app Reflex (primeira vez)...
    %PYTHON_CMD% -m reflex init --name app_reflex --template blank --no-agents
    if %errorlevel% neq 0 (
        echo.
        echo  Erro ao inicializar o app Reflex.
        echo.
        pause
        exit /b 1
    )
)

:: 4) Abrir o navegador apos ~4 segundos (dar tempo do servidor iniciar)
start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:3000"

:: 5) Iniciar o servidor Reflex (http://localhost:3000)
echo  Iniciando servidor...
echo  O navegador vai abrir automaticamente.
echo  Para fechar, feche esta janela ou pressione Ctrl+C.
echo.
%PYTHON_CMD% -m reflex run