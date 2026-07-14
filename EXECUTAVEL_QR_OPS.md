# MTECH - QR Codes nas OPs

O aplicativo `MTECH - QR nas OPs.exe` permite que o analista selecione uma pasta de
Ordens de Produção em PDF e a pasta da base de QR Codes. Ele identifica os processos,
mostra as associações para conferência e insere os QRs na área **Imagem do Produto**.

## Executável

O arquivo gerado fica em:

```text
output\executavel_op_qr\MTECH - QR nas OPs.exe
```

Ele é portátil: o computador do analista não precisa ter Python instalado. O Windows
pode apresentar um aviso na primeira execução porque o arquivo é interno e não possui
assinatura digital comercial.

## Pastas selecionadas

**Pasta das OPs:** pasta que contém os PDFs a serem analisados.

**Pasta dos QR Codes:** deve ser a pasta `qrcodes_processos\base_completa`, contendo:

- `manifesto_qr.json`;
- uma subpasta para cada lista de processos;
- os arquivos PNG dos QR Codes.

## Fluxo de uso

1. Abra `MTECH - QR nas OPs.exe`.
2. Selecione a pasta das OPs.
3. Selecione a pasta base dos QR Codes.
4. Clique em **1. Analisar e associar**.
5. Confira a tabela:
   - verde: associação automática confirmada;
   - amarelo/vermelho: exige revisão;
   - azul: associação confirmada manualmente.
6. Para um item que exige revisão, selecione a linha e clique em
   **Revisar selecionado**. É possível escolher um ou vários processos.
7. Clique em **2. Gerar PDFs com QR**.
8. Use **Abrir pasta de resultado** para acessar os arquivos prontos.

## Saída segura

Por padrão, o aplicativo cria uma pasta nova ao lado da pasta das OPs:

```text
OPS_COM_QR_AAAAMMDD_HHMMSS
```

Os originais não são alterados.

Se a opção **Substituir PDFs originais** for marcada, o aplicativo cria primeiro uma
pasta `BACKUP_OPS_ANTES_QR_AAAAMMDD_HHMMSS`. Todos os PDFs são gerados e validados
antes da substituição.

## Validações

- O produto precisa existir no manifesto.
- O arquivo PNG informado pelo manifesto precisa existir.
- Associações ambíguas bloqueiam o processamento até a revisão.
- A quantidade e o tamanho das páginas devem permanecer iguais.
- Todos os IDs associados precisam aparecer no PDF final.
- PDFs que já contêm QR são bloqueados, salvo quando a opção de reprocessamento for
  marcada conscientemente.
- Um relatório `RELATORIO_QR_OPS.json` é salvo junto aos PDFs gerados.

## Gerar novamente o executável

Na primeira vez:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\gerar_exe_op_qr.ps1 `
  -InstalarDependencias
```

Nas próximas versões:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\gerar_exe_op_qr.ps1
```
