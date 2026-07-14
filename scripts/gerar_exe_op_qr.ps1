param(
    [switch]$InstalarDependencias
)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Raiz "venv\Scripts\python.exe"
$Saida = Join-Path $Raiz "output\executavel_op_qr"
$Nome = "MTECH - QR nas OPs"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Ambiente virtual não encontrado: $Python"
}
if ($InstalarDependencias) {
    & $Python -m pip install -r (Join-Path $Raiz "requirements-op-qr.txt")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências" }
}

& $Python -c "import PyInstaller, pypdf, pdfplumber, reportlab"
if ($LASTEXITCODE -ne 0) {
    throw "Dependências ausentes. Execute novamente com -InstalarDependencias"
}

New-Item -ItemType Directory -Path $Saida -Force | Out-Null
Push-Location $Raiz
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name $Nome `
        --distpath $Saida `
        --workpath (Join-Path $Raiz "tmp\pyinstaller_op_qr") `
        --specpath (Join-Path $Raiz "tmp") `
        --collect-all pdfplumber `
        --exclude-module pandas `
        --exclude-module numpy `
        --exclude-module pyarrow `
        --exclude-module openpyxl `
        --exclude-module matplotlib `
        --exclude-module scipy `
        --exclude-module cv2 `
        --exclude-module streamlit `
        "apps\op_qr_app.py"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executável" }
} finally {
    Pop-Location
}

Write-Host "Executável criado em:"
Write-Host (Join-Path $Saida "$Nome.exe")
