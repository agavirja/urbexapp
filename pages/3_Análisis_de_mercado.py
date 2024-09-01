import streamlit as st
import warnings
from streamlit_option_menu import option_menu

from modulos._analisis_market import main as _analisis_market
from modulos._listings  import main as _listings
from modulos._heatmap_default  import main as _heatmap_default
from modulos._precios_referencia  import main as _precios_referencia
from modulos._proyectos_nuevos  import main as _proyectos_nuevos
from modulos._localizador_marcas import main as _localizador_marcas
from modulos._analisis_normativa_urbana import main as _analisis_normativa_urbana

from data.getuser import getuser
from display.style_white import style 

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

formato = {
           'access':False,
           'token':'',
           'type':None,
           'code':None,
           'modulo':None,
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']
if 'type' in st.query_params: 
    st.session_state.type = st.query_params['type']
if 'code' in st.query_params: 
    st.session_state.code = st.query_params['code']
if 'modulo' in st.query_params: 
    st.session_state.modulo = st.query_params['modulo']

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
    if isinstance(st.session_state.modulo,str) and 'proyectos' in st.session_state.modulo:
        default_index = 5
   
    selectedmod   = option_menu(None, ["Análisis del mercado","Análisis de marcas","Agregador de oferta","Mapa de transacciones", "Precios de referencia", "Proyectos nuevos","Normativa Urbana"], 
        default_index=default_index, orientation="horizontal",icons=['graph-up','shield-check','kanban','globe2','cash-coin','buildings','globe2'], 
        styles={
        "nav-link-selected": {"background-color": "#A16CFF"}, 
        })

    if "Análisis del mercado" in selectedmod:
        _analisis_market()
        
    elif "Análisis de marcas" in selectedmod:
        _localizador_marcas()
    
    elif "Agregador de oferta" in selectedmod:
        _listings()
  
    elif "Mapa de transacciones" in selectedmod:
        _heatmap_default()
        
    elif "Precios de referencia" in selectedmod:
        _precios_referencia()
        
    elif "Proyectos nuevos" in selectedmod:
        _proyectos_nuevos(tipo=st.session_state.type,code=st.session_state.code)
        
    elif "Normativa Urbana" in selectedmod:
        _analisis_normativa_urbana()
        
else:
    from modulos.signup_login import main as signup_login
    signup_login()
