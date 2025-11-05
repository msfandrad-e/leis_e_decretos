import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Análise de Situações", layout="wide")

# --- SIDEBAR ---
st.sidebar.header("📂 Upload da Planilha")
uploaded_file = st.sidebar.file_uploader(
    "Envie um arquivo (CSV ou Excel). Colunas devem começar na linha 5.",
    type=["csv", "xlsx"]
)

# --- CONTEÚDO PRINCIPAL ---
st.title("📊 Dashboard Interativo de Situações")

if not uploaded_file:
    st.info("👈 Faça o upload de uma planilha no menu lateral para começar a análise.")
    st.stop()


# --- LEITURA DO ARQUIVO ---
@st.cache_data
def load_data(file):
    """Carrega os dados do arquivo com tratamento de erros"""
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file, skiprows=4, dtype=str)
        else:
            df = pd.read_excel(file, skiprows=4, dtype=str)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao ler o arquivo: {e}")
        return None


df = load_data(uploaded_file)

if df is None:
    st.stop()

# --- VALIDAÇÃO DAS COLUNAS ---
colunas_necessarias = [
    "ENCONTRADAS",
    "NÃO ENCONTRADAS",
    "REVOGADAS",
    "MOTIVO DA REVOGAÇÃO",
    "ATUALIZADAS",
    "OUTRAS SITUAÇÕES"
]

colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
if colunas_faltantes:
    st.error(f"⚠️ Colunas faltantes no arquivo: {', '.join(colunas_faltantes)}")
    st.warning("📋 Colunas encontradas no arquivo:")
    st.dataframe(pd.DataFrame(df.columns, columns=["Colunas Disponíveis"]), use_container_width=True)
    st.stop()

# --- PREPARAÇÃO DOS DADOS ---
df_exibicao = df.fillna("").replace("nan", "")


# --- FUNÇÃO PARA CONTAGEM ---
def count_filled(series: pd.Series) -> int:
    """Conta células não vazias"""
    return series.apply(lambda x: str(x).strip() not in ["", "nan", "None"]).sum()


# --- CÁLCULO DOS TOTAIS ---
totais = {}
for col in colunas_necessarias:
    if col != "MOTIVO DA REVOGAÇÃO":
        totais[col] = count_filled(df[col])

# --- FILTROS NA SIDEBAR ---
st.sidebar.header("🎛️ Filtros")
filtro = st.sidebar.selectbox(
    "Filtrar por categoria:",
    options=["Todos", "ENCONTRADAS", "NÃO ENCONTRADAS", "REVOGADAS"],
    index=0
)

# --- DEFINIR COLUNAS PARA EXIBIÇÃO ---
if filtro == "Todos":
    colunas_grafico = [col for col in colunas_necessarias if col != "MOTIVO DA REVOGAÇÃO"]
    colunas_tabela = list(df_exibicao.columns)
elif filtro == "REVOGADAS":
    colunas_grafico = ["REVOGADAS"]
    colunas_tabela = ["REVOGADAS", "MOTIVO DA REVOGAÇÃO"]
else:
    colunas_grafico = [filtro]
    colunas_tabela = [filtro]

# --- MÉTRICAS PRINCIPAIS ---
st.markdown("#### 📈 Métricas Principais")

if filtro == "Todos":
    total_geral = sum(totais.values())
else:
   total_geral = totais.get(filtro, 0)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Filtrado", total_geral)

with col2:
    if filtro == "Todos":
        st.metric("Categorias", len(colunas_grafico))
    else:
        st.metric("Categoria Selecionada", filtro)

with col3:
    st.metric("Registros no Arquivo", len(df))

with col4:
    colunas_preenchidas = sum(1 for col in df.columns if count_filled(df[col]) > 0)
    st.metric("Colunas com Dados", colunas_preenchidas)

# --- GRÁFICO DONUT ---
st.markdown("## 📊 Gráfico de comparação")

if total_geral > 0:
    if filtro == "Todos":
        # Gráfico para todas as categorias
        dados_grafico = []
        for categoria, quantidade in totais.items():
            if quantidade > 0:
                dados_grafico.append({"Categoria": categoria, "Quantidade": quantidade})

        if dados_grafico:
            df_grafico = pd.DataFrame(dados_grafico)
            fig = px.pie(
                df_grafico,
                names="Categoria",
                values="Quantidade",
                title="",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textinfo='percent+label', textfont_size=13)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Não há dados para exibir no gráfico.")
    else:
        # Gráfico para categoria específica
        quantidade = totais.get(filtro, 0)
        if quantidade > 0:
            fig = px.pie(
                names=[filtro, "Outros"],
                values=[quantidade, max(0, len(df) - quantidade)],
                title=f"Distribuição: {filtro}",
                hole=0.4
            )
            fig.update_traces(textinfo='value+percent', textfont_size=13)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Não há registros na categoria '{filtro}'.")
else:
    st.warning("Não há dados para exibir com os filtros atuais.")

# --- TABELA INTERATIVA ---
st.markdown("## 📄 Tabela de Dados Filtrada")

if filtro == "Todos":
    st.dataframe(df_exibicao, use_container_width=True)
