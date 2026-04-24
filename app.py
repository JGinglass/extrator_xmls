import os
import tempfile
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # carrega .env se existir (local e Docker)

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from openai import OpenAI

from extratorxmls import (
    DATE_COLS_FLAT,
    MONEY_COLS_FLAT,
    PCT_COLS_FLAT,
    QTY_COLS_FLAT,
    format_columns,
    format_columns_as_currency,
    parse_file_flat,
    to_date_cols,
    to_numeric_cols,
)

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VGR Medical — Analisador de NF-e",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=Noto+Sans:wght@400;500;700&display=swap');

    :root {
      --bg:           #F4F6FA;
      --bg-card:      #FFFFFF;
      --accent:       #0891B2;
      --accent-light: #E0F5FA;
      --accent-dark:  #0E7490;
      --accent-green: #22C55E;
      --text:         #0F172A;
      --text-sub:     #64748B;
      --border:       #E2ECF4;
      --shadow-sm:    0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04);
      --shadow:       0 4px 20px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
      --shadow-lg:    0 10px 40px rgba(0,0,0,0.08);
    }

    /* ── Base ────────────────────────────────── */
    .stApp { background-color: var(--bg) !important; font-family: 'Noto Sans', sans-serif !important; }
    .block-container { padding-top: 1.5rem !important; padding-left: 2.5rem !important; padding-right: 2.5rem !important; max-width: 1400px !important; }
    h1, h2, h3, h4 { color: var(--text) !important; font-family: 'Figtree', sans-serif !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
    p, span, label, div { font-family: 'Noto Sans', sans-serif !important; line-height: 1.6 !important; }
    hr { border-color: var(--border) !important; }

    /* ── Esconde botão de colapso do sidebar (ícone Material não carrega) ── */
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    header [data-testid="stBaseButton-headerNoPadding"] { display: none !important; }

    /* ── Sidebar ─────────────────────────────── */
    [data-testid="stSidebar"] {
      background-color: #FFFFFF !important;
      border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
    [data-testid="stSidebar"] .block-container { padding: 0 !important; }
    [data-testid="stSidebar"] section { color: var(--text) !important; }
    /* área de conteúdo do sidebar com padding */
    [data-testid="stSidebar"] .block-container > div { padding: 0 1.2rem 1.2rem 1.2rem !important; }

    /* ── Buttons ─────────────────────────────── */
    .stButton > button {
      background-color: var(--accent) !important;
      color: #fff !important;
      border: none !important;
      border-radius: 10px !important;
      font-family: 'Figtree', sans-serif !important;
      font-weight: 600 !important;
      font-size: 0.84rem !important;
      padding: 0.5rem 1rem !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
      transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.12s ease !important;
      box-shadow: 0 1px 4px rgba(8,145,178,0.25) !important;
      cursor: pointer !important;
    }
    .stButton > button:hover {
      background-color: var(--accent-dark) !important;
      box-shadow: var(--shadow) !important;
      transform: translateY(-1px) !important;
    }

    /* ── Download button ─────────────────────── */
    [data-testid="stDownloadButton"] > button {
      background-color: #fff !important;
      color: var(--accent) !important;
      border: 1.5px solid var(--accent) !important;
      border-radius: 10px !important;
      font-weight: 600 !important;
      font-family: 'Figtree', sans-serif !important;
    }
    [data-testid="stDownloadButton"] > button:hover { background-color: var(--accent-light) !important; }

    /* ── Tabs ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
      background-color: #fff !important;
      border-radius: 12px 12px 0 0 !important;
      border-bottom: 2px solid var(--border) !important;
      gap: 0 !important;
      padding: 0 0.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
      background-color: transparent !important;
      border-radius: 0 !important;
      color: var(--text-sub) !important;
      font-family: 'Figtree', sans-serif !important;
      font-weight: 600 !important;
      font-size: 0.9rem !important;
      padding: 0.75rem 1.4rem !important;
      border-bottom: 2px solid transparent !important;
      margin-bottom: -2px !important;
      transition: color 0.15s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--accent) !important; }
    .stTabs [aria-selected="true"] {
      background-color: transparent !important;
      color: var(--accent) !important;
      border-bottom: 3px solid var(--accent) !important;
      font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ── Inputs & selects ────────────────────── */
    .stTextInput > div > div,
    .stSelectbox > div > div {
      background-color: #fff !important;
      border: 1.5px solid var(--border) !important;
      border-radius: 8px !important;
      color: var(--text) !important;
    }
    .stTextInput > div > div:focus-within,
    .stSelectbox > div > div:focus-within {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 3px var(--accent-light) !important;
    }
    .stTextInput input, .stSelectbox select { color: var(--text) !important; }

    /* ── Metrics ─────────────────────────────── */
    [data-testid="metric-container"] {
      background-color: #fff !important;
      border: none !important;
      border-left: 4px solid var(--accent) !important;
      border-radius: 14px !important;
      padding: 1.2rem 1.4rem !important;
      box-shadow: var(--shadow) !important;
      transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="metric-container"]:hover {
      transform: translateY(-2px) !important;
      box-shadow: var(--shadow-lg) !important;
    }
    [data-testid="stMetricValue"] {
      color: var(--text) !important;
      font-size: 1.55rem !important;
      font-weight: 800 !important;
      font-family: 'Figtree', sans-serif !important;
      letter-spacing: -0.03em !important;
    }
    [data-testid="stMetricLabel"] {
      color: var(--text-sub) !important;
      font-size: 0.72rem !important;
      font-weight: 600 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.08em !important;
      font-family: 'Noto Sans', sans-serif !important;
    }

    /* ── Dataframe ───────────────────────────── */
    [data-testid="stDataFrame"] {
      border: 1px solid var(--border) !important;
      border-radius: 12px !important;
      overflow: hidden !important;
      box-shadow: var(--shadow) !important;
    }

    /* ── File uploader ───────────────────────── */
    [data-testid="stFileUploaderDropzone"] {
      background-color: var(--accent-light) !important;
      border: 2px dashed var(--accent) !important;
      border-radius: 12px !important;
    }

    /* ── Chat ────────────────────────────────── */
    [data-testid="stChatMessage"] {
      background-color: #fff !important;
      border: 1px solid var(--border) !important;
      border-radius: 16px !important;
      margin-bottom: 0.75rem !important;
      box-shadow: var(--shadow-sm) !important;
      padding: 0.25rem 0 !important;
    }
    [data-testid="stChatMessage"][data-testid*="user"] {
      border-left: 3px solid var(--accent) !important;
    }
    /* Avatar do usuário — substitui o vermelho padrão */
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-user"] > div {
      background-color: var(--accent) !important;
      color: #fff !important;
    }
    /* Avatar do assistente */
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="chatAvatarIcon-assistant"] > div {
      background-color: #0F172A !important;
      color: #fff !important;
    }
    /* Caixa de input do chat */
    [data-testid="stChatInput"] > div {
      border: 2px solid var(--border) !important;
      border-radius: 14px !important;
      background-color: #fff !important;
      box-shadow: var(--shadow-sm) !important;
      transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }
    [data-testid="stChatInput"] > div:focus-within {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 3px rgba(8,145,178,0.12) !important;
    }

    /* ── Alerts ──────────────────────────────── */
    .stAlert { border-radius: 10px !important; }

    /* ── Caption ─────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] { color: var(--text-sub) !important; font-size: 0.82rem !important; }

    /* ── Section header ──────────────────────── */
    .vgr-section-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 0.75rem;
      padding-bottom: 0.4rem;
      border-bottom: 2px solid var(--accent-light);
      font-family: 'Inter', sans-serif;
    }

    /* ── Welcome cards ───────────────────────── */
    .welcome-card {
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.8rem 1.6rem;
      box-shadow: var(--shadow);
      height: 100%;
    }
    .welcome-card .wc-icon { font-size: 2rem; margin-bottom: 0.75rem; }
    .welcome-card .wc-title { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.5rem; }
    .welcome-card .wc-desc { font-size: 0.875rem; color: var(--text-sub); line-height: 1.6; }

    /* ── Sidebar header banner ───────────────── */
    .vgr-sidebar-header {
      background: linear-gradient(160deg, #0F172A 0%, #1A3550 100%);
      padding: 1.5rem 1.2rem 1.3rem 1.2rem;
      margin-bottom: 1.2rem;
      position: relative;
      overflow: hidden;
    }
    .vgr-sidebar-header::after {
      content: '';
      position: absolute;
      top: -20px; right: -20px;
      width: 80px; height: 80px;
      border-radius: 50%;
      background: rgba(8,145,178,0.15);
    }
    .vgr-brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .vgr-brand-dot {
      width: 42px; height: 42px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--accent) 0%, #5BB8E8 100%);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.2rem;
      color: #fff;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(58,158,208,0.5);
    }
    .vgr-brand-name { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; line-height: 1.2; }
    .vgr-brand-sub { font-size: 0.72rem; color: rgba(255,255,255,0.55); font-weight: 400; margin-top: 1px; }

    /* ── Sidebar section label ───────────────── */
    .sidebar-section-label {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.09em;
      color: var(--text-sub);
      margin: 1.1rem 0 0.5rem 0;
    }

    /* ── Sidebar stat grid ───────────────────── */
    .sidebar-stats-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.55rem;
      margin-bottom: 0.8rem;
    }
    .stat-card {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.7rem 0.75rem;
    }
    .stat-card .sc-value {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--accent);
      line-height: 1.2;
    }
    .stat-card .sc-value.full { font-size: 0.88rem; }
    .stat-card .sc-label {
      font-size: 0.68rem;
      color: var(--text-sub);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 2px;
    }

    /* ── Page header ─────────────────────────── */
    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }
    .page-header h2 { margin: 0 !important; font-size: 1.35rem !important; }
    .page-header .ph-sub { font-size: 0.82rem; color: var(--text-sub); margin-top: 0.2rem; }

    /* ── Login page ──────────────────────────── */
    .login-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-top: 6vh;
    }
    .login-logo {
      width: 64px; height: 64px;
      border-radius: 18px;
      background: linear-gradient(135deg, #3A9ED0 0%, #1A2B3C 100%);
      display: flex; align-items: center; justify-content: center;
      font-size: 2rem;
      margin-bottom: 1rem;
      box-shadow: 0 6px 24px rgba(58,158,208,0.35);
    }
    .login-title { font-size: 1.6rem; font-weight: 700; color: #1A2B3C; margin-bottom: 0.2rem; }
    .login-sub { font-size: 0.85rem; color: #6B7C8D; margin-bottom: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Autenticação ─────────────────────────────────────────────────────────────

_CONFIG_PATH = Path("config.yaml")

def _load_auth_config():
    if not _CONFIG_PATH.exists():
        return None
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

_auth_config = _load_auth_config()

if _auth_config is None:
    # config.yaml não existe ainda — mostrar instruções de setup
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            """
            <div class="login-wrapper">
              <div class="login-logo">💊</div>
              <div class="login-title">VGR Medical</div>
              <div class="login-sub">Analisador de NF-e</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.error("Nenhum usuário cadastrado ainda.")
        st.info(
            "**Primeiro acesso:** abra um terminal e execute:\n\n"
            "```\n.venv\\Scripts\\python criar_usuario.py\n```\n\n"
            "Depois reinicie o app."
        )
    st.stop()

_authenticator = stauth.Authenticate(
    _auth_config["credentials"],
    _auth_config["cookie"]["name"],
    _auth_config["cookie"]["key"],
    _auth_config["cookie"]["expiry_days"],
)


# ── Tela de login ─────────────────────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div class="login-wrapper">
              <div class="login-logo">💊</div>
              <div class="login-title">VGR Medical</div>
              <div class="login-sub">Faça login para continuar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _authenticator.login(location="main")

    if st.session_state.get("authentication_status") is False:
        st.error("Usuário ou senha incorretos.")
    st.stop()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_uploaded_files(uploaded_files):
    """Recebe lista de UploadedFile, retorna (DataFrame, lista de erros)."""
    all_rows = []
    errors = []
    for uf in uploaded_files:
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            tmp.write(uf.read())
            tmp_path = tmp.name
        try:
            rows = parse_file_flat(tmp_path)
            if rows:
                all_rows.extend(rows)
            else:
                errors.append(f"⚠️ {uf.name}: infNFe não encontrado")
        except Exception as e:
            errors.append(f"❌ {uf.name}: {e}")
        finally:
            os.unlink(tmp_path)

    if not all_rows:
        return pd.DataFrame(), errors

    df = pd.DataFrame(all_rows)
    df = to_numeric_cols(
        df, MONEY_COLS_FLAT + QTY_COLS_FLAT + ["nItem", "seqRastro"] + PCT_COLS_FLAT
    )
    df = to_date_cols(df, DATE_COLS_FLAT)
    return df, errors


def fmt_brl(value) -> str:
    if pd.isna(value):
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_llm_context(df: pd.DataFrame) -> str:
    """Constrói um texto compacto com os dados das NFs para enviar ao modelo."""
    lines = []

    # --- Resumo geral ---
    n_nfs = df["arquivo"].nunique()
    fornecedores = df["emit_xNome"].dropna().unique().tolist()
    nf_totals = (
        df.groupby("arquivo")
        .agg(
            fornecedor=("emit_xNome", "first"),
            nNF=("nNF", "first"),
            dhEmi=("dhEmi", "first"),
            vNF=("vNF", "first"),
            vICMS=("vICMS_total", "first"),
            vIPI=("vIPI_total", "first"),
            vPIS=("vPIS_total", "first"),
            vCOFINS=("vCOFINS_total", "first"),
            vST=("vST_total", "first"),
        )
        .reset_index()
    )
    total_nf = nf_totals["vNF"].sum()

    lines.append("=== RESUMO GERAL ===")
    lines.append(f"NFs carregadas: {n_nfs}")
    lines.append(f"Valor total das NFs: R$ {total_nf:,.2f}")
    lines.append(f"Fornecedores: {', '.join(fornecedores)}")
    lines.append("")

    # --- Por NF ---
    lines.append("=== NOTAS FISCAIS ===")
    for _, row in nf_totals.iterrows():
        def v(col):
            val = row.get(col, 0)
            return 0 if pd.isna(val) else val

        lines.append(
            f"NF {row['nNF']} | Fornecedor: {row['fornecedor']} | Emissão: {row['dhEmi']} | "
            f"Valor NF: R${v('vNF'):,.2f} | ICMS: R${v('vICMS'):,.2f} | "
            f"IPI: R${v('vIPI'):,.2f} | PIS: R${v('vPIS'):,.2f} | "
            f"COFINS: R${v('vCOFINS'):,.2f} | ST: R${v('vST'):,.2f}"
        )
    lines.append("")

    # --- Itens ---
    lines.append("=== ITENS ===")
    item_cols = [
        "arquivo", "emit_xNome", "nNF", "xProd", "cProd", "qCom_item", "uCom",
        "vUnCom", "vProd_item", "vICMS_item", "vIPI_item",
        "vPIS_item", "vCOFINS_item", "vICMSST_item", "nLote", "dFab", "dVal",
    ]
    existing = [c for c in item_cols if c in df.columns]
    dedup_keys = [c for c in ["arquivo", "cProd", "nLote"] if c in existing]
    items = df[existing].drop_duplicates(subset=dedup_keys)

    for _, row in items.iterrows():
        def fv(col, fmt=".2f"):
            val = row.get(col, None)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            return f"R${float(val):,{fmt}}"

        parts = [
            f"Produto: {row.get('xProd', '')}",
            f"Fornecedor: {row.get('emit_xNome', '')}",
            f"NF: {row.get('nNF', '')}",
            f"Qtd: {row.get('qCom_item', '')} {row.get('uCom', '')}",
            f"Preço unit: {fv('vUnCom', '.4f')}",
            f"Total item: {fv('vProd_item')}",
        ]
        for col, label in [
            ("vICMS_item", "ICMS"), ("vIPI_item", "IPI"),
            ("vPIS_item", "PIS"), ("vCOFINS_item", "COFINS"),
            ("vICMSST_item", "ST"),
        ]:
            val = fv(col)
            if val:
                parts.append(f"{label}: {val}")
        lote = row.get("nLote")
        if lote and not (isinstance(lote, float) and pd.isna(lote)):
            parts.append(f"Lote: {lote} | Val: {row.get('dVal', '')}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


# Paleta VGR Medical para gráficos
# Fornecedores — categorias bem distintas (máximo contraste entre si)
VGR_SUPPLIERS = [
    "#2EC4B6", "#F4A261", "#6D4C9E", "#E76F51",
    "#F7C948", "#CB4D76", "#57CC99", "#3A9ED0",
    "#FF9F1C", "#8338EC",
]
# Impostos — cores fixas por tipo (ICMS, IPI, PIS, COFINS, ICMS-ST)
VGR_TAXES = ["#3A9ED0", "#F4A261", "#2EC4B6", "#E76F51", "#6D4C9E"]
CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#1A2B3C", size=12),
    margin=dict(l=8, r=8, t=36, b=8),
)


def export_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="tabela", index=False)
        ws = writer.book["tabela"]
        format_columns_as_currency(ws, df, [c for c in MONEY_COLS_FLAT if c in df.columns])
        format_columns(ws, df, [c for c in QTY_COLS_FLAT if c in df.columns], "#,##0.000")
        format_columns(ws, df, ["nItem", "seqRastro"], "0")
        format_columns(ws, df, [c for c in DATE_COLS_FLAT if c in df.columns], "dd/mm/yyyy")
        format_columns(ws, df, [c for c in PCT_COLS_FLAT if c in df.columns], "0.00")
    return buf.getvalue()


def parse_fluxo_pagamentos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai as duplicatas de cada NF e retorna um DataFrame com
    colunas: mes (período YYYY-MM), mes_label (MMM/YYYY), fornecedor, valor.
    Cada NF é processada uma única vez (dedup por arquivo).
    """
    from decimal import Decimal, InvalidOperation

    nf_unicas = df.drop_duplicates(subset=["arquivo"])[["arquivo", "emit_xNome", "duplicatas_txt"]]
    rows = []

    for _, nf in nf_unicas.iterrows():
        txt = nf.get("duplicatas_txt")
        fornecedor = nf.get("emit_xNome", "")
        if not txt or (isinstance(txt, float) and pd.isna(txt)):
            continue
        for dup in str(txt).split(";"):
            parts = dup.strip().split("|")
            if len(parts) < 3:
                continue
            _, dvenc, vdup = parts[0].strip(), parts[1].strip(), parts[2].strip()
            try:
                dt = pd.to_datetime(dvenc, errors="coerce")
                valor = float(Decimal(vdup.replace(",", ".")))
            except (InvalidOperation, ValueError):
                continue
            if pd.isna(dt) or valor <= 0:
                continue
            rows.append({
                "mes": dt.strftime("%Y-%m"),
                "mes_label": dt.strftime("%b/%Y"),
                "fornecedor": fornecedor,
                "valor": valor,
                "dt": dt,
            })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("dt")
    return result


# ─── Session state ────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "loaded_names" not in st.session_state:
    st.session_state.loaded_names = []


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Header banner com a marca ──────────────────────────────────────────
    _user_display = _auth_config["credentials"]["usernames"].get(
        st.session_state.get("username", ""), {}
    ).get("name", st.session_state.get("username", ""))

    st.markdown(
        f"""
        <div class="vgr-sidebar-header">
          <div class="vgr-brand">
            <div class="vgr-brand-dot">💊</div>
            <div>
              <div class="vgr-brand-name">VGR Medical</div>
              <div class="vgr-brand-sub">Analisador de NF-e</div>
            </div>
          </div>
          <div style="margin-top:0.9rem; font-size:0.75rem; color:rgba(255,255,255,0.55);">
            Olá, <strong style="color:rgba(255,255,255,0.85);">{_user_display}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _authenticator.logout(button_name="Sair", location="sidebar")

    # ── API Key ────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-label">Configuração</div>', unsafe_allow_html=True)
    _env_key = os.environ.get("OPENAI_API_KEY", "")
    if _env_key:
        api_key = _env_key
        st.caption("🔑 API Key configurada")
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Necessário apenas para o chat com IA",
            label_visibility="collapsed",
        )
        st.caption("🔑 OpenAI API Key — necessária para o chat")

    # ── Upload ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-label">Arquivos</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Carregar XMLs de NF-e",
        type=["xml"],
        accept_multiple_files=True,
        help="Arraste múltiplos arquivos XML de NF-e",
        label_visibility="collapsed",
    )

    if uploaded:
        new_names = sorted(f.name for f in uploaded)
        if new_names != st.session_state.loaded_names:
            with st.spinner("Processando XMLs..."):
                df_parsed, errors = parse_uploaded_files(uploaded)
            for err in errors:
                st.warning(err)
            if not df_parsed.empty:
                st.session_state.df = df_parsed
                st.session_state.loaded_names = new_names
                st.session_state.messages = []
                st.success(f"✅ {len(new_names)} arquivo(s) processado(s)")

    df = st.session_state.df
    if not df.empty:
        # ── Stats em grid de cards ─────────────────────────────────────────
        total = df.groupby("arquivo")["vNF"].first().sum()
        n_nfs = df["arquivo"].nunique()
        n_itens = len(df)
        n_forn = df["emit_xNome"].nunique() if "emit_xNome" in df.columns else 0
        val_str = fmt_brl(total)

        st.markdown('<div class="sidebar-section-label">Resumo</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="sidebar-stats-grid">
              <div class="stat-card">
                <div class="sc-value">{n_nfs}</div>
                <div class="sc-label">NFs</div>
              </div>
              <div class="stat-card">
                <div class="sc-value">{n_itens}</div>
                <div class="sc-label">Itens</div>
              </div>
              <div class="stat-card">
                <div class="sc-value">{n_forn}</div>
                <div class="sc-label">Fornecedores</div>
              </div>
              <div class="stat-card">
                <div class="sc-value full">{val_str}</div>
                <div class="sc-label">Valor Total</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 Limpar dados", use_container_width=True):
            st.session_state.df = pd.DataFrame()
            st.session_state.loaded_names = []
            st.session_state.messages = []
            st.rerun()


# ─── Tela de boas-vindas ──────────────────────────────────────────────────────
df = st.session_state.df

if df.empty:
    st.markdown(
        """
        <div style="padding: 2rem 0 1.5rem 0;">
          <div style="font-size:0.8rem; font-weight:600; color:#3A9ED0; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.5rem;">VGR Medical</div>
          <h1 style="font-size:2rem; font-weight:700; color:#1A2B3C; margin:0 0 0.5rem 0;">Analisador de NF-e</h1>
          <p style="font-size:1rem; color:#6B7C8D; margin:0;">Carregue seus arquivos XML de NF-e pela barra lateral para começar a análise.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    cards = [
        ("📊", "Dashboard", "Visão geral de gastos, impostos e fornecedores com gráficos interativos e KPIs em tempo real."),
        ("📋", "Tabela de Itens", "Explore, filtre por fornecedor ou produto e exporte todos os itens das NFs para Excel."),
        ("💬", "Chat com IA", "Pergunte em linguagem natural: <em>\"Quanto paguei de ICMS na Supermed?\"</em>"),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], cards):
        col.markdown(
            f"""
            <div class="welcome-card">
              <div class="wc-icon">{icon}</div>
              <div class="wc-title">{title}</div>
              <div class="wc-desc">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Tabela", "💬 Chat com IA"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # Totais por NF (evita somar valores de header repetidos por linha de item)
    nf_totals = (
        df.groupby("arquivo")
        .agg(
            fornecedor=("emit_xNome", "first"),
            nNF=("nNF", "first"),
            dhEmi=("dhEmi", "first"),
            vNF=("vNF", "first"),
            vICMS=("vICMS_total", "first"),
            vIPI=("vIPI_total", "first"),
            vPIS=("vPIS_total", "first"),
            vCOFINS=("vCOFINS_total", "first"),
            vST=("vST_total", "first"),
            vFCP=("vFCP_total", "first"),
        )
        .reset_index()
    )

    def s(col):
        return nf_totals[col].fillna(0).sum()

    total_nf = s("vNF")
    total_icms = s("vICMS")
    total_ipi = s("vIPI")
    total_pis = s("vPIS")
    total_cofins = s("vCOFINS")
    total_st = s("vST")
    total_impostos = total_icms + total_ipi + total_pis + total_cofins + total_st

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="page-header"><div><h2>Dashboard</h2>'
        '<div class="ph-sub">Visão consolidada das NFs carregadas</div></div></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total das NFs", fmt_brl(total_nf))
    c2.metric("Total de Impostos", fmt_brl(total_impostos))
    c3.metric("NFs carregadas", df["arquivo"].nunique())
    c4.metric("Fornecedores", df["emit_xNome"].nunique())
    c5.metric("Produtos únicos", df["xProd"].nunique() if "xProd" in df.columns else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="vgr-section-title">Valor total por fornecedor</div>', unsafe_allow_html=True)
        by_forn = (
            nf_totals.groupby("fornecedor")["vNF"]
            .sum()
            .reset_index()
            .sort_values("vNF", ascending=True)
        )
        by_forn.columns = ["Fornecedor", "Valor Total (R$)"]
        fig1 = px.bar(
            by_forn,
            x="Valor Total (R$)",
            y="Fornecedor",
            orientation="h",
            color="Valor Total (R$)",
            color_continuous_scale=[[0, "#A3D8F4"], [1, "#2A7BAA"]],
            text="Valor Total (R$)",
        )
        fig1.update_traces(
            marker_line_width=0,
            texttemplate="R$ %{x:,.0f}",
            textposition="inside",
            textfont=dict(size=11, color="#FFFFFF"),
            insidetextanchor="end",
        )
        fig1.update_layout(
            **CHART_BASE,
            showlegend=False,
            coloraxis_showscale=False,
            xaxis=dict(gridcolor="#EEF3F8", zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.markdown('<div class="vgr-section-title">Composição dos impostos</div>', unsafe_allow_html=True)
        imp_data = {
            "ICMS": total_icms,
            "IPI": total_ipi,
            "PIS": total_pis,
            "COFINS": total_cofins,
            "ICMS-ST": total_st,
        }
        imp_df = pd.DataFrame(
            [(k, v) for k, v in imp_data.items() if v > 0],
            columns=["Imposto", "Valor"],
        )
        if not imp_df.empty:
            fig2 = px.pie(
                imp_df,
                values="Valor",
                names="Imposto",
                hole=0.48,
                color_discrete_sequence=VGR_TAXES,
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label", textfont_size=12)
            fig2.update_layout(**CHART_BASE)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum imposto identificado.")

    st.markdown('<div class="vgr-section-title" style="margin-top:1rem;">Impostos detalhados por NF</div>', unsafe_allow_html=True)
    imp_detail = nf_totals.melt(
        id_vars=["fornecedor", "nNF"],
        value_vars=["vICMS", "vIPI", "vPIS", "vCOFINS", "vST"],
        var_name="Imposto",
        value_name="Valor",
    )
    imp_detail["Imposto"] = imp_detail["Imposto"].map(
        {"vICMS": "ICMS", "vIPI": "IPI", "vPIS": "PIS", "vCOFINS": "COFINS", "vST": "ICMS-ST"}
    )
    imp_detail["Label"] = imp_detail["fornecedor"] + "  ·  NF " + imp_detail["nNF"].astype(str)
    imp_detail = imp_detail[imp_detail["Valor"].fillna(0) > 0]

    if not imp_detail.empty:
        fig3 = px.bar(
            imp_detail,
            x="Label",
            y="Valor",
            color="Imposto",
            barmode="stack",
            color_discrete_sequence=VGR_TAXES,
            labels={"Valor": "R$", "Label": ""},
            text="Valor",
        )
        fig3.update_traces(
            marker_line_width=0,
            texttemplate="%{y:,.0f}",
            textposition="inside",
            textfont=dict(size=10, color="rgba(255,255,255,0.85)"),
            insidetextanchor="middle",
        )
        fig3.update_layout(
            **CHART_BASE,
            legend_title_text="",
            xaxis=dict(gridcolor="rgba(0,0,0,0)", tickangle=0, automargin=True),
            yaxis=dict(gridcolor="#EEF3F8", zeroline=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Fluxo de pagamentos ───────────────────────────────────────────────────
    st.markdown(
        '<div class="vgr-section-title" style="margin-top:1.5rem;">Fluxo de pagamentos por vencimento</div>',
        unsafe_allow_html=True,
    )

    fluxo = parse_fluxo_pagamentos(df)

    if fluxo.empty:
        st.info("Nenhuma informação de cobrança (duplicatas) encontrada nas NFs carregadas.")
    else:
        total_fluxo = fluxo["valor"].sum()
        n_parcelas = len(fluxo)
        mes_pico = fluxo.groupby("mes_label")["valor"].sum().idxmax()
        valor_pico = fluxo.groupby("mes_label")["valor"].sum().max()

        kf1, kf2, kf3 = st.columns(3)
        kf1.metric("Total a pagar", fmt_brl(total_fluxo))
        kf2.metric("Parcelas", n_parcelas)
        kf3.metric("Mês de maior vencimento", f"{mes_pico} · {fmt_brl(valor_pico)}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Opção de visualização: total ou por fornecedor
        col_vis, _ = st.columns([2, 5])
        with col_vis:
            vis_mode = st.radio(
                "Agrupar por",
                ["Total", "Fornecedor"],
                horizontal=True,
                key="fluxo_mode",
                label_visibility="collapsed",
            )

        if vis_mode == "Total":
            fluxo_mes = (
                fluxo.groupby(["mes", "mes_label"])["valor"]
                .sum()
                .reset_index()
                .sort_values("mes")
            )
            fig_fluxo = px.bar(
                fluxo_mes,
                x="mes_label",
                y="valor",
                labels={"mes_label": "", "valor": "R$"},
                color_discrete_sequence=["#3A9ED0"],
                text="valor",
            )
            fig_fluxo.update_traces(
                marker_line_width=0,
                texttemplate="R$ %{y:,.0f}",
                textposition="outside",
                textfont=dict(size=11, color="#3A9ED0"),
            )
        else:
            fluxo_forn = (
                fluxo.groupby(["mes", "mes_label", "fornecedor"])["valor"]
                .sum()
                .reset_index()
                .sort_values("mes")
            )
            fig_fluxo = px.bar(
                fluxo_forn,
                x="mes_label",
                y="valor",
                color="fornecedor",
                barmode="stack",
                labels={"mes_label": "", "valor": "R$", "fornecedor": "Fornecedor"},
                color_discrete_sequence=VGR_SUPPLIERS,
                text="valor",
            )
            fig_fluxo.update_traces(
                marker_line_width=0,
                texttemplate="%{y:,.0f}",
                textposition="inside",
                textfont=dict(size=10, color="rgba(255,255,255,0.85)"),
                insidetextanchor="middle",
            )
            fig_fluxo.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )

        fig_fluxo.update_layout(
            **CHART_BASE,
            xaxis=dict(gridcolor="rgba(0,0,0,0)", tickangle=0),
            yaxis=dict(gridcolor="#EEF3F8", zeroline=False),
        )
        st.plotly_chart(fig_fluxo, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TABELA
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(
        '<div class="page-header"><div><h2>Tabela de Itens</h2>'
        '<div class="ph-sub">Filtre, explore e exporte os itens das NFs</div></div></div>',
        unsafe_allow_html=True,
    )
    cf1, cf2, cf3 = st.columns([2, 3, 2])

    with cf1:
        fornecedores_opts = ["Todos"] + sorted(df["emit_xNome"].dropna().unique().tolist())
        forn_sel = st.selectbox("Fornecedor", fornecedores_opts)

    with cf2:
        produtos_opts = ["Todos"] + sorted(df["xProd"].dropna().unique().tolist()) if "xProd" in df.columns else ["Todos"]
        prod_sel = st.selectbox("Produto", produtos_opts)

    with cf3:
        search = st.text_input("🔍 Busca livre", placeholder="Digite qualquer coisa...")

    filtered = df.copy()
    if forn_sel != "Todos":
        filtered = filtered[filtered["emit_xNome"] == forn_sel]
    if prod_sel != "Todos":
        filtered = filtered[filtered["xProd"] == prod_sel]
    if search:
        mask = filtered.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    st.caption(f"{len(filtered)} linha(s) exibida(s)")

    display_cols = [
        c for c in [
            "emit_xNome", "nNF", "dhEmi", "xProd", "cProd",
            "qCom_item", "uCom", "vUnCom", "vProd_item",
            "vICMS_item", "vIPI_item", "vPIS_item", "vCOFINS_item", "vICMSST_item",
            "nLote", "dFab", "dVal", "vNF",
        ]
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        height=480,
        column_config={
            "emit_xNome": st.column_config.TextColumn("Fornecedor", width="medium"),
            "nNF": st.column_config.TextColumn("Nº NF"),
            "dhEmi": st.column_config.TextColumn("Emissão"),
            "xProd": st.column_config.TextColumn("Produto", width="large"),
            "cProd": st.column_config.TextColumn("Cód."),
            "qCom_item": st.column_config.NumberColumn("Qtd", format="%.3f"),
            "uCom": st.column_config.TextColumn("Un"),
            "vUnCom": st.column_config.NumberColumn("Preço Unit", format="R$ %.4f"),
            "vProd_item": st.column_config.NumberColumn("Total Item", format="R$ %.2f"),
            "vICMS_item": st.column_config.NumberColumn("ICMS", format="R$ %.2f"),
            "vIPI_item": st.column_config.NumberColumn("IPI", format="R$ %.2f"),
            "vPIS_item": st.column_config.NumberColumn("PIS", format="R$ %.2f"),
            "vCOFINS_item": st.column_config.NumberColumn("COFINS", format="R$ %.2f"),
            "vICMSST_item": st.column_config.NumberColumn("ICMS-ST", format="R$ %.2f"),
            "nLote": st.column_config.TextColumn("Lote"),
            "dFab": st.column_config.DateColumn("Fabricação", format="DD/MM/YYYY"),
            "dVal": st.column_config.DateColumn("Validade", format="DD/MM/YYYY"),
            "vNF": st.column_config.NumberColumn("Total NF", format="R$ %.2f"),
        },
    )

    st.download_button(
        label="⬇️ Exportar Excel",
        data=export_excel(filtered),
        file_name="nfe_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHAT COM IA
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    if not api_key:
        st.warning("Insira sua OpenAI API Key na barra lateral para usar o chat.")
        st.stop()

    st.markdown(
        '<div class="page-header"><div><h2>Chat com IA</h2>'
        '<div class="ph-sub">Pergunte sobre suas NFs em linguagem natural</div></div></div>',
        unsafe_allow_html=True,
    )

    sugestoes = [
        "Valor total de cada NF?",
        "Quanto paguei de ICMS?",
        "Fornecedor mais caro?",
        "Produtos com IPI?",
        "5 produtos mais caros",
    ]
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:var(--text-sub,#64748B);'
        'text-transform:uppercase;letter-spacing:0.09em;margin-bottom:0.65rem;'
        'font-family:Noto Sans,sans-serif;">Sugestões</div>',
        unsafe_allow_html=True,
    )
    _r1 = st.columns(3)
    for i in range(3):
        if _r1[i].button(sugestoes[i], key=f"sug_{i}", use_container_width=True):
            st.session_state._pending_prompt = sugestoes[i]
    _, _c1, _c2, _ = st.columns([1, 1, 1, 1])
    for j, col in enumerate([_c1, _c2]):
        if col.button(sugestoes[3 + j], key=f"sug_{3+j}", use_container_width=True):
            st.session_state._pending_prompt = sugestoes[3 + j]

    st.markdown("<br>", unsafe_allow_html=True)

    # Exibe histórico em ordem correta
    for msg in st.session_state.messages:
        avatar = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Captura input (campo fixo no rodapé ou botão de sugestão)
    prompt = st.chat_input("Ex: Quanto foi a fentanila que comprei da Supermed?")
    if not prompt and "_pending_prompt" in st.session_state:
        prompt = st.session_state.pop("_pending_prompt")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        context = build_llm_context(df)
        system_prompt = (
            "Você é um assistente especializado em análise de Notas Fiscais Eletrônicas (NF-e) "
            "de medicamentos e produtos farmacêuticos.\n"
            "Responda sempre em português brasileiro. Use formatação clara com markdown quando útil.\n"
            "Quando mencionar valores monetários, use o formato R$ X.XXX,XX.\n"
            "Se não tiver a informação nos dados, diga claramente.\n\n"
            f"DADOS DAS NFs CARREGADAS:\n{context}"
        )

        with st.spinner("Analisando..."):
            try:
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *st.session_state.messages,
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = f"Erro ao contatar a OpenAI: {e}"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state.messages:
        if st.button("🗑️ Limpar conversa", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()
