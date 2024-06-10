import streamlit as st
from streamlit_cookies_controller import CookieController

from modulos._busqueda_avanzada_default  import main as _busqueda_avanzada_default
from modulos._busqueda_avanzada_predio   import main as _busqueda_avanzada_predio
from modulos._busqueda_avanzada_lote     import main as _busqueda_avanzada_lote

from data.getuser import getuser
from display.style_white import style 

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

style()

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

with st.spinner('Loading'):
    controller = CookieController()
    cookies    = controller.getAll()
    try:    token = controller.get('token')
    except: token = "" 
    if isinstance(st.session_state.token,str) and st.session_state.token=="" and isinstance(token,str) and token!="":
        st.session_state.token = token

if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

if st.session_state.access:
    if st.session_state.code is None or st.session_state.type is None:
        _busqueda_avanzada_default()
    elif isinstance(st.session_state.code, str) and isinstance(st.session_state.type, str) and 'predio' in st.session_state.type.lower():
        _busqueda_avanzada_predio(st.session_state.code,st.session_state.vartype)
    elif isinstance(st.session_state.code, str) and isinstance(st.session_state.type, str) and 'lote' in st.session_state.type.lower():
        _busqueda_avanzada_lote(st.session_state.code)
else:
    from modulos.signup_login import main as signup_login
    signup_login()
