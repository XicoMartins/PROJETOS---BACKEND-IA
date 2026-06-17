# FORMS-MTECH - Controle de Produção

**Status:** ✅ Refatorado para Streamlit Cloud  
**URL:** https://mtechforms-refactored.streamlit.app/ (será criada após deploy)  
**Versão:** 1.2  

## O que mudou?

- ✅ **Removido Django completamente** - Não é necessário para Streamlit
- ✅ **Implementado SQLite puro** - Sem dependências de ORM
- ✅ **Compatível com Streamlit Cloud** - Deploy direto do GitHub
- ✅ **Mesma funcionalidade** - Todos os recursos mantidos

## Instalação Local

```bash
# Clonar repositório
git clone https://github.com/XicoMartins/PROJETOS---BACKEND-IA.git
cd PROJETOS---BACKEND-IA

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # ou .\venv\Scripts\Activate no Windows

# Instalar dependências
pip install -r requirements.txt

# Rodar aplicação
streamlit run streamlit_app.py
```

## Estrutura do Projeto

```
PROJETOS---BACKEND-IA/
├── streamlit_app.py          # App principal
├── requirements.txt          # Dependências
├── README.md
├── core/
│   ├── __init__.py
│   ├── db_utils.py          # BD sem Django
│   └── excel_utils.py       # Leitura de Excel
├── planilhas/               # Planilhas de processo
│   ├── LISTA DE OPERADORES.xlsx
│   └── ... (outras planilhas)
└── assets/                  # Logo e imagens
    ├── logo.png
    └── background.png
```

## Funcionalidades

### 📝 Lançamento de Registros
- Seleção de cliente, display, máquina, processo
- Validação automática
- Salva em banco SQLite local

### 📊 Consulta
- Visualizar todos os registros
- Exportar em CSV
- Paginação (em desenvolvimento)

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt`
- Planilhas Excel em `planilhas/`

## Deploy em Streamlit Cloud

1. Conecte seu repositório GitHub
2. Selecione "PROJETOS---BACKEND-IA"
3. Main file: `streamlit_app.py`
4. Deploy automático a cada push!

## Dados & Persistência

**Local:** Dados salvos em `~/.mtech/production.db`  
**Streamlit Cloud:** Dados em `/tmp/production.db` (voláteis entre deploys)  

Para persistência em produção, use PostgreSQL externo (Supabase, Neon).

## Diferenças vs Versão Anterior

| Aspecto | Antes (Django) | Depois (SQLite) |
|--------|---|---|
| Framework BD | Django ORM | SQLite puro |
| Deploy | VPS necessário | Streamlit Cloud |
| Dependências | Django, migrations | Apenas pandas, streamlit |
| Admin | Django admin | UI Streamlit |
| Arquitetura | Complexa | Simples |

## FAQ

**P: Meus dados antigos?**  
R: Migre do `db.sqlite3` original para o novo com SQL direto.

**P: Pode usar com PostgreSQL?**  
R: Sim! Edite `core/db_utils.py` para usar `psycopg2`.

**P: Como adicionar novas funcionalidades?**  
R: Edite `streamlit_app.py`, faça commit, push - deploy automático!

## Suporte

Problemas? Verifique:
- Planilhas em `planilhas/`
- Python 3.10+
- `pip install -r requirements.txt` rodado

## Roadmap

- [ ] Integração com PostgreSQL
- [ ] Autenticação de usuários
- [ ] Gráficos e relatórios
- [ ] API REST

---

**Criado por:** MTECH  
**Última atualização:** 17/06/2026  
