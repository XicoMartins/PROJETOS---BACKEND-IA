# 🚀 GUIA DE SETUP - WINDOWS

## ✅ Pré-requisitos Verificados

- ✅ Python 3.12 instalado
- ✅ Git instalado (`git version 2.54.0.windows.1`)
- ✅ Virtual Environment criado em `venv/`
- ✅ Dependências sendo instaladas

---

## 📋 Passo a Passo Setup Local

### 1️⃣ Ativar Virtual Environment

**PowerShell (Recomendado):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.\venv\Scripts\activate.bat
```

Se der erro de execução, execute primeiro:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2️⃣ Verificar Instalação de Dependências

```powershell
pip list
```

Deve incluir:
- streamlit >= 1.39
- pandas >= 2.0
- openpyxl >= 3.1
- python-dotenv >= 1.0

Se faltarem, instale manualmente:
```powershell
pip install -r requirements.txt
```

### 3️⃣ Testar a Aplicação

```powershell
streamlit run streamlit_app.py
```

**Esperado:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Abra seu navegador em: **http://localhost:8501**

### 4️⃣ Testes da Funcionalidade

Na interface Streamlit:

- [ ] **Tab "Lançamento":** Formulário aparece completo?
  - [ ] Consegue selecionar Cliente
  - [ ] Consegue selecionar Processo
  - [ ] Consegue selecionar Acabado
  - [ ] Consegue selecionar Ferramental
  - [ ] Consegue selecionar Operador
  - [ ] Consegue preencher Quantidade
  - [ ] Botão "Salvar Registro" funciona?

- [ ] **Tab "Consulta":** 
  - [ ] Listagem de registros aparece?
  - [ ] Consegue filtrar por Data?
  - [ ] Consegue exportar CSV?
  - [ ] Consegue deletar registros?

### 5️⃣ Verificar Banco de Dados

O banco SQLite será criado em:
```
~/.mtech/production.db
```

Para verificar:
```powershell
ls $env:USERPROFILE\.mtech\
```

---

## 📝 Estrutura do Projeto

```
PROJETOS---BACKEND-IA/
├── streamlit_app.py          # 🎯 Aplicação principal
├── requirements.txt          # 📦 Dependências
├── README.md                 # 📚 Documentação
├── SETUP_WINDOWS.md          # 📋 Este guia
├── .gitignore                # 🚫 Arquivos ignorados
├── .streamlit/
│   └── config.toml          # ⚙️ Configuração Streamlit
├── core/
│   ├── __init__.py
│   ├── db_utils.py          # 🗄️ Database (SQLite puro)
│   └── excel_utils.py       # 📊 Leitura de planilhas
├── planilhas/               # 📋 Excel files
│   ├── LISTA DE PROCESSO *.xlsx
│   ├── ...
│   └── (19 arquivos)
├── LISTA DE OPERADORES.xlsx # 👥 Operadores
└── venv/                    # 🐍 Virtual environment
```

---

## 🔧 Troubleshooting

### ❌ Erro: "python is not recognized"
**Solução:** Use o caminho completo:
```powershell
C:\Users\PCPMTECH\AppData\Local\Programs\Python\Python312\python.exe --version
```

### ❌ Erro: "git is not recognized"
**Solução:** Adicione Git ao PATH:
```powershell
$env:PATH += ";C:\Program Files\Git\cmd"
git --version
```

### ❌ Erro: "ModuleNotFoundError: No module named 'streamlit'"
**Solução:** Confirme venv ativado:
```powershell
(venv) PS C:\...> pip install streamlit
```

### ❌ Erro: "FileNotFoundError: planilhas"
**Solução:** Verifique se pasta existe:
```powershell
ls planilhas/
# Deve listar os 19 arquivos .xlsx
```

### ❌ Erro: "sqlite3.OperationalError"
**Solução:** Verifique permissões em:
```powershell
ls $env:USERPROFILE\.mtech\
```

---

## 🚀 Deploy em Streamlit Cloud

### 1. Preparar para Deploy

```powershell
# Commit local
git add .
git commit -m "setup: Pronto para Streamlit Cloud"
git push origin main
```

### 2. Conectar em Streamlit Cloud

1. Acesse: https://streamlit.io/cloud
2. Login com GitHub
3. Clique: **"New app"**
4. Selecione:
   - Repository: `XicoMartins/PROJETOS---BACKEND-IA`
   - Branch: `main`
   - Main file: `streamlit_app.py`
5. Clique: **"Deploy"**
6. ⏳ Aguarde 2-3 minutos

### 3. Verificar Deploy

Após deploy, seu app estará em:
```
https://<seu-nome-app>.streamlit.app
```

Testes em Produção:
- [ ] App carrega sem erros
- [ ] Formulário funciona
- [ ] Consegue salvar registros
- [ ] Consulta mostra dados

---

## 📊 Informações da Aplicação

**Nome:** FORMS-MTECH (Refatorado)  
**Tipo:** Streamlit Web App  
**Backend:** SQLite (sem Django)  
**Linguagem:** Python 3.12  
**Objetivo:** Controle de Produção MTECH Displays  

---

## 📞 Suporte Rápido

| Problema | Solução |
|----------|---------|
| Venv não ativa | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned` |
| Pip não encontra pacotes | `pip install --upgrade pip` |
| Porta 8501 em uso | `streamlit run streamlit_app.py --server.port 8502` |
| Banco não encontrado | `mkdir $env:USERPROFILE\.mtech` |
| Planilhas não carregam | `xcopy planilhas\ | Verifique caminhos` |

---

## ✅ Checklist Final

- [ ] Python 3.12 ✅
- [ ] Git instalado ✅
- [ ] Venv criado ✅
- [ ] Dependências instaladas ✅
- [ ] Planilhas copiadas ✅
- [ ] Testes locais OK ✅
- [ ] Código no GitHub ✅
- [ ] Deploy em Streamlit Cloud ✅

---

**Status:** ✅ **PRONTO PARA USO**

Próximo passo: Executar `streamlit run streamlit_app.py`

