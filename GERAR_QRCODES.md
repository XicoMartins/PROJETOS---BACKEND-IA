# Geração de QR Codes dos processos

O gerador lê a coluna `PROCESSO_ID`, valida os dados e cria um PNG por linha.
Por padrão, cada QR contém somente o ID de seis dígitos.

## Instalação

```powershell
pip install -r requirements.txt
```

## Gerar o piloto DISPLAY ARAMADO P PILÃO

Execute na pasta principal do projeto:

```powershell
python scripts\gerar_qr_processos.py `
  --arquivo "planilhas\LISTA DE PROCESSO DISPLAY ARAMADO P PILÃO.xlsx" `
  --saida "qrcodes_processos\display_aramado_p_pilao" `
  --modo id
```

O resultado será uma pasta com os PNGs e um `manifesto_qr.json` para conferência.

Exemplos:

```text
000001_15X15_NEST_1.png
000002_15X15_NEST_2.png
...
000029_APOIO_RODIZIO.png
```

## Gerar QR com URL completa

Quando a tela do formulário já aceitar `processo_id` pela URL:

```powershell
python scripts\gerar_qr_processos.py `
  --arquivo "planilhas\LISTA DE PROCESSO DISPLAY ARAMADO P PILÃO.xlsx" `
  --saida "qrcodes_processos\display_aramado_p_pilao_url" `
  --modo url `
  --url-base "https://formsmtech.streamlit.app/"
```

No modo URL, o conteúdo será semelhante a:

```text
https://formsmtech.streamlit.app/?processo_id=000001
```

Para o leitor QR USB do computador do supervisor, use preferencialmente `--modo id`.

## Usar no formulário

1. Abra a aba **Lançamento**.
2. O campo **Ler QR Code ou informar ID do processo** receberá o foco.
3. Leia o QR com o leitor USB; o Enter enviado pelo leitor confirma a leitura.
4. Confira Cliente, Display, Ferramental e Processo no resumo protegido.
5. Preencha manualmente código, data, horários, quantidades e operadores.
6. Use **Salvar e ler próximo** para limpar o formulário e voltar ao leitor.

Também é possível digitar um ID, como `000001`, ou abrir a aplicação com:

```text
https://formsmtech.streamlit.app/?processo_id=000001
```

O botão **Alterar dados manualmente** preserva o funcionamento anterior para exceções.
