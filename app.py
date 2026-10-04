import io
import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO CUSTOMIZADO
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sistema de Vendas",
    page_icon="🛍️",
    layout="wide"
)

# Estilização CSS para cartões de métricas e botões
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stButton>button {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

NOME_BANCO = "vendas.db"

# -----------------------------------------------------------------------------
# 2. BANCO DE DADOS (SQLite)
# -----------------------------------------------------------------------------
def conectar_banco():
    return sqlite3.connect(NOME_BANCO)

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            produto TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            valor REAL NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM vendas")
    if cursor.fetchone()[0] == 0:
        dados_iniciais = [
            ("2026-10-01", "Ana", "Notebook", 1, 3500.00),
            ("2026-10-02", "Bruno", "Celular", 2, 2500.00),
            ("2026-10-03", "Carla", "Fone", 3, 300.00),
            ("2026-10-04", "Ana", "Fone", 2, 200.00)
        ]
        cursor.executemany("""
            INSERT INTO vendas (data, vendedor, produto, quantidade, valor)
            VALUES (?, ?, ?, ?, ?)
        """, dados_iniciais)
        
    conn.commit()
    conn.close()

inicializar_banco()

@st.cache_data
def carregar_dados():
    conn = conectar_banco()
    df = pd.read_sql("SELECT * FROM vendas", conn)
    conn.close()
    
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df

tabela_vendas = carregar_dados()

# -----------------------------------------------------------------------------
# 3. SIDEBAR: CADASTRO MANUAL & FILTROS
# -----------------------------------------------------------------------------
st.sidebar.markdown("## ➕ Cadastrar Venda Manual")

with st.sidebar.form(key="form_venda", clear_on_submit=True):
    data_cad = st.date_input("Data do Cadastro")
    vendedor = st.selectbox("Vendedor", ["Ana", "Bruno", "Carla"])
    produto = st.selectbox("Produto", ["Notebook", "Celular", "Fone"])
    quantidade = st.number_input("Quantidade", min_value=1, step=1)
    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
    
    botao_cadastrar = st.form_submit_button("💾 Salvar Venda", use_container_width=True)

if botao_cadastrar:
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vendas (data, vendedor, produto, quantidade, valor)
        VALUES (?, ?, ?, ?, ?)
    """, (str(data_cad), vendedor, produto, quantidade, valor))
    conn.commit()
    conn.close()
    
    st.cache_data.clear()
    st.success("Venda cadastrada com sucesso!")
    st.rerun()

st.sidebar.divider()

# --- FILTROS ---
st.sidebar.markdown("## 🔍 Filtros")

if not tabela_vendas.empty:
    min_data = tabela_vendas["data"].min().date()
    max_data = tabela_vendas["data"].max().date()

    intervalo_datas = st.sidebar.date_input(
        "Selecione o Período",
        value=(min_data, max_data),
        min_value=min_data,
        max_value=max_data
    )

    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        data_inicio, data_fim = intervalo_datas
        df_filtrado = tabela_vendas[
            (tabela_vendas["data"].dt.date >= data_inicio) & 
            (tabela_vendas["data"].dt.date <= data_fim)
        ]
    else:
        df_filtrado = tabela_vendas.copy()
else:
    df_filtrado = tabela_vendas.copy()

# -----------------------------------------------------------------------------
# 4. ÁREA PRINCIPAL: DASHBOARD
# -----------------------------------------------------------------------------
st.title("🛍️ Painel de Controle de Vendas")
st.caption("Acompanhamento de vendas em tempo real com estatísticas dinâmicas")

st.markdown("### 📊 Indicadores Principais")

if not df_filtrado.empty:
    col1, col2, col3 = st.columns(3)
    
    faturamento_total = df_filtrado["valor"].sum()
    total_pedidos = len(df_filtrado)
    ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0
    
    col1.metric("💰 Faturamento Total", f"R$ {faturamento_total:,.2f}")
    col2.metric("📦 Total de Pedidos", total_pedidos)
    col3.metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}")

    st.write("")

    # Layout de Gráficos
    col_graf1, col_espaco, col_graf2 = st.columns([1, 0.08, 1])

    with col_graf1:
        st.markdown("##### 👤 Vendas por Vendedor")
        grafico_vendedor = px.bar(
            df_filtrado, 
            x="vendedor", 
            y="valor", 
            color="produto",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={"valor": "Valor (R$)", "vendedor": "Vendedor"}
        )
        grafico_vendedor.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(grafico_vendedor, use_container_width=True)

    with col_graf2:
        st.markdown("##### 🏷️️ Distribuição por Produto")
        grafico_produto = px.pie(
            df_filtrado, 
            names="produto", 
            values="valor",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        grafico_produto.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(grafico_produto, use_container_width=True)
else:
    st.info("Nenhum registro encontrado para exibir gráficos no período selecionado.")

st.divider()

# -----------------------------------------------------------------------------
# 5. GERENCIAMENTO DE DADOS: VISUALIZAR, UPLOAD E EXCLUIR
# -----------------------------------------------------------------------------
st.markdown("### 📋 Gerenciamento de Registro de Vendas")

tab1, tab2, tab3 = st.tabs(["👁 Visualizar Vendas", "📤 Importar Arquivo (CSV/Excel)", "🗑️ Excluir Venda"])

# --- ABA 1: VISUALIZAR & DOWNLOAD ---
with tab1:
    if not df_filtrado.empty:
        df_exibicao = df_filtrado.copy()
        df_exibicao["data"] = df_exibicao["data"].dt.strftime("%d/%m/%Y")
        
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        col_btn1, col_btn2, _ = st.columns([1, 1, 3])

        csv_data = df_exibicao.to_csv(index=False).encode('utf-8')
        col_btn1.download_button(
            label="📥 Baixar em CSV",
            data=csv_data,
            file_name="relatorio_vendas.csv",
            mime="text/csv",
            use_container_width=True
        )

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_exibicao.to_excel(writer, sheet_name='Vendas', index=False)
        excel_data = buffer.getvalue()

        col_btn2.download_button(
            label="📊 Baixar em Excel",
            data=excel_data,
            file_name="relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("Nenhuma venda cadastrada para exibição.")

# --- ABA 2: UPLOAD DE ARQUIVOS ---
with tab2:
    st.markdown("#### Importar Vendas em Lote")
    st.caption("Faça o upload de uma planilha contendo as colunas: `data`, `vendedor`, `produto`, `quantidade`, `valor`.")

    # Botão para baixar modelo de exemplo
    modelo_df = pd.DataFrame([{
        "data": "2026-10-05",
        "vendedor": "Ana",
        "produto": "Notebook",
        "quantidade": 1,
        "valor": 3500.00
    }])
    buffer_modelo = io.BytesIO()
    with pd.ExcelWriter(buffer_modelo, engine='openpyxl') as writer:
        modelo_df.to_excel(writer, index=False)
    
    st.download_button(
        label="📄 Baixar Planilha Modelo (.xlsx)",
        data=buffer_modelo.getvalue(),
        file_name="modelo_importacao_vendas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.write("")

    arquivo_upload = st.file_uploader("Selecione um arquivo CSV ou Excel", type=["csv", "xlsx"])

    if arquivo_upload is not None:
        try:
            # Leitura baseada na extensão do arquivo
            if arquivo_upload.name.endswith(".csv"):
                df_upload = pd.read_csv(arquivo_upload)
            else:
                df_upload = pd.read_excel(arquivo_upload)

            # Padroniza nomes de colunas
            df_upload.columns = [str(col).strip().lower() for col in df_upload.columns]
            colunas_necessarias = {"data", "vendedor", "produto", "quantidade", "valor"}

            if colunas_necessarias.issubset(set(df_upload.columns)):
                st.markdown("**Pré-visualização dos dados a serem importados:**")
                st.dataframe(df_upload, use_container_width=True)

                if st.button("✅ Confirmar e Salvar no Banco de Dados", type="primary"):
                    conn = conectar_banco()
                    
                    # Garante formato correto de texto para data
                    df_upload["data"] = df_upload["data"].astype(str)
                    
                    # Seleciona apenas as colunas corretas para salvar
                    df_para_salvar = df_upload[["data", "vendedor", "produto", "quantidade", "valor"]]
                    
                    # Insere diretamente na tabela SQLite
                    df_para_salvar.to_sql("vendas", conn, if_exists="append", index=False)
                    conn.close()

                    st.cache_data.clear()
                    st.success("Dados importados e salvos no banco com sucesso!")
                    st.rerun()
            else:
                st.error(f"O arquivo precisa conter exatamente as colunas: {', '.join(colunas_necessarias)}")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")

# --- ABA 3: EXCLUSÃO DE REGISTRO ---
with tab3:
    if not df_filtrado.empty:
        st.warning("⚠️ **Atenção:** A exclusão é permanente e removerá o registro do banco de dados.")
        
        opcoes_vendas = {
            f"ID {row['id']} - {row['data'].strftime('%d/%m/%Y')} | {row['vendedor']} - {row['produto']} (R$ {row['valor']:.2f})": row['id']
            for _, row in df_filtrado.iterrows()
        }

        venda_selecionada = st.selectbox(
            "Selecione a venda para remover:",
            options=list(opcoes_vendas.keys())
        )

        id_para_deletar = opcoes_vendas[venda_selecionada] if venda_selecionada else None

        if st.button("🔴 Confirmar e Excluir Venda", type="primary"):
            if id_para_deletar:
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vendas WHERE id = ?", (id_para_deletar,))
                conn.commit()
                conn.close()

                st.cache_data.clear()
                st.success(f"Venda ID {id_para_deletar} excluída com sucesso!")
                st.rerun()
    else:
        st.info("Nenhuma venda disponível para exclusão.")