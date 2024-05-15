import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from modulos._estudio_mercado_default  import main as _estudio_mercado_default

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

formato = {
           'code':None,
           'type':None,
           'vartype':None,
           'access':False,
           'token':'',
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'code' in st.query_params: 
    st.session_state.code = st.query_params['code']
if 'type' in st.query_params: 
    st.session_state.type = st.query_params['type']
if 'vartype' in st.query_params: 
    st.session_state.vartype = st.query_params['vartype']
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']

@st.cache_data(show_spinner=False)
def getuser(token):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata"]
    schema   = 'urbex'
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df       = pd.read_sql_query(f"""SELECT *  FROM {schema}.users WHERE token='{token}';""" , engine)
    engine.dispose()
    if not df.empty: return True
    else: return False
    
if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

if st.session_state.access:
    _estudio_mercado_default()
else:
    from modulos.signup_login import main as signup_login
    signup_login()
    #st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')