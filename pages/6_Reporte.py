import streamlit as st
import json
import base64
import urllib.parse
from streamlit_option_menu import option_menu
from bs4 import BeautifulSoup
from streamlit_js_eval import streamlit_js_eval

from modulos._detalle_building  import main as _detalle_building
from modulos._detalle_unidad  import main as _detalle_unidad
from modulos._estudio_mercado  import main as _estudio_mercado
from modulos._cabida_lote  import main as _cabida_lote
from modulos._propietarios  import main as _propietarios
from modulos._favoritos_busqueda_general  import main as _busqueda_general_favoritos
from modulos._favoritos_busqueda_lotes import main as _busqueda_lotes_favoritos
from modulos._combinacion_lotes import main as _combinacion_lotes
from modulos._ficha_report  import main as _ficha_report
from modulos._busqueda_general import main as _busqueda_general

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
               'change':False,
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
    # Ejecutable
    collogo1, collogo2, collogo3 = st.columns([0.66,0.24,0.1])
    if params is None:
        screensize = getscreensize()
        _busqueda_general(screensize=screensize)
        
    # Caso: Parametros en la url
    elif isinstance(params,str) and params!='':
        
        params = f"token={params}"
        params = urllib.parse.parse_qs(params)
        params = params['token'][0]
        params = base64.urlsafe_b64decode(params.encode())
        params = json.loads(params.decode())

        grupo     = params['grupo'] if 'grupo' in params else None
        tipo      = params['type'] if 'type' in params else None
        barmanpre = params['barmanpre'] if 'barmanpre' in params else None
        inputvar  = params['inputvar'] if 'inputvar' in params else {}
        chip_referencia = params['chip_referencia'] if 'chip_referencia' in params and isinstance(params['chip_referencia'],str) and params['chip_referencia']!=''  else None
        if st.session_state.token is None: 
            st.session_state.token = params['token'] if 'token' in params and isinstance(params['token'],str) and params['token']!='' else None
        
        if st.session_state.change is False and 'favorito' in params and params['favorito']:
            st.session_state.favorito = True
        if 'id_consulta' in params and isinstance(params['id_consulta'],int):
            st.session_state.id_consulta = params['id_consulta']
                    
        if st.session_state.access:

            #-----------------------------------------------------------------#
            # Busqueda particular por barmanpre/grupo 
            #-----------------------------------------------------------------#
            if 'predio' in tipo:
                
                # ["Descripción General", "Análisis de unidad","Estudio de mercado", "Propietarios","Reporte PDF","Nueva búsqueda"]
                
                selectedmod = option_menu(None, ["Descripción General", "Análisis de unidad","Estudio de mercado", "Simulación de desarrollo del lote","Propietarios","Nueva búsqueda"], 
                    default_index=0, orientation="horizontal",icons=['hexagon','house','house','magic','magic'], 
                    styles={
                        "nav-link-selected": {"background-color": "#A16CFF"},
                    })
                    
                if "Descripción General" in selectedmod:
                    with st.spinner('Buscando información'): 
                        if st.session_state.id_consulta is None:
                            _,st.session_state.id_consulta = savesearch(st.session_state.token, barmanpre, '_detalle_building', None)
                        else:
                            savesearch(st.session_state.token, barmanpre, '_detalle_building', None, id_consulta_defaul=st.session_state.id_consulta)                            
                        _detalle_building(grupo=grupo)

                elif "Análisis de unidad" in selectedmod:  
                    with st.spinner('Buscando información'):
                        savesearch(st.session_state.token, barmanpre, '_analisis_unidad', None, id_consulta_defaul=st.session_state.id_consulta)
                        _detalle_unidad(grupo=grupo, chip_referencia=chip_referencia, barmanpre=barmanpre)

                    
                elif "Estudio de mercado" in selectedmod:
                    with st.spinner('Buscando información'):
                        savesearch(st.session_state.token, barmanpre, '_estudio_mercado', None, id_consulta_defaul=st.session_state.id_consulta)
                        _estudio_mercado(grupo=grupo)

                elif "Simulación de desarrollo del lote" in selectedmod:  
                    with st.spinner('Buscando información'):
                        savesearch(st.session_state.token, barmanpre, '_cabida_lote', None, id_consulta_defaul=st.session_state.id_consulta)
                        _cabida_lote(grupo=grupo)

                elif "Propietarios" in selectedmod:  
                    with st.spinner('Buscando información'):
                        savesearch(st.session_state.token, barmanpre, '_propietarios', None, id_consulta_defaul=st.session_state.id_consulta)
                        _propietarios(grupo=grupo,barmanpre=barmanpre)
                        
                elif "Nueva búsqueda" in selectedmod:
                    
                    col1,col2,col3 = st.columns([0.3,0.4,0.3])
                    style_button_dir = """
                    <style>
                    .custom-button-urbex {
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #A16CFF;
                        color: #ffffff; 
                        font-weight: bold;
                        text-decoration: none;
                        border-radius: 10px;
                        width: 100%;
                        border: none;
                        cursor: pointer;
                        text-align: center;
                        letter-spacing: 1px;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        margin-bottom: 20px;
                    }
                    .custom-button-urbex:visited {
                        color: #ffffff;
                    }
                    </style>
                    """
                    nombre = '¿Seguro quiere salir de está página?'
                    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://localhost:8501/Busqueda" class="custom-button-urbex" target="_self">{nombre}</a></body></html>"""
                    html = BeautifulSoup(html, 'html.parser')
                    with col2:
                        st.markdown(html, unsafe_allow_html=True)


            #-----------------------------------------------------------------#
            # Busuqeda general
            #-----------------------------------------------------------------#
            if 'busqueda_general' in tipo:
                _busqueda_general_favoritos(inputvar=inputvar)

            #-----------------------------------------------------------------#
            # Busuqeda de lotes
            #-----------------------------------------------------------------#
            if 'busqueda_lotes' in tipo:
                _busqueda_lotes_favoritos(inputvar=inputvar)

            #-----------------------------------------------------------------#
            # Busuqeda de lotes
            #-----------------------------------------------------------------#
            if 'combinacion_lote' in tipo:
                _combinacion_lotes(grupo=grupo)

            #-----------------------------------------------------------------#
            # Busuqeda de lotes
            #-----------------------------------------------------------------#
            if 'ficha' in tipo:
                _ficha_report(params['code'])

     
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
                            st.session_state.change   = True
                            st.rerun()
            if st.session_state.favorito:
                on = st.toggle('Guardado',True)
                if on is False:
                    with st.spinner('Removiendo'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,0):
                            st.session_state.favorito = False
                            st.session_state.change   = True
                            st.rerun()

    #-------------------------------------------------------------------------#
def getscreensize():
    try: return int(streamlit_js_eval(js_expressions='screen.width', key = 'SCR'))
    except: return 1920
    
if __name__ == "__main__":
    main()