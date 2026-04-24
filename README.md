# Analisador de NF-e — VGR Medical

Ferramenta para leitura, análise e consulta de XMLs de Nota Fiscal Eletrônica (NF-e) de compras de medicamentos. Permite carregar múltiplos arquivos XML, visualizar os dados em dashboards, filtrar itens em tabela interativa e fazer perguntas em linguagem natural via IA.

---

## Funcionalidades

- **Autenticação** — login com usuário e senha; sessão mantida por cookie (30 dias)
- **Upload de XMLs** — arraste múltiplos arquivos de NF-e de uma vez
- **Dashboard** — KPIs de valor total e impostos, gráficos por fornecedor, composição tributária e fluxo de pagamentos por mês
- **Tabela interativa** — filtros por fornecedor, produto e busca livre; exportação para Excel
- **Chat com IA** — perguntas em português como *"Quanto paguei de ICMS na Supermed?"* ou *"Qual o produto mais caro?"*
- **Gerador de Excel (CLI)** — via linha de comando, mantendo toda a formatação fiscal brasileira

---

## Estrutura do projeto

```
extratorxmls/
├── app.py                  # Interface Streamlit (frontend + auth)
├── extratorxmls.py         # Parser de XMLs NF-e + gerador de Excel (CLI)
├── criar_usuario.py        # Script de setup — cria/atualiza usuários no config.yaml
├── config.yaml             # Credenciais de acesso (gerado pelo criar_usuario.py)
├── requirements.txt        # Dependências Python
├── Dockerfile              # Imagem Docker da aplicação
├── docker-compose.yml      # Orquestração Docker
├── .streamlit/config.toml  # Configuração do Streamlit (headless, porta)
├── .dockerignore           # Arquivos excluídos da imagem Docker
└── xmls/                   # Pasta de XMLs para uso via CLI
```

---

## Rodando com Docker (recomendado)

### Pré-requisitos
- Docker e Docker Compose instalados

### Primeiro acesso — criar usuário

O `config.yaml` com as credenciais fica **fora da imagem**, montado como volume. Crie o primeiro usuário assim:

```bash
# Cria/atualiza o config.yaml interativamente dentro do container
docker compose run --rm vgr-medical python criar_usuario.py
```

### Subir o app

```bash
docker compose up -d
```

Acesse em: **http://localhost:8501**

### Outros comandos úteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Parar
docker compose down

# Rebuild após atualizar o código
docker compose up -d --build

# Adicionar mais usuários
docker compose run --rm vgr-medical python criar_usuario.py
```

---

## Rodando localmente (sem Docker)

### Instalação

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### Criar primeiro usuário

```bash
python criar_usuario.py
```

### Interface web

```bash
.venv\Scripts\streamlit run app.py
```

Acesse em: **http://localhost:8501**

### Gerador de Excel (CLI)

Coloque os XMLs na pasta `xmls/` e execute:

```bash
python extratorxmls.py
```

O arquivo `nfe_export.xlsx` será gerado na raiz do projeto.

---

## Campos extraídos por XML

| Categoria | Campos |
|-----------|--------|
| Cabeçalho da NF | Número, série, chave, data de emissão, natureza da operação |
| Emitente | CNPJ, razão social, UF |
| Destinatário | CNPJ/CPF, razão social, UF |
| Totais da NF | Valor produtos, valor NF, ICMS, IPI, PIS, COFINS, ICMS-ST, FCP |
| Itens | Código, descrição, CFOP, NCM, ANVISA, quantidade, preço unitário |
| Impostos por item | ICMS (com alíquotas e bases), IPI, PIS, COFINS, ICMS-ST, FCP |
| Rastreabilidade | Lote, data de fabricação, data de validade, código de agregação |
| Cobrança | Duplicatas com vencimento e valor (fluxo de pagamentos) |

---

## Tecnologias

| Lib | Uso |
|-----|-----|
| `streamlit` | Interface web |
| `streamlit-authenticator` | Autenticação com login/senha e cookie de sessão |
| `openai` | Chat com IA (GPT-4o-mini) |
| `plotly` | Gráficos interativos |
| `pandas` | Manipulação de dados |
| `lxml` | Parsing de XML com namespace NF-e |
| `openpyxl` | Geração e formatação de Excel |
| `bcrypt` | Hash de senhas |

---

## Observações fiscais

- Suporta o padrão **NF-e modelo 55** (namespace `http://www.portalfiscal.inf.br/nfe`)
- Trata múltiplos regimes de ICMS (ICMS00, ICMS10, ICMS20, ICMS70, ICMSSN etc.)
- Rateia valores de impostos proporcionalmente por lote quando há rastreabilidade farmacêutica
- Valores monetários calculados com `Decimal` para evitar erros de ponto flutuante
