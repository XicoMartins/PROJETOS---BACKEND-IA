# FORMS-MTECH - Controle de Produção

**Status:** ✅ Refatorado para Streamlit Cloud  
**URL:** https://formsmtech.streamlit.app/  
**Versão:** 1.2  

## O que mudou?

- ✅ **Removido Django completamente** - Não é necessário para Streamlit
- ✅ **Persistência configurável** - PostgreSQL em produção e SQLite local
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
- Salva em banco persistente quando `DATABASE_URL` estiver configurada

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
**Produção/Streamlit Cloud:** Configure `DATABASE_URL` nos Secrets para usar PostgreSQL persistente.  

Exemplo de Secret no Streamlit Cloud:

```toml
DATABASE_URL = "postgresql://usuario:senha@host:5432/banco?sslmode=require"
```

Pode ser uma URL de PostgreSQL do Supabase, Neon ou outro provedor compatível.

## Diferenças vs Versão Anterior

| Aspecto | Antes (Django) | Depois (Streamlit) |
|--------|---|---|
| Framework BD | Django ORM | PostgreSQL/SQLite via SQL direto |
| Deploy | VPS necessário | Streamlit Cloud |
| Dependências | Django, migrations | Streamlit, pandas, openpyxl, psycopg |
| Admin | Django admin | UI Streamlit |
| Arquitetura | Complexa | Simples |

## FAQ

**P: Meus dados antigos?**  
R: Migre do `db.sqlite3` original para o novo com SQL direto.

**P: Pode usar com PostgreSQL?**  
R: Sim. Configure `DATABASE_URL` nos Secrets do Streamlit Cloud.

**P: Como adicionar novas funcionalidades?**  
R: Edite `streamlit_app.py`, faça commit, push - deploy automático!

## Suporte

Problemas? Verifique:
- Planilhas em `planilhas/`
- Python 3.10+
- `pip install -r requirements.txt` rodado

## Roadmap

- [x] Integração com PostgreSQL
- [ ] Autenticação de usuários
- [ ] Gráficos e relatórios
- [ ] API REST

---

**Criado por:** MTECH  
**Última atualização:** 17/06/2026  
