import streamlit as st
import json
import base64
import urllib.parse
from streamlit_option_menu import option_menu
from streamlit_js_eval import streamlit_js_eval

from modulos._busqueda_lotes  import main as _busqueda_lotes
from modulos._combinacion_lotes import main as _combinacion_lotes

from functions._principal_login import main as login

from data.tracking import savesearch,update_save_status

from display.style_white import style 

try: st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")
except: pass

    
def main():
    
    style()

    #-------------------------------------------------------------------------#
    # Variables
    formato = {
               'token':None,
               'access':False,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
     
    params = None
    if 'token' in st.query_params: 
        params = st.query_params['token']
    
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
    collogo1, collogo2, collogo3 = st.columns([6,1,1])
    if params is None:
        if st.session_state.access:
            with st.spinner('Buscando información'):        
                _busqueda_lotes(screensize=screensize)

    elif isinstance(params,str) and params!='':
        params = f"token={params}"
        params = urllib.parse.parse_qs(params)
        params = params['token'][0]
        params = base64.urlsafe_b64decode(params.encode())
        params = json.loads(params.decode())
        
        grupo    = params['grupo'] if 'grupo' in params else None
        tipo     = params['type'] if 'type' in params else None
        barmanpe = params['barmanpre'] if 'barmanpre' in params else None
        if st.session_state.token is None: 
            st.session_state.token = params['token'] if 'token' in params and isinstance(params['token'],str) and params['token']!='' else None
        
        if st.session_state.access:
            
            #-----------------------------------------------------------------#
            # Busqueda particular por barmanpre/grupo 
            #-----------------------------------------------------------------#
            if 'combinacion_lote' in tipo:
                with st.spinner('Buscando información'): 
                    _,st.session_state.id_consulta = savesearch(st.session_state.token, barmanpe, '_combinacion_lote', None)
                    _combinacion_lotes(grupo=grupo)
                
    with collogo2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png', width=200)
        
    #-------------------------------------------------------------------------#
    # Guardar la consulta 
    if isinstance(st.session_state.token,str) and st.session_state.token!='' and isinstance(st.session_state.id_consulta,int):
        with collogo2:
            if st.session_state.favorito is False:
                on = st.toggle('Guardar en favoritos',False)
                if on:
                    with st.spinner('Guardando'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,1):
                            st.session_state.favorito = True
                            st.rerun()
            if st.session_state.favorito:
                on = st.toggle('Guardado',True)
                if on is False:
                    with st.spinner('Removiendo'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,0):
                            st.session_state.favorito = False
                            st.rerun()

    #-------------------------------------------------------------------------#

def getscreensize():
    try: return int(streamlit_js_eval(js_expressions='screen.width', key = 'SCR'))
    except: return 1920
    
if __name__ == "__main__":
    main()
