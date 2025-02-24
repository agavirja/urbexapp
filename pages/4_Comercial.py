import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_js_eval import streamlit_js_eval

from modulos._comercial_generador_leads import main as _comercial_leads
from modulos._comercial_propiedades_by_id import main as _comercial_propiedades_by_id
from modulos._comercial_propiedades_by_id_masivo import main as _comercial_propiedades_by_id_masivo

from functions._principal_login import main as login
from data.tracking import update_save_status

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
        
        collogo1, collogo2, collogo3 = st.columns([6,1,1])

        with st.spinner('Buscando información'):
            selectedmod = option_menu(None, ["Generador de Leads","Propiedades por ID","Prefactibilidad"], 
                default_index=0, orientation="horizontal",icons=['hexagon','house','house','magic','magic','magic'], 
                styles={
            "container": {"padding": "0!important", "background-color": "#f9f9f9"},
            "icon": {"color": "#A16CFF", "font-size": "18px"}, 
            "nav-link": {
                "font-size": "14px",
                "text-align": "center",
                "margin": "0 10px",  # Espacio entre botones
                "padding": "8px 12px",
                "color": "#333",
                "border-radius": "5px",
                "transition": "background-color 0.3s",
            },
            "nav-link-selected": {"background-color": "#A16CFF", "color": "white"},
            })
                
            if "Generador de Leads" in selectedmod:
                _comercial_leads(screensize=screensize)
    
            elif "Propiedades por ID" in selectedmod:  
                _comercial_propiedades_by_id()
                
            elif "Prefactibilidad" in selectedmod:  
                _comercial_propiedades_by_id_masivo()

            
                                
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
