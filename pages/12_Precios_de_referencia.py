import streamlit as st
from streamlit_cookies_controller import CookieController

from modulos._precios_referencia  import main as _precios_referencia

from data.getuser import getuser
from display.style_white import style 

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

style()

formato = {
           'access':False,
           'token':'',
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']

with st.spinner('Loading'):
    controller = CookieController()
    cookies    = controller.getAll()
    try:    token = controller.get('token')
    except: token = "" 
    if isinstance(st.session_state.token,str) and st.session_state.token=="" and isinstance(token,str) and token!="":
        st.session_state.token = token
        
#if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
#    st.session_state.access = getuser(st.session_state.token)

#if st.session_state.access:
#    _precios_referencia()
#else:
#    from modulos.signup_login import main as signup_login
#    signup_login()

from display.html_construccion import html as construccion
st.components.v1.html(construccion(), height=400)