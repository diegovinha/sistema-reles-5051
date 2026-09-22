import numpy as np
import pandas as pd
import plotly.graph_objects as go
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st
import base64
import os
import json
import re
from datetime import datetime
import io
from urllib.parse import quote
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import sqlite3
import hashlib
import secrets

# Inicializa o banco de dados SQLite local com modo WAL (evita travamentos)
def inicializar_banco():
    conn = sqlite3.connect("sistema_reles.db")
    
    # ATIVA O MODO WAL: Permite concorrência de leitura e escrita sem travar
    conn.execute("PRAGMA journal_mode=WAL;")
    
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            profissao TEXT,
            crea TEXT,
            setor TEXT,
            empresa TEXT,
            tel1 TEXT,
            tel2 TEXT,
            ramal TEXT,
            cep TEXT,
            cidade TEXT,
            logradouro TEXT,
            bairro TEXT,
            numero TEXT,
            complemento TEXT,
            senha TEXT NOT NULL,
            token TEXT
        )
    ''')
    
    # Adiciona a coluna token caso a tabela seja antiga
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN token TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

inicializar_banco()

# Funções de Criptografia de Senha
def criar_hash_senha(senha):
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((senha + salt).encode('utf-8')).hexdigest()
    return f"{salt}${pwd_hash}"

def verificar_senha_hash(senha_digitada, senha_armazenada):
    try:
        salt, pwd_hash = senha_armazenada.split('$')
        check_hash = hashlib.sha256((senha_digitada + salt).encode('utf-8')).hexdigest()
        return check_hash == pwd_hash
    except Exception:
        return False
#========================================
#BUSCAR CEP
#========================================
import requests

def buscar_dados_cep(cep):
    cep_limpo = "".join(filter(str.isdigit, str(cep)))
    if len(cep_limpo) == 8:
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        try:
            resposta = requests.get(url, timeout=3)
            dados = resposta.json()
            if not "erro" in dados:
                return dados
        except Exception:
            pass
    return None

# ==========================================
# 0. CONFIGURAÇÃO DA IMAGEM
# ==========================================
# Função para ler a imagem local e convertê-la para Base64
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        return ""

# Caminho relativo seguro (funciona no PC e na Nuvem)
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_imagem = os.path.join(diretorio_atual, "logo_superior.png")

img_base64 = get_base64_image(caminho_imagem)

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO (TOPO DO CÓDIGO)
# ==========================================
st.set_page_config(
    page_title="Ensaio de Curva ANSI (50/51)", layout="wide"
)

# 1. Inicializa o estado se não existir
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = ""
if "crea_usuario" not in st.session_state: st.session_state.crea_usuario = ""
if "celular_usuario" not in st.session_state: st.session_state.celular_usuario = ""
if "empresa_usuario" not in st.session_state: st.session_state.empresa_usuario = ""

# 2. RESTAURAÇÃO VIA URL (Sobrevive ao F5)
# Se o usuário apertar F5, a URL ainda terá os parâmetros e restaurará a sessão instantaneamente
# RESTAURAÇÃO SEGURA VIA TOKEN NA URL (Sobrevive ao F5 sem expor dados)
if not st.session_state.autenticado and "token" in st.query_params:
    token_url = st.query_params.get("token")
    if token_url:
        conn = sqlite3.connect("sistema_reles.db")
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM usuarios WHERE token = ?", (token_url,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            st.session_state.autenticado = True
            st.session_state.usuario_logado = res[0]

# Inicialização dos demais estados da aplicação
if "norma_tipo" not in st.session_state: st.session_state.norma_tipo = "IEC-60255"
if "curva_tipo_iec" not in st.session_state: st.session_state.curva_tipo_iec = "Extremamente inversa"
if "curva_tipo_ieee" not in st.session_state: st.session_state.curva_tipo_ieee = "Moderadamente inversa"
if "curva_tipo_outras" not in st.session_state: st.session_state.curva_tipo_outras = "I x T"
if "partida_51" not in st.session_state: st.session_state.partida_51 = 0.0
if "dial_tms" not in st.session_state: st.session_state.dial_tms = 0.100
if "tolerancia" not in st.session_state: st.session_state.tolerancia = 5.0
if "tempo_instantaneo" not in st.session_state: st.session_state.tempo_instantaneo = 0.0
if "partida_50_manual" not in st.session_state: st.session_state.partida_50_manual = 0.0
if "rtc_selectbox" not in st.session_state: st.session_state.rtc_selectbox = "200 / 5"
if "rtc_str_input" not in st.session_state: st.session_state.rtc_str_input = "1000/5"
if "criterio_50" not in st.session_state: st.session_state.criterio_50 = "Manual Direto"
if "nome_arquivo" not in st.session_state: st.session_state.nome_arquivo = ""
if "caminho_absoluto" not in st.session_state: st.session_state.caminho_absoluto = None
if "ultimo_salvamento" not in st.session_state: st.session_state.ultimo_salvamento = "Nunca salvo"
if "arquivo_carregado_id" not in st.session_state: st.session_state.arquivo_carregado_id = None
if "rele" not in st.session_state: st.session_state.rele = ""
if "fabricante" not in st.session_state: st.session_state.fabricante = ""
if "n_serie" not in st.session_state: st.session_state.n_serie = ""
if "equipamento" not in st.session_state: st.session_state.equipamento = ""
if "solicitante" not in st.session_state: st.session_state.solicitante = ""
if "local" not in st.session_state: st.session_state.local = ""
if "oa" not in st.session_state: st.session_state.oa = ""
if "os_ensaio" not in st.session_state: st.session_state.os_ensaio = ""
if "data_ensaio" not in st.session_state: st.session_state.data_ensaio = ""
if "pontos_ensaio" not in st.session_state:
  st.session_state.pontos_ensaio = [
      {"id": "I1", "iprim": 0.0, "treal": 0.000},
      {"id": "I2", "iprim": 0.0, "treal": 0.000},
      {"id": "I3", "iprim": 0.0, "treal": 0.000},
      {"id": "I4", "iprim": 0.0, "treal": 0.000},
      {"id": "I5", "iprim": 0.0, "treal": 0.000},
  ]

# ==========================================
# VALIDAÇÃO DE SENHA E CONTROLE DE ACESSO
# ==========================================
def validar_senha(senha):
    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 dígitos."
    if not re.search(r"[A-Z]", senha):
        return False, "A senha deve conter pelo menos 1 letra maiúscula."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return False, "A senha deve conter pelo menos 1 caracter especial (ex: @, #, $, !)."
    return True, "Senha válida."

# Inicializa o estado de autenticação
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# SE O F5 FOR APERTADO: Restaura o login através do token
if not st.session_state.autenticado:
    token_url = st.query_params.get("token", "")

    if token_url:
        conn = sqlite3.connect("sistema_reles.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome, crea, tel1, empresa FROM usuarios WHERE token = ?",
            (token_url,)
        )
        usuario_token = cursor.fetchone()
        conn.close()

        if usuario_token:
            st.session_state.autenticado = True
            st.session_state.usuario_logado = usuario_token[0] or ""
            st.session_state.crea_usuario = usuario_token[1] or ""
            st.session_state.celular_usuario = usuario_token[2] or ""
            st.session_state.empresa_usuario = usuario_token[3] or ""

if not st.session_state.autenticado:
    # ----------------------------------------------------
    # CONVERTE A IMAGEM DE FUNDO PARA BASE64
    # ----------------------------------------------------
    caminho_bg = os.path.join(diretorio_atual, "background.png")
    bg_base64 = get_base64_image(caminho_bg)

    # ----------------------------------------------------
    # CSS PARA APLICAR A IMAGEM DE FUNDO E AJUSTAR CORES
    # ----------------------------------------------------
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(10, 25, 47, 0.75), rgba(10, 25, 47, 0.75)), url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <h2 style='
        text-align: center;
        color: #ffffff;
        font-family: Arial, sans-serif;
        font-weight: 700;
        letter-spacing: 0.5px;
    '>
    🔒 Acesso Restrito — 
    <span style='color:#67C5F2;'>Sistema de Coordenação ANSI 50/51</span>
    </h2>
    """, unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #ffffff; margin-bottom: 30px;'>Faça login ou cadastre-se para acessar o ambiente de ensaios e relatórios técnicos.</p>", unsafe_allow_html=True)

    st.markdown("""
    <style>
    /* Labels dos campos */
    .stTextInput label, 
    .stPasswordInput label {
        color: #dbeafe !important;
        font-size: 15px !important;
        font-weight: 500 !important;
    }

        /* Campos de entrada */
    div[data-baseweb="input"] {
        background-color: rgba(255,255,255,0.10) !important;
        border-radius: 10px !important;
    }

    /* Texto digitado */
    div[data-baseweb="input"] input {
        color: #ffffff !important;
        font-size: 16px !important;
    }

    /* Placeholder */
    div[data-baseweb="input"] input::placeholder {
        color: #94a3b8 !important;
    }

    /* Botão Entrar */
    div.stButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(90deg, #1597e5, #67C5F2) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        height: 45px !important;
        font-size: 17px !important;
        font-weight: 600 !important;
        transition: 0.3s;
    }
    /* Texto das abas inativas */
    .stTabs [data-testid="stTab"] [data-testid="stMarkdownContainer"] p {
        color: #cbd5e0 !important;
        font-weight: 600 !important;
    }

    /* Texto da aba ativa */
    .stTabs [data-testid="stTab"][aria-selected="true"] [data-testid="stMarkdownContainer"] p {
        color: #67C5F2 !important;
        font-weight: 700 !important;
    }

    /* Caso o texto esteja em span ao invés de p */
    .stTabs [data-testid="stTab"] [data-testid="stMarkdownContainer"] span {
        color: #cbd5e0 !important;
    }

    .stTabs [data-testid="stTab"][aria-selected="true"] [data-testid="stMarkdownContainer"] span {
        color: #67C5F2 !important;
    }

    /* Linha azul da aba selecionada */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #67C5F2 !important;
        height: 3px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_centro, _ = st.columns([1, 2, 1])
    
    with col_centro:
        tab_login, tab_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Novo Cadastro"])
        
        with tab_login:
            with st.form("form_login"):
                usuario_input = st.text_input("Nome de Usuário", key="login_usuario")
                senha_input = st.text_input("Senha", type="password", key="login_senha")
                st.markdown("<br>", unsafe_allow_html=True)
                btn_entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                
                if btn_entrar:
                    if not usuario_input.strip() or not senha_input:
                        st.error("Preencha o nome de usuário e a senha.")
                    else:
                        conn = sqlite3.connect("sistema_reles.db")
                        cursor = conn.cursor()
                        cursor.execute("SELECT senha, nome, crea, tel1, empresa FROM usuarios WHERE usuario = ?",(usuario_input.strip(),))
                        resultado = cursor.fetchone()
                        conn.close()
                        
                        if resultado and verificar_senha_hash(senha_input, resultado[0]):
                            # Gera um token seguro exclusivo para esta sessão
                            novo_token = secrets.token_hex(32)
                            # Salva o token no banco de dados para este usuário
                            conn = sqlite3.connect("sistema_reles.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE usuarios SET token = ? WHERE usuario = ?", (novo_token, usuario_input.strip()))
                            conn.commit()
                            conn.close()
                            st.session_state.autenticado = True
                            st.session_state.autenticado = True
                            st.session_state.usuario_logado = resultado[1] if resultado[1] else usuario_input.strip()
                            st.session_state.crea_usuario = resultado[2] or ""
                            st.session_state.celular_usuario = resultado[3] or ""
                            st.session_state.empresa_usuario = resultado[4] or ""
                                
                                # URL limpa: mostra apenas o token criptografado, sem expor o nome ou status
                            st.query_params.clear()
                            st.query_params["token"] = novo_token
                                
                            st.success("Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Usuário não encontrado ou senha incorreta.")

   
        
        
        

        with tab_cadastro:
            defaults = {
                "cad_nome": "", "cad_usuario": "", "cad_prof": "", "cad_crea": "", "cad_setor": "", 
                "cad_empresa": "", "cad_tel1": "", "cad_tel2": "", "cad_ramal": "", 
                "cad_cep": "", "cad_logradouro": "", "cad_bairro": "", "cad_cidade": "",
                "cad_numero": "", "cad_complemento": "", "cad_senha": "", "cad_conf_senha": ""
            }
            for chave, valor in defaults.items():
                if chave not in st.session_state:
                    st.session_state[chave] = valor

            st.markdown("""<h3 style="color:#67C5F2;">Endereço por CEP</h3>""", unsafe_allow_html=True)
            col_cep_input, col_cep_btn = st.columns([2, 1])
            with col_cep_input:
                st.text_input("CEP da Empresa", key="cad_cep", max_chars=8, placeholder="00000-000")
            with col_cep_btn:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                buscar_cep = st.button("Buscar CEP", key="btn_buscar_cep", use_container_width=True)

            if buscar_cep:
                cep_atual = st.session_state.get("cad_cep", "")
                cep_limpo = "".join(filter(str.isdigit, str(cep_atual)))
                if len(cep_limpo) != 8:
                    st.error("Digite um CEP válido com 8 dígitos.")
                else:
                    cep_info = buscar_dados_cep(cep_limpo)
                    if cep_info:
                        st.session_state["cad_logradouro"] = cep_info.get("logradouro", "")
                        st.session_state["cad_bairro"] = cep_info.get("bairro", "")
                        st.session_state["cad_cidade"] = f"{cep_info.get('localidade', '')} / {cep_info.get('uf', '')}"
                        st.success("Endereço carregado pelo CEP.")
                    else:
                        st.error("CEP não encontrado.")

            with st.form("form_cadastro", clear_on_submit=False):
                st.text_input("Nome Completo * (Obrigatório)", key="cad_nome")
                
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    st.text_input("Profissão", key="cad_prof")
                    st.text_input("Registro CREA", key="cad_crea")
                    st.text_input("Setor", key="cad_setor")
                    st.text_input("Empresa", key="cad_empresa")
                    st.text_input("Celular 1", key="cad_tel1")
                with col_sub2:
                    st.text_input("Celular 2", key="cad_tel2")
                    st.text_input("Telefone com Ramal", key="cad_ramal")
                    st.text_input("Cidade / Estado", key="cad_cidade")
                
                st.text_input("Logradouro (Rua / Avenida)", key="cad_logradouro")
                
                col_end1, col_end2, col_end3 = st.columns([2, 1, 2])
                with col_end1:
                    st.text_input("Bairro", key="cad_bairro")
                with col_end2:
                    st.text_input("Número", key="cad_numero", placeholder="Ex: 1500")
                with col_end3:
                    st.text_input("Complemento", key="cad_complemento", placeholder="Ex: Sala 42")
                
                st.markdown("---")
                st.markdown("""<h3 style="color:#67C5F2;">Credenciais de Acesso</h3>""", unsafe_allow_html=True)
                st.text_input("Nome de Usuário para Login * (Obrigatório)", key="cad_usuario", help="Ex: joao.silva (único no sistema)")
                st.text_input("Crie uma Senha *", type="password", key="cad_senha", help="Mínimo 8 caracteres, 1 letra maiúscula e 1 caractere especial.")
                st.text_input("Confirme a Senha *", type="password", key="cad_conf_senha")             
                st.markdown("<br>", unsafe_allow_html=True)              
                finalizar_cadastro = st.form_submit_button("Finalizar Cadastro e Entrar", type="primary", use_container_width=True)

            if finalizar_cadastro:
                nome_val = st.session_state.get("cad_nome", "").strip()
                usuario_val = st.session_state.get("cad_usuario", "").strip()
                senha_val = st.session_state.get("cad_senha", "")
                conf_senha_val = st.session_state.get("cad_conf_senha", "")
                
                if not nome_val:
                    st.error("O campo Nome Completo é obrigatório.")
                elif not usuario_val:
                    st.error("O campo Nome de Usuário é obrigatório.")
                elif not secrets.compare_digest(senha_val, conf_senha_val):
                    st.error("As senhas não coincidem.")
                else:
                    valida, msg = validar_senha(senha_val)
                    if not valida:
                        st.error(msg)
                    else:
                        senha_segura = criar_hash_senha(senha_val)
                        conn = None
                        try:
                            conn = sqlite3.connect("sistema_reles.db")
                            cursor = conn.cursor()
                            novo_token = secrets.token_hex(32)
                            cursor.execute('''
                                INSERT INTO usuarios (nome, usuario, profissao, crea, setor, empresa, tel1, tel2, ramal, cep, cidade, logradouro, bairro, numero, complemento, senha)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                nome_val,
                                usuario_val,
                                st.session_state.get("cad_prof", ""),
                                st.session_state.get("cad_crea", ""),
                                st.session_state.get("cad_setor", ""),
                                st.session_state.get("cad_empresa", ""),
                                st.session_state.get("cad_tel1", ""),
                                st.session_state.get("cad_tel2", ""),
                                st.session_state.get("cad_ramal", ""),
                                st.session_state.get("cad_cep", ""),
                                st.session_state.get("cad_cidade", ""),
                                st.session_state.get("cad_logradouro", ""),
                                st.session_state.get("cad_bairro", ""),
                                st.session_state.get("cad_numero", ""),
                                st.session_state.get("cad_complemento", ""),
                                senha_segura
                            ))
                            conn.commit()
                            
                            st.session_state.autenticado = True
                            st.session_state.usuario_logado = nome_val 
                            st.query_params.clear()
                            st.query_params["token"] = novo_token
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Este Nome de Usuário já está em uso. Escolha outro.")
                        except Exception as e:
                            st.error(f"Erro ao salvar cadastro: {e}")
                        finally:
                            if conn is not None:
                                conn.close()
    st.stop()

