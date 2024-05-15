import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from modulos._precios_referencia  import main as _precios_referencia

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

formato = {
           'access':False,
           'token':'',
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
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
    _precios_referencia()
else:
    from modulos.signup_login import main as signup_login
    signup_login()
    #st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