else:
    # Filtrar apenas linhas que têm dados na coluna selecionada
    df_filtrado = df_exibicao[df_exibicao[filtro].apply(
        lambda x: str(x).strip() not in ["", "nan", "None"]
    )]

    if not df_filtrado.empty:
        st.dataframe(df_filtrado[colunas_tabela], use_container_width=True)
        st.caption(f"Mostrando {len(df_filtrado)} registros com dados em '{filtro}'")
    else:
        st.info(f"Nenhum registro encontrado com dados em '{filtro}'")

# --- CONTAINER EXPANSÍVEL COM LISTA DE REVOGAÇÕES ---
if filtro == "REVOGADAS" or filtro == "Todos":
    # Filtrar registros que têm dados na coluna REVOGADAS
    revogadas_filtradas = df_exibicao[df_exibicao["REVOGADAS"].apply(
        lambda x: str(x).strip() not in ["", "nan", "None"]
    )]

    if not revogadas_filtradas.empty:
        with st.expander("📋 Lista Detalhada de Revogações", expanded=False):
            st.markdown("### 🎯 Revogações e seus Motivos")

            # Criar lista de revogações com motivos
            for idx, row in revogadas_filtradas.iterrows():
                revogada = row["REVOGADAS"]
                motivo = row["MOTIVO DA REVOGAÇÃO"]

                # Verificar se o motivo está vazio
                if str(motivo).strip() in ["", "nan", "None"]:
                    motivo_exibicao = "❓ *Motivo não informado*"
                    cor_borda = "#ffcccc"  # Vermelho claro para motivos faltantes
                else:
                    motivo_exibicao = motivo
                    cor_borda = "#e6f3ff"  # Azul claro para motivos preenchidos

                # Container para cada item da lista (TAMANHO REDUZIDO)
                with st.container():
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid {cor_borda};
                            border-radius: 8px;
                            padding: 8px 12px;
                            margin: 6px 0;
                            background-color: #fafafa;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                            font-size: 14px;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <strong style="color: #333; font-size: 16px;">🔴 {revogada}</strong>
                                </div>
                                <div style="flex: 2; margin-left: 16px;">
                                    <span style="color: #666; font-size: 15px;"><strong>Motivo:</strong> {motivo_exibicao}</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # Estatísticas rápidas (também reduzidas)
            total_revogadas = len(revogadas_filtradas)
            com_motivo = revogadas_filtradas["MOTIVO DA REVOGAÇÃO"].apply(
                lambda x: str(x).strip() not in ["", "nan", "None"]
            ).sum()
            sem_motivo = total_revogadas - com_motivo

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Revogações", total_revogadas)
            with col2:
                st.metric("Com Motivo", com_motivo)
            with col3:
                st.metric("Sem Motivo", sem_motivo)
    else:
        st.info("Não há registros de revogação para exibir.")

# --- DOWNLOAD DA PLANILHA PROCESSADA ---
st.markdown("## 💾 Exportar Dados")

col1, col2 = st.columns(2)

with col1:
    # Download dos dados filtrados
    if filtro == "Todos":
        dados_exportar = df_exibicao
    else:
        dados_exportar = df_filtrado[colunas_tabela] if 'df_filtrado' in locals() and not df_filtrado.empty else \
        df_exibicao[colunas_tabela]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dados_exportar.to_excel(writer, index=False, sheet_name="Dados Filtrados")

        # Adicionar aba com métricas
        metricas_df = pd.DataFrame({
            'Métrica': ['Total de Registros', 'Categoria Filtrada', 'Registros no Filtro'],
            'Valor': [len(df), filtro, len(dados_exportar)]
        })
        metricas_df.to_excel(writer, index=False, sheet_name="Métricas")

    processed_data = output.getvalue()

    st.download_button(
        label="⬇️ Baixar Excel Processado",
        data=processed_data,
        file_name=f"dados_processados_{filtro.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Baixe os dados filtrados em formato Excel"
    )

with col2:
    # Download do resumo estatístico
    if st.button("📊 Gerar Relatório de Resumo"):
        resumo = []
        for categoria, quantidade in totais.items():
            if quantidade > 0:
                percentual = (quantidade / len(df)) * 100
                resumo.append({
                    'Categoria': categoria,
                    'Quantidade': quantidade,
                    'Percentual (%)': f"{percentual:.1f}%"
                })

        resumo_df = pd.DataFrame(resumo)
        st.dataframe(resumo_df, use_container_width=True)

# --- INFORMAÇÕES ADICIONAIS ---
with st.expander("ℹ️ Informações sobre a Análise"):
    st.markdown("""
    **Como usar este dashboard:**
    - Faça upload de uma planilha CSV ou Excel com as colunas específicas
    - Use o filtro lateral para focar em categorias específicas
    - Visualize a distribuição através dos gráficos
    - Analise os dados detalhados na tabela
    - Para revogações, expanda a seção "Lista Detalhada de Revogações" para ver cada item com seu motivo
    - Exporte os resultados para Excel

    **Colunas necessárias:**
    - ENCONTRADAS, NÃO ENCONTRADAS, REVOGADAS
    - MOTIVO DA REVOGAÇÃO, ATUALIZADAS, OUTRAS SITUAÇÕES
    """)

st.caption(
    f"Arquivo carregado: {uploaded_file.name} | Última atualização: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")