# ==========================================
# CSS / ESTILO DA PÁGINA
# ==========================================

st.markdown("""
<style>

.secao-protecao_fase {
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 2px solid #D20A2E;
    padding-bottom: 10px;
    margin-bottom: 18px;
}

.icone {
    font-size: 20px;
}

.titulo {
    font-size: 20px;
    font-weight: 700;
    color: #263238;
}

.tag {
    background-color: #D20A2E;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    margin-left: auto;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CAPTURA DOS DADOS DA INTERFACE PARA SALVAMENTO E RELATÓRIO
# ==========================================
def obter_dados_atuais():
    n_tipo = st.session_state.get("norma_tipo", "IEC-60255")
    if n_tipo == "IEC-60255":
        c_tipo = st.session_state.get("curva_tipo_iec", "Extremamente inversa")
    elif n_tipo == "IEEE-ANSI":
        c_tipo = st.session_state.get("curva_tipo_ieee", "Moderadamente inversa")
    elif n_tipo == "Proteção de Máquinas Térmicas":
        c_tipo = st.session_state.get("curva_tipo_outras", "I x T")
    else:
        c_tipo = "Personalizada"

    rtc_sel = st.session_state.get("rtc_selectbox", "200 / 5")
    if rtc_sel == "Personalizado (Digitar)":
        r_str = st.session_state.get("rtc_str_input", "1000/5")
    else:
        r_str = rtc_sel

    pontos_atualizados = []
    for idx, p in enumerate(st.session_state.get("pontos_ensaio", [])):
        iprim_val = st.session_state.get(f"iprim_{idx}", p.get("iprim"))
        treal_val = st.session_state.get(f"treal_{idx}", p.get("treal"))
        pontos_atualizados.append({
            "id": p.get("id"),
            "iprim": iprim_val,
            "treal": treal_val
        })

    return {
    # Identificação do ensaio
    "rele": st.session_state.get("rele", ""),
    "fabricante": st.session_state.get("fabricante", ""),
    "n_serie": st.session_state.get("n_serie", ""),
    "equipamento": st.session_state.get("equipamento", ""),
    "solicitante": st.session_state.get("solicitante", ""),
    "local": st.session_state.get("local", ""),
    "oa": st.session_state.get("oa", ""),
    "os_ensaio": st.session_state.get("os_ensaio", ""),
    "data_ensaio": st.session_state.get("data_ensaio", ""),

    # Responsável pelo ensaio
    "usuario_logado": st.session_state.get("usuario_logado", ""),
    "crea_usuario": st.session_state.get("crea_usuario", ""),
    "celular_usuario": st.session_state.get("celular_usuario", ""),
    "empresa_usuario": st.session_state.get("empresa_usuario", ""),

    # Parâmetros do ensaio
    "norma_tipo": n_tipo,
    "curva_tipo": c_tipo,
    "partida_51": st.session_state.get("partida_51", 10.0),
    "dial_tms": st.session_state.get("dial_tms", 0.18),
    "tolerancia": st.session_state.get("tolerancia", 5.0),
    "tempo_instantaneo": st.session_state.get("tempo_instantaneo", 0.075),
    "rtc_str": r_str,
    "criterio_50": st.session_state.get("criterio_50", "Manual Direto"),
    "partida_50_manual": st.session_state.get("partida_50_manual", 75.0),
    "k_input_user_ieee": st.session_state.get("k_input_user_ieee", 0.0515),
    "alpha_input_user_ieee": st.session_state.get("alpha_input_user_ieee", 2.0),
    "l_input_user_ieee": st.session_state.get("l_input_user_ieee", 0.1217),
    "nome_arquivo": st.session_state.get("nome_arquivo", ""),
    "pontos_ensaio": pontos_atualizados
}

# ==========================================
# 3. ROTINAS DE INICIALIZAÇÃO (NOVO E ABRIR)
# ==========================================
token_atual = st.query_params.get("token", "")

if st.query_params.get("acao") == "novo":
    st.session_state.norma_tipo = "IEC-60255"
    st.session_state.curva_tipo_iec = "Normalmente inversa"
    st.session_state.partida_51 = 0.0
    st.session_state.dial_tms = 0.100
    st.session_state.tolerancia = 5.0
    st.session_state.tempo_instantaneo = 0.0
    st.session_state.partida_50_manual = 0.0
    st.session_state.rtc_selectbox = "200 / 5"
    st.session_state.criterio_50 = "Manual Direto"
    st.session_state.nome_arquivo = ""
    st.session_state.caminho_absoluto = None
    st.session_state.ultimo_salvamento = "Nunca salvo"
        # Limpa a identificação do ensaio
    st.session_state.rele = ""
    st.session_state.fabricante = ""
    st.session_state.n_serie = ""
    st.session_state.equipamento = ""
    st.session_state.solicitante = ""
    st.session_state.local = ""
    st.session_state.oa = ""
    st.session_state.os_ensaio = ""
    st.session_state.data_ensaio = ""
    st.session_state.pontos_ensaio = [
      {"id": "I1", "iprim": 0.0, "treal": 0.000},
      {"id": "I2", "iprim": 0.0, "treal": 0.000},
      {"id": "I3", "iprim": 0.0, "treal": 0.000},
      {"id": "I4", "iprim": 0.0, "treal": 0.000},
      {"id": "I5", "iprim": 0.0, "treal": 0.000},
    ]
    for idx in range(10):
        if f"iprim_{idx}" in st.session_state: del st.session_state[f"iprim_{idx}"]
        if f"treal_{idx}" in st.session_state: del st.session_state[f"treal_{idx}"]
        # Remove somente a ação "novo" e preserva a autenticação
    st.query_params.clear()
    st.query_params["token"] = token_atual
    st.rerun()
    
    # Limpa a URL mas RECOLOCA o token para manter o usuário logado
    st.query_params.clear()
    if token_atual:
        st.query_params["token"] = token_atual
    st.rerun()

if "abrir_json" in st.query_params:
    try:
        data = json.loads(st.query_params["abrir_json"])
        st.session_state.norma_tipo = data.get("norma_tipo", "IEC-60255")
        st.session_state.partida_51 = data.get("partida_51", 20.0)
        st.session_state.dial_tms = data.get("dial_tms", 0.100)
        st.session_state.tolerancia = data.get("tolerancia", 5.0)
        st.session_state.tempo_instantaneo = data.get("tempo_instantaneo", 0.0)
        
        rtc_carregado = data.get("rtc_str", "200 / 5")
        opcoes_rtc_validas = ["100 / 5", "150 / 5", "200 / 5", "300 / 5", "400 / 5", "600 / 5", "800 / 5"]
        if rtc_carregado in opcoes_rtc_validas:
            st.session_state.rtc_selectbox = rtc_carregado
        else:
            st.session_state.rtc_selectbox = "Personalizado (Digitar)"
            st.session_state.rtc_str_input = rtc_carregado
            
        st.session_state.criterio_50 = data.get("criterio_50", "Manual Direto")
        st.session_state.partida_50_manual = data.get("partida_50_manual", 160.0)
        st.session_state.nome_arquivo = data.get("nome_arquivo", "ensaio_rele_5051.json")
        st.session_state.caminho_absoluto = None 
        
        norma_carregada = data.get("norma_tipo", "IEC-60255")
        curva_carregada = data.get("curva_tipo", "")
        if norma_carregada == "IEC-60255":
            st.session_state.curva_tipo_iec = curva_carregada
        elif norma_carregada == "IEEE-ANSI":
            st.session_state.curva_tipo_ieee = curva_carregada
        else:
            st.session_state.curva_tipo_outras = curva_carregada

        if "pontos_ensaio" in data:
            st.session_state.pontos_ensaio = data["pontos_ensaio"]
            for idx, p in enumerate(data["pontos_ensaio"]):
                st.session_state[f"iprim_{idx}"] = float(p.get("iprim", 0.0))
                st.session_state[f"treal_{idx}"] = float(p.get("treal", 0.0))
                
        st.query_params.clear()
        if token_atual:
            st.query_params["token"] = token_atual
        st.rerun()
    except Exception as e:
        st.query_params.clear()
        if token_atual:
            st.query_params["token"] = token_atual

# ==========================================
# RESTAURAÇÃO DOS DADOS AO ABRIR O RELATÓRIO
# (preserva os valores atuais mesmo com a navegação da navbar)
# ==========================================
if "dados_relatorio" in st.query_params:
    try:
        dados_relatorio = json.loads(st.query_params["dados_relatorio"])
                # Restaura a identificação do ensaio
        st.session_state.rele = dados_relatorio.get("rele", "")
        st.session_state.fabricante = dados_relatorio.get("fabricante", "")
        st.session_state.n_serie = dados_relatorio.get("n_serie", "")
        st.session_state.equipamento = dados_relatorio.get("equipamento", "")
        st.session_state.solicitante = dados_relatorio.get("solicitante", "")
        st.session_state.local = dados_relatorio.get("local", "")
        st.session_state.oa = dados_relatorio.get("oa", "")
        st.session_state.os_ensaio = dados_relatorio.get("os_ensaio", "")
        st.session_state.data_ensaio = dados_relatorio.get("data_ensaio", "")
        st.session_state.norma_tipo = dados_relatorio.get("norma_tipo", st.session_state.get("norma_tipo", "IEC-60255"))
        st.session_state.partida_51 = dados_relatorio.get("partida_51", st.session_state.get("partida_51", 0.0))
        st.session_state.dial_tms = dados_relatorio.get("dial_tms", st.session_state.get("dial_tms", 0.100))
        st.session_state.tolerancia = dados_relatorio.get("tolerancia", st.session_state.get("tolerancia", 5.0))
        st.session_state.tempo_instantaneo = dados_relatorio.get("tempo_instantaneo", st.session_state.get("tempo_instantaneo", 0.0))
        st.session_state.criterio_50 = dados_relatorio.get("criterio_50", st.session_state.get("criterio_50", "Manual Direto"))
        st.session_state.partida_50_manual = dados_relatorio.get("partida_50_manual", st.session_state.get("partida_50_manual", 0.0))
        st.session_state.rtc_selectbox = dados_relatorio.get("rtc_str", st.session_state.get("rtc_selectbox", "200 / 5"))
        st.session_state.rtc_str_input = dados_relatorio.get("rtc_str", st.session_state.get("rtc_str_input", "1000/5"))
        st.session_state.k_input_user_ieee = float(dados_relatorio.get("k_input_user_ieee", st.session_state.get("k_input_user_ieee", 0.0515)))
        st.session_state.alpha_input_user_ieee = float(dados_relatorio.get("alpha_input_user_ieee", st.session_state.get("alpha_input_user_ieee", 2.0)))
        st.session_state.l_input_user_ieee = float(dados_relatorio.get("l_input_user_ieee", st.session_state.get("l_input_user_ieee", 0.1217)))
        st.session_state.pontos_ensaio = dados_relatorio.get("pontos_ensaio", st.session_state.get("pontos_ensaio", []))
        # Restaura os dados do responsável pelo ensaio
        st.session_state.usuario_logado = dados_relatorio.get("usuario_logado", "")
        st.session_state.crea_usuario = dados_relatorio.get("crea_usuario", "")
        st.session_state.celular_usuario = dados_relatorio.get("celular_usuario", "")
        st.session_state.empresa_usuario = dados_relatorio.get("empresa_usuario", "")

        norma_carregada = st.session_state.norma_tipo
        curva_carregada = dados_relatorio.get("curva_tipo", "")
        if norma_carregada == "IEC-60255":
            st.session_state.curva_tipo_iec = curva_carregada
        elif norma_carregada == "IEEE-ANSI":
            st.session_state.curva_tipo_ieee = curva_carregada
        else:
            st.session_state.curva_tipo_outras = curva_carregada

        for idx, ponto in enumerate(st.session_state.pontos_ensaio):
            st.session_state[f"iprim_{idx}"] = float(ponto.get("iprim", 0.0))
            st.session_state[f"treal_{idx}"] = float(ponto.get("treal", 0.0))
    except Exception:
        pass

# ==========================================
# 4. RENDERIZAÇÃO DA NAVBAR E CSS
# ==========================================
caminho_bg = os.path.join(diretorio_atual, "background.png")
bg_base64 = get_base64_image(caminho_bg)

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(10, 25, 47, 0.75), rgba(10, 25, 47, 0.75)), url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <style>
/* Torna o cabeçalho padrão transparente para não conflitar com o seu design */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Esconde os menus extras do Streamlit (como Deploy e os três pontinhos), 
       mas preserva o botão de abrir/fechar a barra lateral */
    .stToolbar {
        display: none !important;
    }
    
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 2rem;
    }
    
    .navbar {
        background-color: #1a365d;
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 0px 0px 8px 8px;
        margin-bottom: 10px;
        margin-top: 0px;
        width: 100%;
        font-family: sans-serif;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .navbar-brand {
        font-size: 22px;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 8px;
        letter-spacing: 0.5px;
    }
    .navbar-links {
        display: flex;
        gap: 20px;
        align-items: center;
        font-size: 14px;
    }
    .navbar-links a {
        color: white;
        text-decoration: none;
        transition: color 0.2s;
    }
    .navbar-links a:hover {
        color: #cbd5e0;
    }
    .logo-univesp {
        height: 100px; 
        margin-left: 10px;
        border-radius: 4px;
        object-fit: contain;
    }
    
    [data-testid="stFileUploadDropzone"] > div > small {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if img_base64:
    # Se a sua imagem for JPG, use image/jpeg. Se for PNG, use image/png
    html_logo = f'<img src="data:image/jpeg;base64,{img_base64}" class="logo-univesp" alt="Logo">'
else:
    html_logo = '<span style="color:#e53e3e; font-weight:bold; margin-left:10px;">Logo Não Encontrada</span>'

# Os dados e o token são codificados no próprio link
_dados_relatorio_link = obter_dados_atuais()
_relatorio_link_url = f"?token={token_atual}&acao=gerar_relatorio&dados_relatorio=" + quote(
    json.dumps(_dados_relatorio_link, ensure_ascii=False, separators=(",", ":"))
)

st.markdown(
    f"""
    <div class="navbar">
        <div class="navbar-brand">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                <path d="M12 8v4"></path>
                <path d="M12 16h.01"></path>
            </svg>
            Sistema de Ensaio de Relés ANSI 50/51
        </div>
        <div class="navbar-links">
            <a href="{_relatorio_link_url}" target="_blank">Gerar Relatório PDF</a>
            <a href="#">Normas ⏷</a>
            {html_logo}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# CARD DE BOAS-VINDAS ESPAÇOSO E ELEGANTE
# ==========================================
if st.session_state.get("autenticado", False):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    # Captura data e hora oficial do Brasil
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    data_atual = agora.strftime("%d/%m/%Y")
    hora_atual = agora.strftime("%H:%M:%S")
    
    # Resgata o nome completo do session_state
    nome_usuario = st.session_state.get("usuario_logado", "Usuário")
    
    # Renderiza o card espaçoso (altura de 70-90px com padding confortável)
    st.markdown(f"""
        <div style="
            background-color: #f8fafc; 
            border-left: 6px solid #1a365d; 
            padding: 18px 24px; 
            border-radius: 8px; 
            margin-bottom: 22px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div style="
                    background-color: #1a365d; 
                    color: white; 
                    border-radius: 50%; 
                    width: 44px; 
                    height: 44px; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    font-size: 20px;
                ">👤</div>
                <div>
                    <div style="font-weight: bold; color: #1a365d; font-size: 16px; margin-bottom: 2px;">
                        👋 Bem-vindo, {nome_usuario}
                    </div>
                    <div style="color: #4a5568; font-size: 13px;">
                        Seu acesso foi realizado com sucesso.
                    </div>
                </div>
            </div>
            <div style="color: #4a5568; font-size: 13px; text-align: right; font-family: monospace; line-height: 1.5;">
                📅 Data do Acesso: {data_atual}<br>
                🕐 Horário do Acesso: {hora_atual}
            </div>
        </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Painel do Usuário")
    st.write(f"Logado como:\n**{st.session_state.get('usuario_logado', 'Usuário')}**")
    st.markdown("---")
    
    # EXPANDE O PERFIL E DADOS CADASTRAIS PARA EDIÇÃO
    with st.expander("✏️ Meus Dados & Cadastro", expanded=False):
        # Busca os dados atuais com segurança no banco com WAL mode
        try:
            with sqlite3.connect("sistema_reles.db", timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nome, profissao, crea, setor, empresa, tel1, tel2, ramal, cep, cidade, logradouro, bairro, numero, complemento 
                    FROM usuarios WHERE nome = ? OR usuario = ?
                """, (st.session_state.get('usuario_logado'), st.session_state.get('usuario_logado')))
                user_data = cursor.fetchone()
        except Exception as e:
            user_data = None
            st.error(f"Erro ao ler dados: {e}")
        
        if user_data:
            d_nome, d_prof, d_crea, d_setor, d_emp, d_tel1, d_tel2, d_ramal, d_cep, d_cidade, d_logr, d_bairro, d_num, d_comp = [
                val if val is not None else "" for val in user_data
            ]
            
            with st.form("form_editar_perfil"):
                st.markdown("<b>Dados Profissionais e Pessoais</b>", unsafe_allow_html=True)
                edit_nome = st.text_input("Nome Completo", value=d_nome, key="perfil_nome")
                edit_prof = st.text_input("Profissão", value=d_prof, key="perfil_prof")
                edit_crea = st.text_input("Registro CREA", value=d_crea, key="perfil_crea")
                edit_setor = st.text_input("Setor", value=d_setor, key="perfil_setor")
                edit_emp = st.text_input("Empresa", value=d_emp, key="perfil_emp")
                
                st.markdown("<b>Contatos</b>", unsafe_allow_html=True)
                edit_tel1 = st.text_input("Celular 1", value=d_tel1, key="perfil_tel1")
                edit_tel2 = st.text_input("Celular 2", value=d_tel2, key="perfil_tel2")
                edit_ramal = st.text_input("Ramal", value=d_ramal, key="perfil_ramal")
                
                st.markdown("<b>Endereço</b>", unsafe_allow_html=True)
                edit_cep = st.text_input("CEP", value=d_cep, key="perfil_cep")
                edit_cidade = st.text_input("Cidade / Estado", value=d_cidade, key="perfil_cidade")
                edit_logr = st.text_input("Logradouro", value=d_logr, key="perfil_logr")
                edit_bairro = st.text_input("Bairro", value=d_bairro, key="perfil_bairro")
                edit_num = st.text_input("Número", value=d_num, key="perfil_num")
                edit_comp = st.text_input("Complemento", value=d_comp, key="perfil_comp")
                
                st.markdown("<br>", unsafe_allow_html=True)
                btn_salvar_perfil = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                
                if btn_salvar_perfil:
                    try:
                        with sqlite3.connect("sistema_reles.db", timeout=10) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE usuarios SET 
                                nome = ?, profissao = ?, crea = ?, setor = ?, empresa = ?, 
                                tel1 = ?, tel2 = ?, ramal = ?, cep = ?, cidade = ?, 
                                logradouro = ?, bairro = ?, numero = ?, complemento = ?
                                WHERE nome = ? OR usuario = ?
                            """, (
                                edit_nome, edit_prof, edit_crea, edit_setor, edit_emp,
                                edit_tel1, edit_tel2, edit_ramal, edit_cep, edit_cidade,
                                edit_logr, edit_bairro, edit_num, edit_comp,
                                st.session_state.get('usuario_logado'), st.session_state.get('usuario_logado')
                            ))
                            conn.commit()
                        
                        # Atualiza a sessão e dispara o aviso flutuante
                        st.session_state.usuario_logado = edit_nome
                        st.toast("Dados atualizados com sucesso!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

    st.markdown("---")
    
    # Botão de Logout seguro
    if st.button("🚪 Encerrar Sessão (Sair)", type="secondary", use_container_width=True):
        usuario_atual = st.session_state.get('usuario_logado', '')
        try:
            with sqlite3.connect("sistema_reles.db", timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET token = NULL WHERE nome = ? OR usuario = ?", (usuario_atual, usuario_atual))
                conn.commit()
        except Exception:
            pass
            
        st.session_state.autenticado = False
        st.session_state.usuario_logado = ""
        st.query_params.clear()
        st.rerun()

        # --- RODAPÉ DA BARRA LATERAL ---
    
    st.markdown(
        """
        <br>
        <div style="
            text-align: center; 
            color: #718096; 
            font-size: 12px; 
            border-top: 1px solid #e2e8f0; 
            padding-top: 12px; 
            margin-top: 20px;
        ">
            <b style="color: #2d3748; font-size: 16px;">Contato:</b>
            <br><br>E-mail:
            <a href="mailto:diegovinha57@gmail.com" style="color: #4a5568; font-size: 11.5px; text-decoration: none;">
                ✉️ diegovinha57@gmail.com
            </a>
            <br>Linkedin:
            <a href="https://www.linkedin.com/in/diego-costa-vinha-4942926a/" target="_blank" style="color: #2d3748; font-size: 13px; font-weight: bold; text-decoration: none;">
                diego_vinha 🔗
            </a>
            <br>
            <a href="https://wa.me/5543996113960" target="_blank" style="color: #25D366; font-size: 11.5px; text-decoration: none; font-weight: bold; display: inline-flex; align-items: center; justify-content: center; gap: 4px; margin-top: 4px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="#25D366" viewBox="0 0 16 16">
                  <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.558 6.558 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.348.1-.1.133-.172.198-.298.065-.125.032-.235-.016-.33-.048-.096-.445-1.072-.61-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.078.38-.057 1.17-.478 1.338-.94.17-.463.17-.861.119-.94-.051-.079-.187-.128-.384-.227z"/>
                </svg>
                (43) 99611-3960
            </a>
 
        <div style="
            text-align: center; 
            color: #718096; 
            font-size: 12px; 
            border-top: 1px solid #e2e8f0; 
            padding-top: 12px; 
            margin-top: 20px;
        ">
            Desenvolvido por:<br>
            <b style="color: #2d3748; font-size: 13px;">Diego Costa Vinha</b>
            <br>Versão:
            <b style="color: #2d3748; font-size: 13px;">1.0.0</b>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# FUNÇÕES DE APOIO E CÁLCULO DIRETO DA SESSÃO
# ==========================================
def get_parametros_sessao():
    n_tipo = st.session_state.get("norma_tipo", "IEC-60255")
    if n_tipo == "IEC-60255":
        c_tipo = st.session_state.get("curva_tipo_iec", "Extremamente inversa")
    elif n_tipo == "IEEE-ANSI":
        c_tipo = st.session_state.get("curva_tipo_ieee", "Moderadamente inversa")
    elif n_tipo == "Outras":
        c_tipo = st.session_state.get("curva_tipo_outras", "I x T")
    else: 
        c_tipo = st.session_state.get("curva_personalizada", "Personalizada")

    p_51 = st.session_state.get("partida_51", 0.0)
    tms = st.session_state.get("dial_tms", 0.100)
    tol = st.session_state.get("tolerancia", 5.0)
    t_inst = st.session_state.get("tempo_instantaneo", 0.0)
    crit_50 = st.session_state.get("criterio_50", "Manual Direto")
    p_50_man = st.session_state.get("partida_50_manual", 0.0)
    
    rtc_sel = st.session_state.get("rtc_selectbox", "200 / 5")
    if rtc_sel == "Personalizado (Digitar)":
        r_str = st.session_state.get("rtc_str_input", "1000/5")
    else:
        r_str = rtc_sel
        
    try:
        tc_p, tc_s = map(float, r_str.replace(" ", "").split("/"))
        rel_tc = tc_p / tc_s
    except Exception:
        rel_tc = 40.0
        
    return n_tipo, c_tipo, p_51, tms, tol, t_inst, crit_50, p_50_man, r_str, rel_tc

def get_parametros_norma_dict(n_tipo, c_tipo):
    if n_tipo == "IEC-60255":
        tabela = {
            "Normalmente inversa": {"K": 0.14, "alpha": 0.02},
            "Muito inversa": {"K": 13.5, "alpha": 1.0},
            "Extremamente inversa": {"K": 80.0, "alpha": 2.0},
            "Inversa longa": {"K": 120.0, "alpha": 1.0},
            "Inversa curta": {"K": 0.05, "alpha": 0.04},
        }
        return tabela.get(c_tipo, {"K": 80.0, "alpha": 2.0})
    elif n_tipo == "IEEE-ANSI":
        tabela = {
            "Moderadamente inversa": {"K": 0.0515, "alpha": 0.02, "L": 0.1140},
            "Muito inversa": {"K": 19.61, "alpha": 2.0, "L": 0.491},
            "Extremamente inversa": {"K": 28.2, "alpha": 2.0, "L": 0.1217},
        }
        return tabela.get(c_tipo, {"K": 0.0515, "alpha": 0.02, "L": 0.1140})
    elif n_tipo == "Personalizada":
# Proteção caso ocorra algum valor inválido na sessão
        try:
            k_val = float(st.session_state.get("k_input_user_ieee", 0.0515))
            alpha_val = float(st.session_state.get("alpha_input_user_ieee", 2.0))
            l_val = float(st.session_state.get("l_input_user_ieee", 0.1217))
        except (ValueError, TypeError):
            k_val, alpha_val, l_val = 0.0515, 2.0, 0.1217
        return {"K": k_val, "alpha": alpha_val, "L": l_val}
    return{}

def calcular_teorico_geral(i_prim, n_tipo, c_tipo, p_51, tms, p_50, t_inst):
    if i_prim >= p_50:
        return t_inst
    p51_calc = max(p_51, 0.001)
    if n_tipo == "IEC-60255":
        if i_prim <= p51_calc:
            return np.nan
        p = get_parametros_norma_dict(n_tipo, c_tipo)
        return tms * (p["K"] / (((i_prim / p51_calc) ** p["alpha"]) - 1))
    elif n_tipo in ["IEEE-ANSI"]:
        if i_prim < 1.1 * p51_calc:
            return np.nan
        m = i_prim / p51_calc
        if m > 20.0: m = 20.0
        p = get_parametros_norma_dict(n_tipo, c_tipo)
        return tms * ((p["K"] / ((m**p["alpha"]) - 1)) + p["L"])
    elif n_tipo in ["Personalizada"]:
        if i_prim <= p51_calc:  # Garante o comportamento IEC se L=0 (atua logo acima de Ip)
            return np.nan         
        m = i_prim / p51_calc         
        p = get_parametros_norma_dict(n_tipo, c_tipo)
        return tms * ((p["K"] / ((m**p["alpha"]) - 1)) + p["L"])
    else:
        if i_prim <= p51_calc:
            return np.nan
        m = i_prim / p51_calc
        if c_tipo == "I x T":
            return (60 / m) * tms
        else:
            return (540 / (m**2)) * tms

# ==========================================
# FUNÇÃO DE GERAÇÃO DO RELATÓRIO PDF EM MEMÓRIA
# ==========================================
def gerar_pdf_relatorio():
    n_tipo, c_tipo, p_51, tms, tol, t_inst, crit_50, p_50_man, rtc_str, rel_tc = get_parametros_sessao()
    p_50 = p_50_man

        # Identificação do ensaio
    rele = st.session_state.get("rele", "")
    fabricante = st.session_state.get("fabricante", "")
    n_serie = st.session_state.get("n_serie", "")
    equipamento = st.session_state.get("equipamento", "")
    solicitante = st.session_state.get("solicitante", "")
    local = st.session_state.get("local", "")
    oa = st.session_state.get("oa", "")
    os_ensaio = st.session_state.get("os_ensaio", "")
    data_ensaio = st.session_state.get("data_ensaio", "")
   
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=TA_CENTER, textColor=colors.HexColor('#1a365d'))
    subtitle_style = ParagraphStyle('ReportSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, alignment=TA_CENTER, textColor=colors.HexColor('#4a5568'))
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=colors.HexColor('#1a365d'), spaceBefore=8, spaceAfter=3)
    normal_style = ParagraphStyle('ReportNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#2d3748'))
    bold_style = ParagraphStyle('ReportBold', parent=normal_style, fontName='Helvetica-Bold')
    table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.white)
    table_cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.HexColor('#2d3748'))

    #arq_atual = st.session_state.get('nome_arquivo', '')
    #arq_display = arq_atual if arq_atual else "Novo Arquivo em Edição (Sem Título)"

    story.append(Paragraph("Relatório Técnico de Ensaio de Coordenação e Seletividade", title_style))
    story.append(Paragraph("Análise de Sobrecorrente Temporizada e Instantânea", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Data de Emissão: {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M:%S')}", subtitle_style))
    #story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} | Arquivo em Análise: {arq_display}", subtitle_style))
    story.append(Spacer(1, 8))

    # ==========================================
    # RESPONSÁVEL PELO ENSAIO
    # ==========================================
    nome_responsavel = st.session_state.get("usuario_logado", "")
    crea_responsavel = st.session_state.get("crea_usuario", "")
    celular_responsavel = st.session_state.get("celular_usuario", "")
    empresa_responsavel = st.session_state.get("empresa_usuario", "")

    story.append(Spacer(1, 18))
    story.append(Paragraph("Responsável pelo Ensaio", heading_style))

    responsavel_data = [
        [
            Paragraph("Nome:", bold_style),
            Paragraph(nome_responsavel or "—", normal_style),
            Paragraph("CREA:", bold_style),
            Paragraph(crea_responsavel or "—", normal_style),
        ],
        [
            Paragraph("Empresa:", bold_style),
            Paragraph(empresa_responsavel or "—", normal_style),
            Paragraph("Celular:", bold_style),
            Paragraph(celular_responsavel or "—", normal_style),
        ],
    ]

    t_responsavel = Table(
        responsavel_data,
        colWidths=[55, 245, 55, 185]
    )

    t_responsavel.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))

    story.append(t_responsavel)    

    # ==========================================
    # IDENTIFICAÇÃO DO ENSAIO
    # ==========================================
    story.append(Paragraph("Identificação do Ensaio", heading_style))

    ident_data = [
        [
            Paragraph("<b>Modelo do Relé:</b>", normal_style),
            Paragraph(str(st.session_state.get("rele", "") or "—"), normal_style),
            Paragraph("<b>Fabricante:</b>", normal_style),
            Paragraph(str(st.session_state.get("fabricante", "") or "—"), normal_style),
            Paragraph("<b>Nº de Série:</b>", normal_style),
            Paragraph(str(st.session_state.get("n_serie", "") or "—"), normal_style),
        ],
        [
            Paragraph("<b>ID Equipamento:</b>", normal_style),
            Paragraph(str(st.session_state.get("equipamento", "") or "—"), normal_style),
            Paragraph("<b>Solicitante:</b>", normal_style),
            Paragraph(str(st.session_state.get("solicitante", "") or "—"), normal_style),
            Paragraph("<b>Local:</b>", normal_style),
            Paragraph(str(st.session_state.get("local", "") or "—"), normal_style),
        ],
        [
            Paragraph("<b>O/A:</b>", normal_style),
            Paragraph(str(st.session_state.get("oa", "") or "—"), normal_style),
            Paragraph("<b>O/S:</b>", normal_style),
            Paragraph(str(st.session_state.get("os_ensaio", "") or "—"), normal_style),
            Paragraph("<b>Data do Ensaio:</b>", normal_style),
            Paragraph(str(st.session_state.get("data_ensaio", "") or "—"), normal_style),
        ],
    ]

    t_ident = Table(
        ident_data,
        colWidths=[75, 105, 65, 115, 75, 105]
    )

    t_ident.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))

    story.append(t_ident)
    story.append(Spacer(1, 8))

    
    story.append(Paragraph("1. Informações e Parâmetros Atuais da Página", heading_style))
    
    params_data = [
        [Paragraph("Norma Utilizada:", bold_style), Paragraph(n_tipo, normal_style), Paragraph("Partida 51 (A prim):", bold_style), Paragraph(f"{p_51:.2f} A", normal_style)],
        [Paragraph("Curva Selecionada:", bold_style), Paragraph(c_tipo, normal_style), Paragraph("Dial (TMS):", bold_style), Paragraph(f"{tms:.3f}", normal_style)],
        [Paragraph("Relação RTC:", bold_style), Paragraph(f"{rtc_str} ({rel_tc:.0f}:1)", normal_style), Paragraph("Tolerância (±%):", bold_style), Paragraph(f"± {tol:.1f}%", normal_style)],
        [Paragraph("Critério Unidade 50:", bold_style), Paragraph(crit_50, normal_style), Paragraph("Partida 50 / Tempo 50:", bold_style), Paragraph(f"{p_50:.2f} A / {t_inst:.3f} s", normal_style)]
    ]
    
    t_params = Table(params_data, colWidths=[110, 140, 115, 175])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_params)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("2. Tabela Completa de Pontos de Ensaio Ativos", heading_style))
    
    table_data = [[
        Paragraph("ID do Ponto", table_header_style),
        Paragraph("Corrente Primária (A)", table_header_style),
        Paragraph("Corrente Secundária (A)", table_header_style),
        Paragraph("Tempo Teórico (s)", table_header_style),
        Paragraph("Tempo Real (s)", table_header_style),
        Paragraph("Erro Relativo (%)", table_header_style),
        Paragraph("Status do Teste", table_header_style)
    ]]
    
    aprovados = 0
    reprovados = 0
    fora_curva = 0
    
    pontos_ativos = st.session_state.get("pontos_ensaio", [])
    
    for idx, p in enumerate(pontos_ativos):
        iprim = st.session_state.get(f"iprim_{idx}", p.get("iprim", 0.0))
        treal = st.session_state.get(f"treal_{idx}", p.get("treal", 0.0))
        isec = iprim / rel_tc if rel_tc > 0 else 0.0
        t_teorico = calcular_teorico_geral(iprim, n_tipo, c_tipo, p_51, tms, p_50, t_inst)
        
        if pd.isna(t_teorico) or t_teorico == 0:
            t_teorico_str = "Infinito"
            erro_str = "N/A"
            status = "Fora da curva"
            fora_curva += 1
        else:
            t_teorico_str = f"{t_teorico:.3f} s"
            erro = ((treal - t_teorico) / t_teorico) * 100
            erro_str = f"{erro:+.1f}%"
            if abs(erro) <= tol:
                status = "Aprovado"
                aprovados += 1
            else:
                status = "Reprovado"
                reprovados += 1
                
        status_color = '#22543d' if status == 'Aprovado' else '#742a2a' if status == 'Reprovado' else '#4a5568'
        
        table_data.append([
            Paragraph(str(p.get("id")), table_cell_style),
            Paragraph(f"{iprim:.1f}", table_cell_style),
            Paragraph(f"{isec:.2f}", table_cell_style),
            Paragraph(t_teorico_str, table_cell_style),
            Paragraph(f"{treal:.3f}", table_cell_style),
            Paragraph(erro_str, table_cell_style),
            Paragraph(f"<font color='{status_color}'><b>{status}</b></font>", table_cell_style)
        ])
        
    t_points = Table(table_data, colWidths=[45, 80, 80, 75, 75, 70, 115])
    t_points.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a365d')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_points)
    story.append(Spacer(1, 8))

    # Geração do Gráfico via Matplotlib
    try:
        fig_mpl, ax = plt.subplots(figsize=(6.5, 3.5), dpi=200)
        
        p51_plot = max(p_51, 0.001)
        p50_plot = max(p_50, 0.001)
        #limite_inf_plot = p51_plot * 1.1 if n_tipo == "IEEE-ANSI" else p51_plot * 1.01
        limite_inf_plot = p51_plot * 1.001    
        if p50_plot > limite_inf_plot:
            i_vals_51 = np.logspace(np.log10(limite_inf_plot), np.log10(p50_plot), 100)
        else:
            i_vals_51 = np.array([limite_inf_plot])
        
        if n_tipo == "IEC-60255":
            p_mat = get_parametros_norma_dict(n_tipo, c_tipo)
            t_vals_51 = [tms * (p_mat["K"] / (((iv / p51_plot) ** p_mat["alpha"]) - 1)) for iv in i_vals_51]
        elif n_tipo in ["IEEE-ANSI","Personalizada"]:
            p_mat = get_parametros_norma_dict(n_tipo, c_tipo)
            t_vals_51 = []
            for iv in i_vals_51:
                m = iv / p51_plot
                if m > 20.0: 
                   m = 20.0
                t_vals_51.append(tms * ((p_mat["K"] / ((m ** p_mat["alpha"]) - 1)) + p_mat["L"]))
        else:
            if c_tipo == "I x T":
                t_vals_51 = [(60 / (iv / p51_plot)) * tms for iv in i_vals_51]
            else:
                t_vals_51 = [(540 / ((iv / p51_plot)**2)) * tms for iv in i_vals_51]

    # Nome limpo para a legenda (evita duplicações)
        if n_tipo == "Personalizada":
            nome_legenda_51 = "ANSI (51) - Curva Personalizada"
        elif n_tipo == "IEEE-ANSI":
            nome_legenda_51 = f"ANSI (51) - Curva {c_tipo}"
        else:
            nome_legenda_51 = f"ANSI (51) - Curva {c_tipo} ({n_tipo})"

        ax.plot(i_vals_51, t_vals_51, color="#ffb90f", linewidth=2, label=nome_legenda_51)

        i_vals_50 = np.logspace(np.log10(p50_plot), np.log10(max(p50_plot * 2.5, 500.0)), 100)
        t_vals_50 = [t_inst] * len(i_vals_50)
        ax.plot(i_vals_50, t_vals_50, color="#ff0f0f", linewidth=2, label="ANSI (50) - Unidade Instantânea")
        
        if len(t_vals_51) > 0:
            ax.plot([p50_plot, p50_plot], [t_vals_51[-1], t_inst], color="#ff0f0f", linewidth=2)

        if pontos_ativos:
            p_x_teo, p_y_teo, p_x_real, p_y_real = [], [], [], []
            for i, row in enumerate(pontos_ativos):
                iprim_v = st.session_state.get(f"iprim_{i}", row.get("iprim", 0.0))
                treal_v = st.session_state.get(f"treal_{i}", row.get("treal", 0.0))
                t_teo = calcular_teorico_geral(iprim_v, n_tipo, c_tipo, p_51, tms, p_50, t_inst)
                
                if not pd.isna(t_teo):
                    p_x_teo.append(iprim_v)
                    p_y_teo.append(t_teo)
                p_x_real.append(iprim_v)
                p_y_real.append(treal_v)
                
            if p_x_teo:
                ax.scatter(p_x_teo, p_y_teo, color="#0d6efd", marker="^", s=30, label="Pontos Teóricos", zorder=5)
            if p_x_real:
                ax.scatter(p_x_real, p_y_real, color="#28a745", marker="o", s=30, label="Pontos Reais", zorder=5)

        # Configuração rigorosa dos eixos idêntica à interface Web
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlim(0.1, 10000.0)  # Trava o eixo X igualzinho ao Plotly
        ax.set_ylim(0.01, 100.0)   # Trava o eixo Y igualzinho ao Plotly

        ax.set_xlabel("Corrente primária (A)", fontsize=7.5)
        ax.set_ylabel("Tempo (s)", fontsize=7.5)
        ax.set_title("Curva de Coordenação e Seletividade — Funções ANSI 50/51", fontsize=8.5, fontweight='bold')
        ax.grid(True, which="both", ls="--", alpha=0.5)
        ax.legend(fontsize=6.5, loc="upper right")
        ax.tick_params(labelsize=7)
        plt.tight_layout()

        img_buffer = io.BytesIO()
        fig_mpl.savefig(img_buffer, format='png', dpi=150)
        plt.close(fig_mpl)
        img_buffer.seek(0)

        story.append(Paragraph("3. Gráfico da Curva Característica", heading_style))
        story.append(Image(img_buffer, width=420, height=210))
        story.append(Spacer(1, 4))
    except Exception as e:
        story.append(Paragraph(f"<i>[Aviso: Não foi possível renderizar o gráfico no relatório: {e}]</i>", normal_style))

    story.append(Paragraph("4. Resumo e Conclusão do Ensaio", heading_style))
    total_pontos = len(pontos_ativos)
    
    summary_text = f"""
    <b>Total de Pontos Ensaiados:</b> {total_pontos}<br/>
    <b>Pontos Aprovados:</b> <font color="#22543d"><b>{aprovados}</b></font><br/>
    <b>Pontos Reprovados (Fora da Tolerância de ±{tol}%):</b> <font color="#742a2a"><b>{reprovados}</b></font><br/>
    <b>Pontos Fora da Curva Característica:</b> {fora_curva}<br/><br/>
    <b>Parecer Técnico:</b> {'O ensaio demonstra conformidade integral na seletividade e coordenação da proteção ANSI 50/51, com todos os pontos dentro dos limites regulamentares admissíveis.' if reprovados == 0 and total_pontos > 0 else 'Foram constatados desvios superiores à tolerância estipulada, sendo recomendada a revisão dos parâmetros de temporização ou aferição do sistema de ensaio.' if total_pontos > 0 else 'Nenhum ponto registrado para avaliação.'}
    """
    story.append(Paragraph(summary_text, normal_style))  
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Tratamento da ação disparada pelo menu "Relatórios" na navbar
if st.query_params.get("acao") == "gerar_relatorio":

    st.markdown("""
        <div style="background-color: #f8fafc; border: 1px solid #cbd5e0; padding: 25px; border-radius: 8px; margin: 20px 0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h2 style="color: #1a365d; margin-top: 0;">Relatório Técnico de Ensaio (PDF)</h2>
            <p style="color: #4a5568; font-size: 14px; margin-bottom: 20px;">O relatório consolida os parâmetros atuais da tela, a tabela completa de pontos de ensaio com status de conformidade, o gráfico da curva e o resumo executivo.</p>
        </div>
    """, unsafe_allow_html=True)
    
    pdf_data = gerar_pdf_relatorio()
    st.download_button(
        label="📥 Baixar Relatório Técnico em PDF",
        data=pdf_data,
        file_name=f"Relatorio_Tecnico_ANSI_5051_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ Retornar para a Tela Principal", use_container_width=True):
        st.query_params.clear()
        st.rerun()
    st.stop()

