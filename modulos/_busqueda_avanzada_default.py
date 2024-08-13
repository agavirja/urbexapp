import streamlit as st
import warnings
from streamlit_option_menu import option_menu

from modulos._busqueda_avanzada_principal import main as _busqueda_avanzada_principal
from modulos._localizador_propietarios  import main as _localizador_propietarios

from data.getuser import getuser
from display.style_white import style 

warnings.filterwarnings("ignore")

formato = {
           'access':False,
           'token':'',
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'token' in st.query_params: 
    st.session_state.token = st.query_params['token']
 
if st.session_state.access is False and isinstance(st.session_state.token, str) and st.session_state.token!='':
    st.session_state.access = getuser(st.session_state.token)

def main():
    
    style()
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Header (https://icons.getbootstrap.com/)
    default_index = 0
    selectedmod   = option_menu(None, ["Búsqueda general de predios","Búsqueda por Id del propietario"], 
        default_index=default_index, orientation="horizontal",icons=['hexagon','person-circle'], 
        styles={
        "nav-link-selected": {"background-color": "#A16CFF"}, 
        })

    if "Búsqueda general de predios" in selectedmod:
        _busqueda_avanzada_principal()
        
    elif "Búsqueda por Id del propietario" in selectedmod:
        _localizador_propietarios()
