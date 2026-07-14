# Automação local de planilhas e QR Codes

## O que foi mantido

O analista continua criando a lista de processos no modelo Excel que já utiliza hoje.
Não foi criado um modelo novo e não é necessário copiar os dados para outro formato.

A automação apenas acrescenta a coluna `PROCESSO_ID` quando ela não existe, preenche
os IDs vazios com a sequência global de seis dígitos e preserva as demais abas,
fórmulas, valores e formatação do arquivo.

## Fluxo

1. O analista salva uma **cópia fechada** da planilha em uma das pastas de entrada:
   - `automacao_qr\entrada\producao`
   - `automacao_qr\entrada\pintura`
2. A tarefa do Windows executa uma verificação curta a cada minuto.
3. O arquivo é validado sem alterar a base.
4. Os próximos IDs globais são reservados no SQLite local.
5. Uma cópia de segurança do arquivo recebido é criada.
6. A planilha preenchida é publicada em `planilhas` ou `PINTURA`.
7. Um QR PNG por processo é criado em `qrcodes_processos\base_completa`.
8. O manifesto global é atualizado.
9. O arquivo recebido vai para `automacao_qr\processados`.
10. Se houver erro de conteúdo, o arquivo vai para `automacao_qr\rejeitados` junto
    de um arquivo `.erro.txt` explicando o motivo.

Arquivos temporários do Excel (`~$...xlsx`) são ignorados. Se o arquivo ainda estiver
sendo salvo, ele fica na entrada e é verificado novamente na próxima execução.

## Segurança da sequência

- IDs existentes nunca são alterados ou reutilizados.
- A sequência é global entre produção e pintura.
- Antes de reservar novos números, toda a base é validada contra duplicidades.
- A reserva usa uma transação SQLite e uma trava impede duas execuções simultâneas.
- Se uma execução falhar após reservar números, pode haver um salto na sequência.
  Isso é intencional: um ID reservado nunca é reaproveitado.
- A planilha original da base não é substituída; uma nova lista com nome já existente
  é rejeitada para evitar sobrescrita acidental.

## Preparar a configuração local

Copie `automacao_qr\config.example.json` para
`automacao_qr\config.local.json`. O arquivo local não entra no Git.

Na fase piloto, mantenha:

```json
"github": {
  "sincronizar": false,
  "branch": "main"
}
```

Assim, a automação local gera os arquivos, mas não faz commit nem push sozinha.

## Testar sem alterar nada

Coloque uma cópia de uma nova planilha na pasta de entrada e execute:

```powershell
.\venv\Scripts\python.exe scripts\automacao_planilhas_qr.py `
  --config automacao_qr\config.local.json `
  --tipo producao
```

Sem `--aplicar`, o programa apenas valida e informa quais IDs seriam usados.

Para testar um arquivo específico sem colocá-lo na fila:

```powershell
.\venv\Scripts\python.exe scripts\automacao_planilhas_qr.py `
  --config automacao_qr\config.local.json `
  --tipo producao `
  --arquivo "C:\caminho\LISTA DE PROCESSO TESTE.xlsx"
```

## Efetivar manualmente no piloto

```powershell
.\venv\Scripts\python.exe scripts\automacao_planilhas_qr.py `
  --config automacao_qr\config.local.json `
  --tipo producao `
  --aplicar
```

Troque `producao` por `pintura` quando necessário.

## Instalar no Agendador de Tarefas

O instalador foi criado, mas não deve ser executado antes do teste piloto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_automacao_qr_windows.ps1
```

No modo padrão, a tarefa usa a conta atual e funciona enquanto essa conta estiver
conectada ao Windows. Para executar mesmo sem login, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_automacao_qr_windows.ps1 `
  -ExecutarSemLogin
```

Nesse modo, informe uma conta que tenha acesso à pasta de rede. Para execução sem
login, prefira caminhos UNC no `config.local.json`, pois a unidade `S:` pode não estar
mapeada para a tarefa.

## Publicação automática no GitHub

Após o piloto local estar validado, `github.sincronizar` pode ser alterado para
`true`. Nesse modo a automação:

1. exige que o repositório esteja sem alterações pendentes;
2. executa `git pull --ff-only` antes de processar;
3. adiciona somente a nova planilha, seus QRs e o manifesto;
4. cria um commit e envia para a branch configurada.

Se o repositório estiver sujo ou o `pull` falhar, nenhuma planilha é processada.

## Uso de recursos

A tarefa não mantém um serviço Python residente. Ela abre, verifica a fila e encerra.
Sem arquivo novo, o consumo dura poucos segundos por minuto. Excel não precisa ficar
aberto. Com o computador desligado, a automação local não executa; a opção
`StartWhenAvailable` faz o Windows rodar a verificação quando o computador voltar.
