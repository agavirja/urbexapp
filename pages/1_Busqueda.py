import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from modulos._busqueda_general import main as _busqueda_general
from functions._principal_login import main as login
from functions._principal_logout import main as logout

from display.style_white import style 

try: st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")
except: pass

def main():
    
    style()

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
        'token': None,
        'access': False
    }
    
    for key, value in formato.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    #-------------------------------------------------------------------------#
    # Login
    if not st.session_state.access:
        with st.spinner('Iniciando sesión...'):
            login()
    #else:
    #    logout()
        
    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = getscreensize()

    #-------------------------------------------------------------------------#
    # Ejecutable
    if st.session_state.access:
        
        collogo1, collogo2, collogo3 = st.columns([0.65,0.25,0.1])

        with st.spinner('Buscando informacion'):
            _busqueda_general(screensize=screensize)

        with collogo2:
            st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png', width=200)
        

def getscreensize():
    try: return int(streamlit_js_eval(js_expressions='screen.width', key = 'SCR'))
    except: return 1920

if __name__ == "__main__":
    main()
