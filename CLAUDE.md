# CLAUDE.md — Contexto do projeto para o assistente

## O que é este projeto

Ferramenta de análise de Notas Fiscais Eletrônicas (NF-e) para uma distribuidora de medicamentos (VGR Medical). O cliente recebe XMLs de NFs de compra de fornecedores (indústrias e outras distribuidoras) e precisa analisá-los sem abrir arquivo por arquivo.

O projeto tem dois modos de uso:
1. **CLI** (`extratorxmls.py`) — lê XMLs da pasta `xmls/` e gera um Excel consolidado
2. **Interface web** (`app.py`) — Streamlit com autenticação, upload de XMLs, dashboard, tabela e chat com IA

---

## Arquivos principais

| Arquivo | Papel |
|---------|-------|
| `extratorxmls.py` | Parser de XML NF-e + gerador de Excel. Contém toda a lógica de extração e as constantes de colunas (`MONEY_COLS_FLAT`, `QTY_COLS_FLAT`, etc.) |
| `app.py` | Interface Streamlit. Importa funções de `extratorxmls.py`. Usa OpenAI `gpt-4o-mini` para o chat. Inclui autenticação via `streamlit-authenticator`. |
| `criar_usuario.py` | Script interativo para criar/atualizar usuários no `config.yaml`. Usar em host ou via `docker compose run`. |
| `config.yaml` | Credenciais de acesso (gerado por `criar_usuario.py`). **Não versionar em repositório público.** |
| `requirements.txt` | Dependências: streamlit, openai, plotly, pandas, lxml, openpyxl, streamlit-authenticator, pyyaml, bcrypt |
| `Dockerfile` | Imagem Python 3.11-slim com o app |
| `docker-compose.yml` | Sobe o app na porta 8501; monta `config.yaml` como volume do host |
| `.streamlit/config.toml` | Streamlit headless + endereço 0.0.0.0 para funcionar em container |
| `xmls/` | Pasta de XMLs para uso via CLI |

---

## Decisões técnicas importantes

- **LLM: OpenAI GPT-4o-mini** — escolha do cliente por custo. Não usar Claude API nem modelos mais caros sem autorização explícita.
- **Sem banco de dados** — os dados ficam em memória (`st.session_state`) durante a sessão do Streamlit. Não há persistência entre sessões.
- **Parser reutilizado** — `app.py` importa `parse_file_flat` e funções de formatação diretamente de `extratorxmls.py`. Não duplicar lógica de parsing.
- **Valores financeiros com `Decimal`** — nunca usar `float` para cálculos monetários. O `safe_rateio` faz o rateio por lote com precisão.
- **Namespace NFe fixo** — `http://www.portalfiscal.inf.br/nfe`. Todos os XPath usam o prefixo `nfe:`.
- **Autenticação via streamlit-authenticator** — `config.yaml` com hash bcrypt das senhas. Cookie de sessão de 30 dias. O arquivo `config.yaml` é montado como volume no Docker e **não é copiado para dentro da imagem**.
- **Docker**: imagem baseada em `python:3.11-slim`. `config.yaml` vive no host e é montado via volume. Para adicionar usuários: `docker compose run --rm vgr-medical python criar_usuario.py`.

---

## Domínio fiscal brasileiro — referências rápidas

- **NF-e modelo 55** — nota fiscal eletrônica padrão entre empresas
- **ICMS** — imposto estadual sobre circulação de mercadorias
- **ICMS-ST** — substituição tributária do ICMS (recolhido antecipadamente)
- **IPI** — imposto federal sobre produtos industrializados
- **PIS / COFINS** — contribuições federais sobre faturamento
- **FCP** — Fundo de Combate à Pobreza (adicional ao ICMS em alguns estados)
- **NCM** — Nomenclatura Comum do Mercosul (classificação fiscal do produto)
- **CFOP** — Código Fiscal de Operações (natureza da operação na NF)
- **ANVISA** — agência reguladora; código `cProdANVISA` identifica medicamentos
- **Rastro / lote** — rastreabilidade farmacêutica obrigatória; cada item pode ter múltiplos lotes com datas de fabricação e validade
- **Duplicatas** — parcelas de cobrança da NF (`cobr/dup`), usadas no gráfico de fluxo de pagamentos

---

## Padrão de dados

A função `parse_file_flat(path)` retorna uma lista de dicionários. Cada dicionário é uma linha do Excel/DataFrame, podendo representar:
- **Uma linha por item** (produtos sem rastreabilidade de lote)
- **Uma linha por lote** (medicamentos com `rastro`), com valores rateados proporcionalmente à quantidade do lote

Colunas sufixadas com `_total` vêm do `<ICMSTot>` da NF inteira e se repetem em todas as linhas da mesma NF.
Colunas sufixadas com `_item` são do item (`<det>`).
Colunas sufixadas com `_lote` são do lote (`<rastro>`), com valores rateados.

O campo `duplicatas_txt` tem formato `"nDup|dVenc|vDup; nDup|dVenc|vDup"` — gerado por `duplicatas_txt_from_infNFe()` e usado pela função `parse_fluxo_pagamentos()` no dashboard.

---

## Como rodar

```bash
# Docker (recomendado)
docker compose run --rm vgr-medical python criar_usuario.py  # primeiro acesso
docker compose up -d

# Interface web local
python criar_usuario.py   # primeiro acesso
.venv\Scripts\streamlit run app.py

# CLI (gera nfe_export.xlsx)
.venv\Scripts\python extratorxmls.py
```

---

## O que evitar

- Não usar `float` para valores monetários — usar `Decimal`
- Não duplicar a lógica de parsing em `app.py` — importar de `extratorxmls.py`
- Não trocar o modelo de LLM de `gpt-4o-mini` sem confirmar com o usuário
- Não adicionar banco de dados sem solicitação explícita
- Não criar scripts separados para funcionalidades que cabem dentro de `app.py` ou `extratorxmls.py`
- Não copiar `config.yaml` para dentro da imagem Docker — ele deve sempre ser um volume do host
