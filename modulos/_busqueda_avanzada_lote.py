import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from streamlit_js_eval import streamlit_js_eval
from streamlit_option_menu import option_menu

from modulos._descripcion_combinacionlote import main as _descripcion_combinacionlote
from modulos._estudio_mercado_parcial import main as _estudio_mercado_parcial
from modulos._analisis_unidad import main as _analisis_unidad
from modulos._propietarios import main as _propietarios

def main(code=None):

    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #FAFAFA;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #fff;
            }}
        
        div[data-testid="stToolbar"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stDecoration"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stStatusWidget"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
    
        #MainMenu {{
        visibility: hidden; 
        height: 0%;
        }}
        header {{
            visibility: hidden; 
            height: 0%;
            }}
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        div[data-testid="stSpinner"] {{
            color: #000000;
            }}
        
        a[href="#responsive-table"] {{
            visibility: hidden; 
            height: 0%;
            }}
        
        a[href^="#"] {{
            /* Estilos para todos los elementos <a> con href que comienza con "#" */
            visibility: hidden; 
            height: 0%;
            overflow-y: hidden;
        }}

        div[class="table-scroll"] {{
            background-color: #a6c53b;
            visibility: hidden;
            overflow-x: hidden;
            }}
            
        </style>
        """,
        unsafe_allow_html=True
    )
    #html = gethtml()
    #st.components.v1.html(html,height=450)
    
    default_index = 0
    #-------------------------------------------------------------------------#
    # Header
    selectedmod = option_menu(None, ["Lotes", "Estudio de mercado", "Propietarios"], 
        default_index=default_index, orientation="horizontal",icons=['hexagon','house','magic','person'], 
        styles={
            "nav-link-selected": {"background-color": "#6EA4EE"},
        })
        
    precuso,latitud,longitud = getlatlngPrecuso(code)
    
    if "Lotes" in selectedmod:
        _descripcion_combinacionlote(code)
    
    elif "Estudio de mercado" in selectedmod:
        _estudio_mercado_parcial(code=None,latitud=latitud,longitud=longitud,precuso=precuso) # barmanpre
  
    elif "Propietarios" in selectedmod:
        _propietarios(chip=None,barmanpre=None,vartype=None)
    
@st.cache_data(show_spinner=False)
def getlatlngPrecuso(code):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    precuso,latitud,longitud = [None]*3
    try: 
        lista       = str(code).split('|')
        query       = "','".join(lista)
        query       = f" id IN ('{query}')"   
        datapredios = pd.read_sql_query(f"SELECT barmanpre FROM  bigdata.bogota_consolidacion_lotes_2000 WHERE {query}" , engine)
    
        if not datapredios.empty:
            barmanprelist = datapredios['barmanpre'].str.split('|')
            barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
            barmanprelist = list(set(barmanprelist))
    
            query = "','".join(barmanprelist)
            query = f" barmanpre IN ('{query}')"   
            dataprecuso = pd.read_sql_query(f"SELECT precuso,latitud,longitud FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)

            if not dataprecuso.empty:
                precuso  = list(dataprecuso['precuso'].unique())
                latitud  = dataprecuso['latitud'].mean()
                longitud = dataprecuso['longitud'].mean()
    except: pass
    return precuso,latitud,longitud

if __name__ == "__main__":
    main()
