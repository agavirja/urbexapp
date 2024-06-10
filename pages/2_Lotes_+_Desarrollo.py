import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine
from streamlit_cookies_controller import CookieController

from modulos._lotes_desarrollo_busqueda_lotes import main as _lotes_desarrollo_busqueda_lotes
from modulos._lotes_desarrollo_manzanas import main as _lotes_desarrollo_manzanas
from modulos._lotes_desarrollo_consolidacion import main as _lotes_desarrollo_consolidacion

from data.getuser import getuser
from display.style_white import style 

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

with st.spinner('Loading'):
    controller = CookieController()
    cookies    = controller.getAll()
    try:    token = controller.get('token')
    except: token = "" 
    if isinstance(st.session_state.token,str) and st.session_state.token=="" and isinstance(token,str) and token!="":
        st.session_state.token  = token
        
if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

if st.session_state.access:
    
    style()
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Header (https://icons.getbootstrap.com/)
    default_index = 0
    selectedmod   = option_menu(None, ["Búsqueda avanzada de lotes", "Búsquedas de manzanas","Consolidación de lotes", "Mapa de normativa urbana"], 
        default_index=default_index, orientation="horizontal",icons=['hexagon','pip','union','map'], 
        styles={
        "nav-link-selected": {"background-color": "#A16CFF"}, 
        })

    if "Búsqueda avanzada de lotes" in selectedmod:
        _lotes_desarrollo_busqueda_lotes()
    
    elif "Búsquedas de manzanas" in selectedmod:
        _lotes_desarrollo_manzanas()
  
    elif "Consolidación de lotes" in selectedmod:
        _lotes_desarrollo_consolidacion()
        
    elif "Mapa de normativa urbana" in selectedmod:
        st.write("Mapa de normativa urbana")
        
else:
    from modulos.signup_login import main as signup_login
    signup_login()
