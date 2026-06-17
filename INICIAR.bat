@echo off
REM Script para iniciar Streamlit App no Windows (Command Prompt)
REM Duplo-clique para executar!

SETLOCAL ENABLEDELAYEDEXPANSION

REM Definir cor e título
title FORMS-MTECH Streamlit App
color 0A

echo.
echo ============================================
echo     INICIAR STREAMLIT - FORMS-MTECH
echo ============================================
echo.

REM Navegar para pasta do projeto
cd /d "s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA"

echo 📂 Pasta: %cd%
echo.

REM Ativar virtual environment
echo 🐍 Ativando Virtual Environment...
call venv\Scripts\activate.bat

echo ✅ Virtual Environment ativado!
echo.

REM Rodar Streamlit
echo 🚀 Iniciando Streamlit App...
echo.
echo ⏳ Aguarde... a aplicação abrirá em http://localhost:8501
echo.
echo Para parar: Feche esta janela ou pressione Ctrl + C
echo.
echo ============================================
echo.

streamlit run streamlit_app.py

REM Se chegar aqui, a app foi parada
echo.
echo ============================================
echo     APP FINALIZADO
echo ============================================
pause
