import streamlit as st
import warnings

from modulos._lotes_desarrollo_busqueda_lotes import main as _lotes_desarrollo_busqueda_lotes

from data.getuser import getuser
from display.style_white import style 

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

formato = {
           'access':False,
           'token':'',
           'code':None,
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']
if 'code' in st.query_params: 
    st.session_state.code = st.query_params['code']
 
if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

if st.session_state.access:
    
    style()
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)

    _lotes_desarrollo_busqueda_lotes(code=st.session_state.code)
    
else:
    from modulos.signup_login import main as signup_login
    signup_login()
