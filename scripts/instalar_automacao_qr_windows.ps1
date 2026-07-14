param(
    [string]$NomeTarefa = "MTECH - Processar planilhas e QR Codes",
    [switch]$ExecutarSemLogin
)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Raiz "venv\Scripts\python.exe"
$Script = Join-Path $Raiz "scripts\automacao_planilhas_qr.py"
$Config = Join-Path $Raiz "automacao_qr\config.local.json"
$Exemplo = Join-Path $Raiz "automacao_qr\config.example.json"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}
if (-not (Test-Path -LiteralPath $Config)) {
    Copy-Item -LiteralPath $Exemplo -Destination $Config
    Write-Host "Configuração criada em $Config. Revise-a antes de executar novamente."
    exit 2
}

$Argumentos = '"{0}" --config "{1}" --aplicar' -f $Script, $Config
$Acao = New-ScheduledTaskAction -Execute $Python -Argument $Argumentos -WorkingDirectory $Raiz
$Inicio = (Get-Date).AddMinutes(1)
$Gatilho = New-ScheduledTaskTrigger -Once -At $Inicio `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$Configuracoes = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

if ($ExecutarSemLogin) {
    $Credencial = Get-Credential -Message "Conta Windows com acesso à pasta do projeto"
    $Usuario = $Credencial.UserName
    $Senha = $Credencial.GetNetworkCredential().Password
    Register-ScheduledTask -TaskName $NomeTarefa -Action $Acao -Trigger $Gatilho `
        -Settings $Configuracoes -User $Usuario -Password $Senha -RunLevel Limited -Force | Out-Null
} else {
    $Usuario = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $Principal = New-ScheduledTaskPrincipal -UserId $Usuario `
        -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $NomeTarefa -Action $Acao -Trigger $Gatilho `
        -Settings $Configuracoes -Principal $Principal -Force | Out-Null
}

Write-Host "Tarefa instalada: $NomeTarefa"
Write-Host "A planilha atual continua sendo o modelo; nenhuma planilha-modelo nova foi criada."
