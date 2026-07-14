# Automação de novas planilhas e QR Codes

## Situação atual

- A base possui IDs globais de seis dígitos.
- IDs existentes nunca devem ser renumerados.
- O gerador em lote cria um QR por processo e valida duplicidades entre planilhas.

## Opção recomendada agora: serviço no Windows

Executar a automação em um único computador ou servidor que permaneça ligado e tenha
acesso à unidade `S:`. O Agendador de Tarefas pode executar a verificação a cada minuto.

Fluxo esperado:

1. Detectar uma planilha nova na pasta `planilhas`.
2. Ignorar arquivos temporários iniciados por `~$`.
3. Aguardar o arquivo parar de mudar antes de abri-lo.
4. Criar um backup.
5. Validar `CLIENTE`, `ACABADO`, `FERRAMENTAL` e `PROCESSO`.
6. Reservar os próximos IDs globais em uma transação.
7. Preencher somente linhas sem `PROCESSO_ID`.
8. Salvar primeiro em arquivo temporário e substituir o original somente após validar.
9. Gerar os QR Codes novos e atualizar o manifesto.
10. Registrar sucesso ou erro em log.

Para impedir que dois computadores distribuam o mesmo ID, somente uma máquina deve
executar esse serviço. A sequência deve ficar em SQLite ou no banco do sistema, com
restrição `UNIQUE` para `PROCESSO_ID`; não deve depender somente do maior valor lido
nas planilhas.

## Opção mais robusta: upload dentro do sistema

Criar uma tela administrativa **Importar planilha de processo**. O servidor valida o
arquivo, reserva os IDs no banco, devolve a planilha preenchida e disponibiliza um ZIP
com os QR Codes. Essa opção oferece histórico, permissões, mensagens de erro e evita
depender de uma pasta monitorada.

É a melhor alternativa quando a base passar a ser controlada principalmente pelo
sistema, e não diretamente pelos arquivos Excel.

## Opção integrada ao GitHub

Uma GitHub Action pode executar quando uma nova planilha for enviada para `planilhas/`.
Ela valida a base, preenche os IDs, gera os QR Codes e cria um commit ou pull request.

Essa opção funciona bem quando todas as planilhas entram pelo GitHub, mas não detecta
um arquivo colocado apenas na unidade `S:` enquanto ele não for enviado ao repositório.

## Controles obrigatórios

- Não alterar IDs que já existem.
- Validar IDs vazios, inválidos e duplicados globalmente.
- Preservar códigos como texto e zeros à esquerda.
- Ignorar arquivos `~$` do Excel.
- Manter backup anterior a cada processamento.
- Usar trava para impedir duas execuções simultâneas.
- Registrar planilha, aba, linha, ID e data de criação.
- Não substituir a planilha original se qualquer validação falhar.

## Gerar novamente toda a coleção de QR Codes

```powershell
python scripts\gerar_qr_base.py `
  --diretorio "planilhas" `
  --saida "qrcodes_processos\base_completa" `
  --modo id
```
