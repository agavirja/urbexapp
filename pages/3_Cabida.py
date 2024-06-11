import streamlit as st

from modulos._cabida_lotes_default  import main as _cabida_lotes_default
from modulos._cabida_lotes  import main as _cabida_lotes

from data.getuser import getuser
from display.style_white import style 

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

style()

formato = {
           'access':False,
           'code':None,
           'token':'',
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'code' in st.query_params: 
    st.session_state.code = st.query_params['code']
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']

if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

if st.session_state.access:
    if st.session_state.code is None:
        _cabida_lotes_default()
    elif isinstance(st.session_state.code, str):
        _cabida_lotes(st.session_state.code)

    #barmanpre  = '008412025008' # o '008412025008|008412025008|008412025008'
    #_cabida_lotes(barmanpre)

else:
    from modulos.signup_login import main as signup_login
    signup_login()