# ==========================================
# 4. PAINEL DE GESTÃO NATIVO DO STREAMLIT
# ==========================================

def registrar_salvamento():
    from zoneinfo import ZoneInfo

    if not st.session_state.nome_arquivo:
        st.session_state.nome_arquivo = "novo_ensaio_5051.json"

    st.session_state.ultimo_salvamento = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%d/%m/%Y às %H:%M:%S")

col_btn1, col_btn2, col_btn3, col_info = st.columns([1.5, 3.5, 1.5, 5.5])

with col_btn1:
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    st.link_button("📄 Novo Arquivo", url=f"?token={token_atual}&acao=novo", use_container_width=True)
with col_btn2:
    uploaded_file = st.file_uploader("Abrir", type=["json"], label_visibility="collapsed")

with col_btn3:
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    st.download_button(
        "💾 Salvar como...",
        data=json.dumps(obter_dados_atuais(), ensure_ascii=False, indent=4),
        file_name=st.session_state.nome_arquivo or "novo_ensaio_5051.json",
        mime="application/json",
        on_click=registrar_salvamento,
        use_container_width=True
    )

if uploaded_file is not None and st.session_state.get("arquivo_carregado_id") != uploaded_file.file_id:
    st.session_state.arquivo_carregado_id = uploaded_file.file_id
    try:
        data = json.load(uploaded_file)
        # Identificação do ensaio
        st.session_state.rele = data.get("rele", "")
        st.session_state.fabricante = data.get("fabricante", "")
        st.session_state.n_serie = data.get("n_serie", "")
        st.session_state.equipamento = data.get("equipamento", "")
        st.session_state.solicitante = data.get("solicitante", "")
        st.session_state.local = data.get("local", "")
        st.session_state.oa = data.get("oa", "")
        st.session_state.os_ensaio = data.get("os_ensaio", "")
        st.session_state.data_ensaio = data.get("data_ensaio", "")

        # Parâmetros do ensaio
        st.session_state.norma_tipo = data.get("norma_tipo", "IEC-60255")
        st.session_state.partida_51 = float(data.get("partida_51", 20.0))
        st.session_state.dial_tms = float(data.get("dial_tms", 0.100))
        st.session_state.tolerancia = float(data.get("tolerancia", 5.0))
        st.session_state.tempo_instantaneo = float(data.get("tempo_instantaneo", 0.025))
        
        rtc_carregado = data.get("rtc_str", "200 / 5")
        opcoes_rtc_validas = ["100 / 5", "150 / 5", "200 / 5", "300 / 5", "400 / 5", "600 / 5", "800 / 5"]
        if rtc_carregado in opcoes_rtc_validas:
            st.session_state.rtc_selectbox = rtc_carregado
        else:
            st.session_state.rtc_selectbox = "Personalizado (Digitar)"
            st.session_state.rtc_str_input = rtc_carregado
            
        st.session_state.criterio_50 = data.get("criterio_50", "Manual Direto")
        st.session_state.partida_50_manual = float(data.get("partida_50_manual", 160.0))
        
        st.session_state.nome_arquivo = uploaded_file.name
        st.session_state.caminho_absoluto = None 
        st.session_state.ultimo_salvamento = "Nunca salvo"
        
        norma_carregada = data.get("norma_tipo", "IEC-60255")
        curva_carregada = data.get("curva_tipo", "")
        if norma_carregada == "IEC-60255":
            st.session_state.curva_tipo_iec = curva_carregada
        elif norma_carregada == "IEEE-ANSI":
            st.session_state.curva_tipo_ieee = curva_carregada
        else:
            st.session_state.curva_tipo_outras = curva_carregada

        if "pontos_ensaio" in data:
            st.session_state.pontos_ensaio = data["pontos_ensaio"]
            # Atualiza explicitamente as chaves dos widgets individuais na sessão
            for idx, p in enumerate(data["pontos_ensaio"]):
                st.session_state[f"iprim_{idx}"] = float(p.get("iprim", 0.0))
                st.session_state[f"treal_{idx}"] = float(p.get("treal", 0.0))
            
        st.toast("✓ Arquivo carregado com sucesso!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o arquivo: {e}")

