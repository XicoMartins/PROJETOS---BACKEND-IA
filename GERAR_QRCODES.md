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

## Ler pela câmera do celular

Nas telas de lançamento de produção e pintura, abra **Ler QR Code pela câmera do celular** e toque em **Iniciar câmera**. A leitura é contínua enquanto a câmera estiver aberta e para automaticamente assim que um QR Code válido for identificado.

O vídeo é analisado diretamente no navegador do celular: somente o conteúdo decodificado do QR Code é enviado ao Streamlit. Por isso, o leitor principal não depende de transmissão WebRTC nem de configuração STUN/TURN. O acesso à câmera exige HTTPS e a permissão do usuário no navegador.

As opções anteriores continuam disponíveis:

- leitor QR USB ou digitação manual no campo de identificação;
- QR contendo apenas o `PROCESSO_ID` ou uma URL completa;
- **Leitor alternativo por transmissão de vídeo**, mantido temporariamente como contingência.

Caso o navegador não encontre a câmera, confira a permissão de câmera do site e teste novamente pelo Safari ou Chrome atualizado.

## Atualizar o componente da câmera

O arquivo compilado do leitor já faz parte do repositório e não precisa ser gerado durante a publicação do Streamlit. Somente ao alterar `components/qr_scanner/src/scanner.js`, instale as dependências e recompile:

```powershell
cd components\qr_scanner
pnpm install --store-dir "$env:LOCALAPPDATA\Temp\mtech-pnpm-store" --config.node-linker=hoisted
pnpm run build
```

O `store-dir` local evita a criação de links simbólicos incompatíveis com a unidade de rede `S:`.

Depois, versione também `components/qr_scanner/dist/scanner.js`.

## Gerar os QR Codes de toda a base

Para processar todas as planilhas da pasta `planilhas` em uma única execução:

```powershell
python scripts\gerar_qr_base.py `
  --diretorio "planilhas" `
  --diretorio "PINTURA" `
  --saida "qrcodes_processos\base_completa" `
  --modo id
```

O gerador valida duplicidades entre planilhas e cria um único
`manifesto_qr.json`, contendo também o nome da planilha de origem. Os PNGs
ficam separados em uma subpasta com o mesmo nome de cada planilha.
