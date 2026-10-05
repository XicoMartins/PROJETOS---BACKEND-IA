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

Quando a seção `painel` está habilitada na configuração, a mesma planilha já
preenchida com `PROCESSO_ID` também é publicada no outro projeto:

- produção: `planilhas`;
- pintura: `planilhas_pintura`.

Antes de processar, a automação valida e atualiza os dois repositórios. Ao final,
cria commits separados e executa o push do backend e do painel. Imagens novas ou
atualizadas em `FOTOS DISPLAY`, nos formatos `.png`, `.jpg`, `.jpeg` e `.webp`,
são publicadas automaticamente mesmo quando não há planilha na fila. Alterações
fora dessa pasta continuam bloqueando o processamento por segurança.

Arquivos temporários do Excel (`~$...xlsx`) são ignorados. Se o arquivo ainda estiver
sendo salvo, ele fica na entrada e é verificado novamente na próxima execução.

## Segurança da sequência

- IDs existentes nunca são alterados ou reutilizados.
- A sequência é global entre produção e pintura.
- Antes de reservar novos números, toda a base é validada contra duplicidades.
- Um mesmo produto acabado não pode existir em duas planilhas com nomes diferentes;
  para alterá-lo, reutilize o nome do arquivo já publicado.
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
},
"painel": {
  "publicar": true,
  "raiz_projeto": "S:/caminho/PROJETOS - PAINEL PRODUÇÃO IA",
  "base_producao": "planilhas",
  "base_pintura": "planilhas_pintura",
  "github": {
    "sincronizar": true,
    "branch": "main"
  }
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

Se houver alterações fora das pastas controladas pela automação ou o `pull` falhar,
nenhuma planilha é processada. Uma imagem ainda sendo copiada fica aguardando o
próximo ciclo e não gera erro.

## Passo a passo para o colaborador

### Antes do envio

1. Confirme se a planilha é de **produção** ou **pintura**.
2. Salve e feche a planilha no Excel antes de copiá-la.
3. Prepare a imagem do produto em `.png`, `.jpg`, `.jpeg` ou `.webp`.
4. Use um nome fácil de reconhecer e correspondente ao produto, por exemplo:
   `PG BACKLIGHT MOD 6.png`.

### Enviar a imagem

1. Abra o projeto do painel na rede:
   `S:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS - PAINEL PRODUÇÃO IA`.
2. Copie a imagem para a pasta `FOTOS DISPLAY`.
3. Aguarde a cópia terminar. Não é necessário fazer commit ou abrir o GitHub.

### Enviar a planilha

- Para produção, copie a planilha fechada para:
  `S:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA\automacao_qr\entrada\producao`.
- Para pintura, copie a planilha fechada para:
  `S:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA\automacao_qr\entrada\pintura`.

Não copie arquivos temporários cujo nome começa com `~$`.

### Conferir o resultado

1. Aguarde até dois minutos.
2. Quando o processamento terminar, a planilha sairá da pasta `entrada` e irá para
   `automacao_qr\processados`.
3. A planilha com os IDs, os QR Codes, a imagem e os commits serão publicados
   automaticamente.
4. Se a planilha for movida para `automacao_qr\rejeitados`, abra o arquivo
   `.erro.txt` que estará ao lado dela e encaminhe a mensagem ao responsável pelo
   sistema.

O colaborador não precisa executar comandos, criar commits ou fazer push manual.

## Uso de recursos

A tarefa não mantém um serviço Python residente. Ela abre, verifica a fila e encerra.
Sem arquivo novo, o consumo dura poucos segundos por minuto. Excel não precisa ficar
aberto. Com o computador desligado, a automação local não executa; a opção
`StartWhenAvailable` faz o Windows rodar a verificação quando o computador voltar.
