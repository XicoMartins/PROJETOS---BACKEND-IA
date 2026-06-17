# 🎯 COMO INICIAR A APLICAÇÃO - GUIA RÁPIDO

## ⚡ OPÇÃO MAIS FÁCIL - Duplo-clique (Recomendado!)

### Windows Explorer:
1. Abra: `s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA\`
2. Procure o arquivo: **`INICIAR.bat`**
3. 🖱️ Duplo-clique nele
4. 🟢 A aplicação iniciará automaticamente
5. 🌐 Abra no navegador: **http://localhost:8501**

---

## 🔧 OPÇÃO 2 - PowerShell (Para usuários avançados)

### Passo 1: Abra PowerShell
1. Clique em Iniciar
2. Digite: `PowerShell`
3. Abra "Windows PowerShell"

### Passo 2: Navegue para a pasta
```powershell
cd "s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA"
```

### Passo 3: Execute o script
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\INICIAR.ps1
```

### Passo 4: Acesse no navegador
```
http://localhost:8501
```

---

## 🖥️ OPÇÃO 3 - Command Prompt (CMD)

### Passo 1: Abra Command Prompt
1. Clique em Iniciar
2. Digite: `cmd`
3. Abra "Command Prompt"

### Passo 2: Navegue para a pasta
```cmd
cd /d "s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA"
```

### Passo 3: Ative e inicie
```cmd
venv\Scripts\activate.bat
streamlit run streamlit_app.py
```

### Passo 4: Acesse no navegador
```
http://localhost:8501
```

---

## 📝 RESUMO DAS 3 OPÇÕES

| Opção | Dificuldade | Tempo | Como Fazer |
|-------|------------|-------|-----------|
| **INICIAR.bat** | ⭐ Fácil | 5s | Duplo-clique |
| PowerShell | ⭐⭐ Médio | 10s | Executar script |
| Command Prompt | ⭐⭐⭐ Avançado | 15s | Comandos manuais |

---

## ✅ SE TUDO DEU CERTO

Você deve ver algo assim no console:

```
2026-06-17 16:17:55.978 Uvicorn server started on 0.0.0.0:8501

You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.X.X:8501
```

---

## ⚠️ SE DEU ERRO

### Erro: "Access Denied" ou "Permission Denied"

**Solução para PowerShell:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

Depois tente novamente:
```powershell
.\INICIAR.ps1
```

### Erro: "Pasta não encontrada" ou "arquivo não existe"

**Solução:**
1. Verifique se está na pasta correta:
```powershell
pwd  # Deve mostrar: ...PROJETOS---BACKEND-IA
```

2. Se não estiver, execute:
```powershell
cd "s:\PROJETOS EM ANDAMENTO\PAINEL DE CONTROLE MTECH\PROGRAMAS\PROJETOS---BACKEND-IA"
```

### Erro: "Port 8501 already in use"

**Solução:**
```powershell
streamlit run streamlit_app.py --server.port 8502
```

Acesse: `http://localhost:8502`

---

## 🌐 ACESSAR A APLICAÇÃO

### Localmente (seu PC):
```
http://localhost:8501
```

### De outro computador (mesma rede):
```
http://192.168.X.X:8501
```
(substitua X.X pelo IP do seu PC)

---

## ⏹️ COMO PARAR A APLICAÇÃO

### Opção 1: Fechar a janela
- Simplesmente feche a janela do console

### Opção 2: Teclado
- Pressione: **Ctrl + C**

### Opção 3: Tarefa Agendada (Windows)
```powershell
Stop-Process -Name streamlit -Force
```

---

## 🔄 REABRIR DEPOIS

A próxima vez, simplesmente:
1. Duplo-clique em **`INICIAR.bat`**
2. Pronto! 🚀

---

## 💡 DICAS

✅ Deixe um atalho de `INICIAR.bat` na área de trabalho para acesso rápido
✅ Fixe a janela do navegador em http://localhost:8501 nos favoritos
✅ A aplicação recarrega automaticamente ao fazer mudanças no código
✅ Se não abrir no navegador, copie a URL manualmente

---

**Próximo Passo:** Duplo-clique em `INICIAR.bat` 🎉

