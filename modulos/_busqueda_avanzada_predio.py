import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from modulos._busqueda_avanzada_descripcion_lote import main as _descripcion_lote
from modulos._busqueda_avanzada_analisis_unidad import main as _analisis_unidad
from modulos._busqueda_avanzada_pdfreport import main as _busqueda_avanzada_pdfreport
from modulos._propietarios import main as _propietarios
from modulos._estudio_mercado_parcial import main as _estudio_mercado_parcial

def main(code=None,vartype=None):
    
    initialformat = {
        'token':'',
        }
    for key,value in initialformat.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    default_index = 0
    barmanpre     = None
    chip          = None
    if 'barmanpre' in vartype: 
        default_index = 0
        barmanpre     = code
    elif 'chip' in vartype: 
        default_index = 1
        chip          = code
        
    if barmanpre is None and isinstance(chip, str):
        barmanpre = chip2barmanpre(chip)
        
    #-------------------------------------------------------------------------#
    # Header (https://icons.getbootstrap.com/)
    selectedmod = option_menu(None, ["Descripción General", "Análisis de unidad","Estudio de mercado", "Propietarios","Reporte PDF","Nueva búsqueda"], 
        default_index=default_index, orientation="horizontal",icons=['hexagon','house','magic','person','file-earmark-pdf','arrow-counterclockwise'], 
        styles={
            "nav-link-selected": {"background-color": "#A16CFF"},
        })
        
    if "Descripción General" in selectedmod:
        _descripcion_lote(code=barmanpre)
    
    elif "Estudio de mercado" in selectedmod:
        _estudio_mercado_parcial(code=barmanpre)
  
    elif "Análisis de unidad" in selectedmod:
        _analisis_unidad(chip=chip,barmanpre=barmanpre,vartype=vartype)
        
    elif "Propietarios" in selectedmod:
        _propietarios(chip=chip,barmanpre=barmanpre,vartype=vartype)
        
    elif "Reporte PDF" in selectedmod:
        _busqueda_avanzada_pdfreport(chip=chip,barmanpre=barmanpre)
        
    elif "Nueva búsqueda" in selectedmod:
        
        col1,col2,col3 = st.columns([0.3,0.4,0.3])
        style_button_dir = """
        <style>
        .custom-button {
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
        .custom-button:visited {
            color: #ffffff;
        }
        </style>
        """
        nombre = '¿Seguro quiere salir de está página?'
        html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
        html = BeautifulSoup(html, 'html.parser')
        with col2:
            st.markdown(html, unsafe_allow_html=True)
                
@st.cache_data(show_spinner=False)
def chip2barmanpre(chip):
    result = None
    if chip is not None and chip!="" and isinstance(chip,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"prechip='{chip}'"
        data     = pd.read_sql_query(f"SELECT barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            result = data['barmanpre'].iloc[0]
        engine.dispose()
    return result

if __name__ == "__main__":
    main()