with col_info:
    arq_display = st.session_state.nome_arquivo if st.session_state.nome_arquivo else "Novo Arquivo (Sem Título)"
    st.markdown(
        f"""
        <div style="background-color: #f8fafc; padding: 9px 16px; border-radius: 6px; margin-top: 14px; margin-bottom: 25px; font-family: sans-serif; font-size: 13px; color: #334155; border-left: 4px solid #1a365d; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div>⏱️ <b>Último salvamento:</b> <span style="color: #059669; font-weight: 600;">{st.session_state.ultimo_salvamento}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )



#Identificação do relé de proteção

st.markdown("""
<div style="
    display: flex;
    align-items: center;
    gap: 10px;
    border-left: 5px solid #1a365d;
    padding: 7px 12px;
    margin: 12px 0 18px 0;
">
    <span style="
        font-size: 21px;
        font-weight: 700;
        color: white !important;
        letter-spacing: 0.2px;
    ">
        ⚡ Identificação do Ensaio
    </span>
</div>
""", unsafe_allow_html=True)

# Linha 1 — Identificação do relé
col1, col2, col3 = st.columns([1.5, 1.5, 1])

with col1:
    st.text_input(
        "Modelo do Relé",
        key="rele",
        placeholder="Ex.: URP6000-5/6001-5"
    )

with col2:
    st.text_input(
        "Fabricante",
        key="fabricante",
        placeholder="Ex.: Pextron"
    )

with col3:
    st.text_input(
        "Nº de Série",
        key="n_serie",
        placeholder="Nº de série"
    )

# Linha 2 — Identificação da instalação
col1, col2, col3 = st.columns([1, 1.5, 2])

with col1:
    st.text_input(
        "ID do Equipamento",
        key="equipamento",
        placeholder="Ex.: Bay 12"
    )

with col2:
    st.text_input(
        "Solicitante",
        key="solicitante",
        placeholder="Responsável / solicitante"
    )

with col3:
    st.text_input(
        "Local do Serviço",
        key="local",
        placeholder="Ex.: Subestação / Unidade / Painel"
    )

# Linha 3 — Dados da ordem
col1, col2, col3 = st.columns([1, 1, 0.6])

with col1:
    st.text_input(
        "O/A",
        key="oa",
        placeholder="Ordem de Ajuste"
    )

with col2:
    st.text_input(
        "O/S",
        key="os_ensaio",
        placeholder="Ordem de Serviço"
    )

with col3:
    st.text_input(
        "Data",
        key="data_ensaio",
        placeholder="dd/mm/aaaa"
    )


st.markdown("""
<style>

    /* ==============================
       FUNDO GERAL
       ============================== */
    .stApp {
        background-color: #F5F7FA;
    }

    /* ==============================
       TÍTULO PRINCIPAL
       ============================== */
    .titulo-principal {
        background: linear-gradient(135deg, #C8102E, #A5001C);
        color: white;
        padding: 16px 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 25px;
        font-weight: 700;
        border: 1px solid #8E0018;
        box-shadow: 0 3px 8px rgba(0,0,0,0.15);
        margin-bottom: 6px;
    }

    /* ==============================
       SUBTÍTULO
       ============================== */
    .subtitulo {
        color: #5F6B7A;
        text-align: center;
        font-size: 14px;
        margin-top: 4px;
        margin-bottom: 25px;
    }

    /* ==============================
       TÍTULO DAS SEÇÕES
       ============================== */
    .secao-titulo {
        color: #263238;
        font-size: 17px;
        font-weight: 700;
        padding-bottom: 8px;
        margin-bottom: 12px;
        border-bottom: 2px solid #D20A2E;
    }

    /* ==============================
       CARD DOS PARÂMETROS
       ============================== */
    .painel-config {
        background-color: white;
        padding: 20px 20px 10px 20px;
        border-radius: 12px;
        border: 1px solid #E1E5EA;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-top: 10px;
        margin-bottom: 20px;
    }

    /* ==============================
       LABELS DOS INPUTS
       ============================== */
    label {
        font-weight: 600 !important;
        color: #37474F !important;
    }

    /* ==============================
       SELECTBOX / INPUTS
       ============================== */
    div[data-baseweb="select"] > div {
        border-radius: 7px;
        border: 1px solid #D8DDE3;
    }

    /* ==============================
       ESPAÇAMENTO
       ============================== */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

</style>
""", unsafe_allow_html=True)

# ==========================================
# CABEÇALHO
# ==========================================

st.markdown(
    '<div class="titulo-principal">Ensaio de Curva ANSI (50/51)</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitulo">'
    'Análise de coordenação e seletividade de proteção de sobrecorrente '
    '(Temporizada e Instantânea)'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================
# 5. PAINEL DE CONFIGURAÇÕES FASE
# ==========================================
st.markdown("""
    <div class="secao-protecao_fase">
        <span class="icone">⚙</span>
        <span class="titulo">Configuração da Proteção 51</span>
        <span class="tag">Curva de Fase</span>
    </div>
    """, unsafe_allow_html=True)

col_norma, col1, col2, col3, col4, col5 = st.columns(6)

with col_norma:
  norma_tipo = st.selectbox(
      "NORMA",
      ["IEC-60255", "IEEE-ANSI", "Proteção de Máquinas Térmicas", "Personalizada"],
      key="norma_tipo",
  )

with col1:
  partida_51 = st.number_input(
      "PARTIDA 51 - fase (A PRIM.)", min_value=0.0, step=0.5, key="partida_51", placeholder="Digite um valor de corrente (A)"
  )

with col2:
  if norma_tipo == "IEC-60255":
    curva_tipo = st.selectbox(
        "CURVA",
        ["Normalmente inversa", "Muito inversa", "Extremamente inversa", "Inversa longa", "Inversa curta"],
        key="curva_tipo_iec"
    )
 
  elif norma_tipo == "IEEE-ANSI":
    curva_tipo = st.selectbox(
        "CURVA",
        ["Moderadamente inversa", "Muito inversa", "Extremamente inversa"],
        key="curva_tipo_ieee"
    )
     
  elif norma_tipo == "Proteção de Máquinas Térmicas":
    curva_tipo = st.selectbox(
        "CURVA",
        ["I x T", "I² x T"],
        key="curva_tipo_outras"
    )

  else:
    curva_tipo = st.selectbox(
            "CURVA", ["Personalizada"], key="curva_personalizada")
with col3:
  dial_tms = st.number_input(
      "DIAL ($T_{ms}$)", min_value=0.01, max_value=10.0, step=0.01, key="dial_tms"
  )

with col4:
  opcoes_rtc = ["100 / 5", "150 / 5", "200 / 5", "300 / 5", "400 / 5", "600 / 5", "800 / 5", "Personalizado (Digitar)"]
  rtc_selecionado = st.selectbox("RTC", opcoes_rtc, key="rtc_selectbox")
  
  if rtc_selecionado == "Personalizado (Digitar)":
    rtc_str = st.text_input("Digite o RTC:", key="rtc_str_input")
  else:
    rtc_str = rtc_selecionado

with col5:
  tolerancia = st.number_input(
      "TOLERÂNCIA (±%)", min_value=0.1, max_value=20.0, step=0.5, key="tolerancia"
  )

if norma_tipo == "Personalizada":
    st.markdown("---") # Linha sutil para separar visualmente
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        k_user_str = st.number_input("Digite a Constante K (IEEE):", min_value=0.01, max_value=100.0, value=0.0515, step=0.01, key="k_input_user_ieee")
    with sub_col2:
        alpha_user_str = st.number_input("Digite a Constante α (IEEE):", min_value=0.02, max_value=3.0, value=2.0, step=0.1, key="alpha_input_user_ieee")
    with sub_col3:
        L_user_str = st.number_input("Digite a Constante L (IEEE):", min_value=0.0, max_value=1.0, value=0.1217, step=0.1, key="l_input_user_ieee")

# ==========================================
# 6. CONFIGURAÇÃO DA UNIDADE INSTANTÂNEA (50)
# ==========================================
st.markdown("""
    <div class="secao-protecao_fase">
        <span class="icone">⚙</span>
        <span class="titulo">Configuração do Critério da Unidade Instantânea (50)</span>
        <span class="tag">Curva de Fase</span>
    </div>
    """, unsafe_allow_html=True)

c_inst1, c_inst2, c_inst3 = st.columns(3)

with c_inst1:
  criterio_50 = st.selectbox(
      "Critério de Ajuste (50)",
      ["Manual Direto", "Corrente Transitória / Inrush (Ip = k * Itran)", "Curto-Circuitos Bifásicos (Ip = k * Icc2F)"],
      key="criterio_50"
  )

with c_inst2:
  if "Transitória" in criterio_50:
    itran = st.number_input("Corrente Transitória / Inrush (A)", min_value=0.0, value=120.0, step=5.0)
    k_fator = st.number_input("Fator k (1,05 a 1,3)", min_value=1.0, max_value=2.0, value=1.2, step=0.05)
    partida_50 = itran * k_fator
    st.info(f"Partida 50 calculada: **{partida_50:.1f} A**")
  elif "Bifásico" in criterio_50:
    icc2f = st.number_input("Corrente de Curto Bifásico - Icc2F (A)", min_value=0.0, value=250.0, step=10.0)
    k_fator = st.number_input("Fator k (< 0,8)", min_value=0.1, max_value=1.0, value=0.75, step=0.05)
    partida_50 = icc2f * k_fator
    st.info(f"Partida 50 calculada: **{partida_50:.1f} A**")
  else:
    partida_50 = st.number_input("PARTIDA 50 MANUAL (A PRIM.)", min_value=0.0, step=5.0, key="partida_50_manual", placeholder="Digite um valor de corrente (A)")

with c_inst3:
  tempo_instantaneo = st.number_input("Tempo de Atuação 50 (s)", min_value=0.0, max_value=1.0, value=0.0, step=0.005, format="%.3f", key="tempo_instantaneo", placeholder="Digite um valor de tempo (s)")

# Parâmetros ativos atuais da tela
n_tipo_Ativo, c_tipo_Ativo, p_51_Ativo, tms_Ativo, tol_Ativo, t_inst_Ativo, crit_50_Ativo, p_50_man_Ativo, rtc_str_Ativo, rel_tc_Ativo = get_parametros_sessao()
p_50_Ativo = p_50_man_Ativo

# ==========================================
# 9. GERENCIAMENTO DOS PONTOS DE ENSAIO
# ==========================================
st.markdown(
    '<div class="secao-titulo">⚙ Painel de Controle dos Pontos de Ensaio</div>',
    unsafe_allow_html=True
)

with st.form("form_add_ponto", clear_on_submit=True):
  col_f1, col_f2, col_f3, col_f4 = st.columns([1, 2, 2, 1])
  with col_f1:
    novo_id = st.text_input("ID", value=f"I{len(st.session_state.pontos_ensaio)+1}")
  with col_f2:
    novo_iprim = st.number_input("Corrente Primária (A)", min_value=0.0, value=0.0, step=0.5, placeholder="Digite um valor de corrente (A)")
  with col_f3:
    novo_treal = st.number_input("Tempo Real (s)", min_value=0.0
                                 , value=0.0, step=0.001, format="%.3f", placeholder="Digite um valor de tempo (s)")
  with col_f4:
    st.markdown("<br>", unsafe_allow_html=True)
    btnAdd = st.form_submit_button("Adicionar Ponto")

  if btnAdd:
    st.session_state.pontos_ensaio.append({
        "id": novo_id,
        "iprim": novo_iprim,
        "treal": novo_treal,
    })
    st.rerun()

st.markdown(
    '<div class="secao-titulo">⚙ Relatório de Resultados e Erro Relativo</div>',
    unsafe_allow_html=True
)
st.markdown(
    "<normalize>Abaixo estão listados todos os pontos ativos do ensaio com cálculo dinâmico imediato. (🟥 - Teste Reprovado e 🟩 - Teste Aprovado)</normalize>",
    unsafe_allow_html=True,
)

h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 2, 2, 2, 2, 2, 1])
with h1: st.markdown("**n°**")
with h2: st.markdown("**Corrente Primária (A)**")
with h3: st.markdown("**Corrente Secundária (A)**")
with h4: st.markdown("**Tempo Teórico**")
with h5: st.markdown("**Tempo Real (s)**")
with h6: st.markdown("**Erro (%)**")
with h7: st.markdown("**Apagar**")

linhas_processadas = []
indices_para_remover = []

for idx, p in enumerate(st.session_state.pontos_ensaio):
  col_r1, col_r2, col_r3, col_r4, col_r5, col_r6, col_r7 = st.columns([1, 2, 2, 2, 2, 2, 1])

  with col_r1:
    st.text(p["id"])
  with col_r2:
    iprim_val = st.number_input(
        f"Primária {idx}",
        min_value=0.0,
        value=float(p["iprim"]),
        step=1.0,
        key=f"iprim_{idx}",
        label_visibility="collapsed",
    )
  with col_r3:
    i_sec = iprim_val / rel_tc_Ativo
    st.text(f"{i_sec:.2f} A")

  with col_r4:
    t_teorico = calcular_teorico_geral(iprim_val, n_tipo_Ativo, c_tipo_Ativo, p_51_Ativo, tms_Ativo, p_50_Ativo, t_inst_Ativo)
    if pd.isna(t_teorico) or t_teorico == 0:
      t_teorico_str = "Infinito"
    else:
      t_teorico_str = f"{t_teorico:.3f} s"
    st.text(t_teorico_str)

  with col_r5:
    treal_val = st.number_input(
        f"Real {idx}",
        min_value=0.0,
        value=float(p["treal"]),
        step=0.001,
        format="%.3f",
        key=f"treal_{idx}",
        label_visibility="collapsed",
    )

  if pd.isna(t_teorico) or t_teorico == 0:
    erro = 0.0
    status = "Fora da curva"
    cor_fundo = "#f8f9fa"
  else:
    erro = ((treal_val - t_teorico) / t_teorico) * 100
    status = "Aprovado" if abs(erro) <= tol_Ativo else "Reprovado"
    cor_fundo = "#22de8a" if abs(erro) <= tol_Ativo else "#eb2a3a"

  with col_r6:
    st.markdown(
        f"<div style='background-color: {cor_fundo}; padding: 5px; border-radius: 4px; text-align: center; font-weight: bold; color: #000;' title='Status: {status}'>{erro:+.1f}%</div>",
        unsafe_allow_html=True,
    )

  with col_r7:
    if st.button("🗑️", key=f"del_{idx}"):
      indices_para_remover.append(idx)

  st.session_state.pontos_ensaio[idx]["iprim"] = iprim_val
  st.session_state.pontos_ensaio[idx]["treal"] = treal_val

  linhas_processadas.append({
      "Ponto": p["id"],
      "Corrente Primária (A)": iprim_val,
      "Tempo Teórico Num": t_teorico,
      "Tempo Real (s)": treal_val,
  })

if indices_para_remover:
  for i in sorted(indices_para_remover, reverse=True):
    st.session_state.pontos_ensaio.pop(i)
  st.rerun()

df_res = pd.DataFrame(linhas_processadas)
st.markdown("---")

# ==========================================
# 10. CONSTRUÇÃO DO GRÁFICO PLOTLY NA TELA
# ==========================================
col_graf, col_info = st.columns([2, 1])

with col_graf:
  st.markdown(
    '<div class="secao-titulo"> 📉 Curva do Coordenograma 50/51</div>',
    unsafe_allow_html=True
)
  col_chk1, col_chk2 = st.columns(2)
  with col_chk1:
    mostrar_legenda_teo = st.checkbox("Exibir legenda nos pontos Teóricos", value=True)
  with col_chk2:
    mostrar_legenda_real = st.checkbox("Exibir legenda nos pontos Reais", value=True)

  fig = go.Figure()

  p51_plot = max(p_51_Ativo, 0.001)
  p50_plot = max(p_50_Ativo, 0.001)
  #limite_inf_plot = p51_plot * 1.1 if n_tipo_Ativo == "IEEE-ANSI" else p51_plot * 1.01
  limite_inf_plot = p51_plot * 1.001
  if p50_plot > limite_inf_plot:
    i_vals_51 = np.logspace(np.log10(limite_inf_plot), np.log10(p50_plot), 100)
  else:
    i_vals_51 = [limite_inf_plot]
  
  if n_tipo_Ativo == "IEC-60255":
    p = get_parametros_norma_dict(n_tipo_Ativo, c_tipo_Ativo)
    t_vals_51 = [tms_Ativo * (p["K"] / (((iv / p51_plot) ** p["alpha"]) - 1)) for iv in i_vals_51]
  elif n_tipo_Ativo in ["IEEE-ANSI","Personalizada"]:
    p = get_parametros_norma_dict(n_tipo_Ativo, c_tipo_Ativo)
    t_vals_51 = []
    for iv in i_vals_51:
        m = iv / p51_plot
        if m > 20.0: m = 20.0
        t_vals_51.append(tms_Ativo * ((p["K"] / ((m ** p["alpha"]) - 1)) + p["L"]))
  else:
    if c_tipo_Ativo == "I x T":
      t_vals_51 = [(60 / (iv / p51_plot)) * tms_Ativo for iv in i_vals_51]
    else:
      t_vals_51 = [(540 / ((iv / p51_plot)**2)) * tms_Ativo for iv in i_vals_51]

  fig.add_trace(go.Scatter(x=i_vals_51, y=t_vals_51, mode="lines", name=f"ANSI (51) - Curva {c_tipo_Ativo} ({n_tipo_Ativo})", line=dict(color="#ffb90f", width=3)))

  i_vals_50 = np.logspace(np.log10(p50_plot), np.log10(max(p50_plot * 2.5, 500.0)), 100)
  t_vals_50 = [t_inst_Ativo] * len(i_vals_50)

  fig.add_trace(go.Scatter(x=i_vals_50, y=t_vals_50, mode="lines", name="ANSI (50) - Unidade Instantânea", line=dict(color="#ff0f0f", width=3)))
  fig.add_trace(go.Scatter(x=[p50_plot, p50_plot], y=[t_vals_51[-1] if len(t_vals_51) > 0 else t_inst_Ativo, t_inst_Ativo], mode="lines", showlegend=False, line=dict(color="#ff0f0f", width=3)))

  if not df_res.empty:
    paleta_cores = ["#0d6efd", "#20c997", "#fd7e14", "#6f42c1", "#e83e8c", "#28a745", "#17a2b8"]
    p_x_teo, p_y_teo, p_ids_teo, cores_teo = [], [], [], []
    
    for i, row in df_res.iterrows():
      if not pd.isna(row["Tempo Teórico Num"]):
        p_x_teo.append(row["Corrente Primária (A)"])
        p_y_teo.append(row["Tempo Teórico Num"])
        p_ids_teo.append(row["Ponto"] + " (Teórico)")
        cores_teo.append(paleta_cores[i % len(paleta_cores)])

    if p_x_teo:
      modo_teo = "markers+text" if mostrar_legenda_teo else "markers"
      fig.add_trace(go.Scatter(x=p_x_teo, y=p_y_teo, mode=modo_teo, text=p_ids_teo, textposition="top right", marker=dict(size=12, symbol="triangle-up", color=cores_teo), name="Pontos Teóricos"))

    p_x_real = df_res["Corrente Primária (A)"].tolist()
    p_y_real = df_res["Tempo Real (s)"].tolist()
    p_ids_real = [p + " (Real)" for p in df_res["Ponto"].tolist()]
    cores_real = [paleta_cores[i % len(paleta_cores)] for i in range(len(df_res))]

    modo_real = "markers+text" if mostrar_legenda_real else "markers"
    fig.add_trace(go.Scatter(x=p_x_real, y=p_y_real, mode=modo_real, text=p_ids_real, textposition="bottom right", marker=dict(size=12, symbol="circle", color=cores_real), name="Pontos Reais"))

  fig.update_layout(title=dict(text="Curva de Coordenação e Seletividade — Funções ANSI 50/51", x=0.5, xanchor="center"), xaxis_title="Corrente primária (A)", yaxis_title="Tempo (s)", margin=dict(l=20, r=20, t=60, b=20), height=500, hovermode="closest")
  fig.update_xaxes(type="log", range=[-1, 4], showline=True, linewidth=1, linecolor="gray", mirror=True, showgrid=True, minor=dict(showgrid=True))
  fig.update_yaxes(type="log", range=[-2, 2], showline=True, linewidth=1, linecolor="gray", mirror=True, showgrid=True, minor=dict(showgrid=True))
  
  st.plotly_chart(fig, width='stretch')
   
  st.markdown(f"""
<div style="line-height: 1.3; margin-top: 8px;">
    <div><strong>Norma de referência:</strong> {n_tipo_Ativo}</div>
    <div><strong>Curva característica:</strong> {curva_tipo}</div>
    <div><strong>Multiplicador de tempo (<i>T</i><sub>ms</sub>):</strong> {dial_tms:.2f}</div>
    <div><strong>Relação RTC:</strong> {rtc_str_Ativo} ({rel_tc_Ativo:.0f}:1)</div> 
</div>
""", unsafe_allow_html=True)


# ==========================================
# PAINEL INFORMATIVO — ANSI 50
# ==========================================

with col_info:

    st.markdown("""
    <div class="secao-protecao_fase">
        <span class="icone">⚡</span>
        <span class="titulo">PROTEÇÃO INSTANTÂNEA</span>
        <span class="tag">ANSI 50</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
    f"""
    <div style="
        background-color: #FDE2E2;
        color: #8B0000;
        padding: 14px 16px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 10px;
    ">
        <strong>Corrente de pickup:</strong> {p_50_Ativo:.1f} A
        &nbsp; | &nbsp;
        <strong>Tempo de atuação estimado:</strong> {t_inst_Ativo:.3f} s
    </div>
    """,
    unsafe_allow_html=True
)

    st.latex(
        r"T_{50} = \frac{1,5 \text{ ciclos}}{60 \text{Hz}} = 0,025 \text{s}"
    )

    st.markdown(
        """
        <div style="
            font-size: 14px;
            line-height: 1.7;
            color: #455A64;
            text-align: justify;
        ">
        A unidade instantânea <b>ANSI 50</b> atua quando a corrente
        de falta ultrapassa o valor de pickup ajustado. O tempo de
        atuação é predominantemente determinado pelos tempos de
        processamento do relé e de abertura do disjuntor.
        <br><br>
        Para fins de representação da curva, adota-se como referência
        um tempo de <b>1,5 ciclos</b>, correspondente a
        <b>0,025 s em sistemas de 60 Hz</b>.
        <br><br>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_info:

    st.markdown("""
<div class="secao-protecao_fase">
    <span class="icone">⏱</span>
    <span class="titulo">PROTEÇÃO TEMPORIZADA</span>
    <span class="tag">ANSI 51</span>  
</div>
""", unsafe_allow_html=True)

    st.markdown(
    f"""
    <div style="
        background-color: #FDE2E2;
        color: #8B0000;
        padding: 14px 16px;
        border-radius: 8px;
        margin-top: 8px;
        margin-bottom: 10px;
        line-height: 1.3;
    ">
        <div><strong>Norma de referência:</strong> {n_tipo_Ativo}</div>
        <div><strong>Curva característica:</strong> {curva_tipo}</div>
        <div><strong>Multiplicador de tempo (<i>T</i><sub>ms</sub>):</strong> {dial_tms:.2f}</div>
    </div>
    """,
    unsafe_allow_html=True
)
    
    if n_tipo_Ativo == "IEC-60255":
      st.latex(r"T_{51} = T_{ms} \times \frac{K}{\left(\frac{I_{ma}}{I_{ac}}\right)^\alpha - 1}")
      st.markdown("Onde $T_{ms}$ é o dial de tempo (Multiplicador de Tempo), $I_{ma}$ é a sobrecorrente máxima admitida e $I_{ac}$ é a corrente de partida (acionamento).") 
      st.markdown("#### Valores Teóricos da Norma IEC")
      tabela_coefs = pd.DataFrame({
          "Tipo de Curva": [
              "Normalmente inversa",
              "Muito inversa",
              "Extremamente inversa",
              "Inversa longa",
              "Inversa curta"
          ],
          "K": ["0,14", "13,5", "80", "120", "0,05"],
          "α": ["0,02", "1", "2", "1", "0,04"]
      })
      st.table(tabela_coefs)
  
    elif n_tipo_Ativo == "IEEE-ANSI":
      st.latex(r"T_{51} = T_{ms} \cdot \left( \frac{K}{\left(\frac{I_{ma}}{I_{ac}}\right)^\alpha - 1} + L \right)")
      st.markdown("""
      **Legenda das Grandezas:**
      - **T** – tempo de atuação da proteção
      - **$I_{ma}$** – sobrecorrente máxima admitida (corrente medida no primário)
      - **$I_{ac}$** – corrente de acionamento (partida 51)
      - **$T_{ms}$** – multiplicador de tempo (dial)
      - **K, α e L** – constantes da curva IEEE-ANSI
      """)
      st.warning("⚠️ **Limites de Operação IEEE-ANSI:**\n\nA norma estabelece limites onde a curva atua rigorosamente dentro da faixa de sobrecorrente: \n$1,1 \\times I_{ac} < I_{ma} < 20 \\times I_{ac}$")
  
    else:
      st.markdown("<small>Equações para relés digitais portadores de curvas destinadas à proteção de máquinas térmicas (motores, geradores e transformadores):</small>", unsafe_allow_html=True)
      if curva_tipo == "I x T":
        st.latex(r"T_{51} = \frac{60}{\left( \frac{I_{ma}}{I_s} \right)} \times T_{ms}")
      else:
        st.latex(r"T_{51} = \frac{540}{\left( \frac{I_{ma}}{I_s} \right)^2} \times T_{ms}")
