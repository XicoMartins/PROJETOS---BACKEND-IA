# 🚀 INICIAR APLICAÇÃO STREAMLIT
# Script para ativar venv e rodar app automaticamente

# Permitir execução de scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Ir para pasta do projeto
$projectPath = "s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA"
cd $projectPath

Write-Host "📂 Navegando para: $projectPath" -ForegroundColor Green

# Ativar virtual environment
Write-Host "🐍 Ativando Virtual Environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Verificar se venv está ativado
if ($env:VIRTUAL_ENV) {
    Write-Host "✅ Virtual Environment ativado: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "⚠️  Atenção: Virtual Environment pode não ter ativado corretamente" -ForegroundColor Yellow
}

# Rodar Streamlit
Write-Host "`n🚀 Iniciando Streamlit App..." -ForegroundColor Cyan
Write-Host "⏳ A aplicação abrirá em: http://localhost:8501" -ForegroundColor Cyan
Write-Host "`nPara parar: Pressione Ctrl + C`n" -ForegroundColor Gray

streamlit run streamlit_app.py
