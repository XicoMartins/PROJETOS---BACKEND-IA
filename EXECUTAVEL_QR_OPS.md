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

Se uma subpasta de produto for escolhida, o aplicativo localiza automaticamente a
pasta `base_completa` acima dela e corrige o caminho exibido.

## Fluxo de uso

1. Abra `MTECH - QR nas OPs.exe`.
2. Selecione a pasta das OPs.
3. Selecione a pasta base dos QR Codes.
4. Clique em **1. Analisar e associar**.
   O rodapé mostra o progresso no formato `Analisando PDF 12 de 32`.
5. Confira a tabela:
   - verde: associação automática confirmada;
   - amarelo/vermelho: exige revisão;
   - azul: associação confirmada manualmente.
6. Para um item que exige revisão, selecione a linha e clique em
   **Revisar selecionado**. É possível escolher um ou vários processos.
7. Clique em **2. Gerar PDFs com QR**.
8. Use **Abrir pasta de resultado** para acessar os arquivos prontos.

Durante o processamento, o rodapé informa separadamente as fases **Gerando
localmente**, **Validando resultado**, **Criando backup** e **Salvando na pasta
final**. O botão **Cancelar** interrompe a operação com segurança. Antes da cópia
final, nenhum arquivo parcial é mantido na pasta das OPs.

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

Durante a análise, o manifesto é mantido em cache e os PDFs são lidos em paralelo.
Os PNGs são verificados somente depois da associação e apenas para os processos que
serão efetivamente inseridos, evitando percorrer toda a base pela rede.

Na geração, até quatro PDFs são preparados e validados simultaneamente em uma pasta
temporária local. Sobreposições de QR repetidas são reutilizadas em memória. Somente
depois que todos os resultados passam nas validações os arquivos são transferidos
para a pasta sincronizada. Se houver cancelamento ou erro durante a substituição dos
originais, os PDFs já alterados são restaurados a partir do backup.

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
