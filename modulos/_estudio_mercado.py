import streamlit as st
import shapely.wkt as wkt
import pandas as pd
import json
from datetime import datetime

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions._principal_getdatanalisis import main as getradio   #_principal_getdataradio
from functions._principal_getpdf import main as _principal_getpdf

from data._principal_caracteristicas import datacaracteristicas

from display._principal_estudio_mercado import main as generar_html

def main(grupo=None):
    
    style_page()
    
    colb1,colb2,colb3 = st.columns([6,1,1],vertical_alignment="center")
    col1, col2        = st.columns([0.15,0.85])
    with col1:
        metros    = st.selectbox('Metros',options=[100,200,300,400,500],index=4)
        datauso   = usosuelo_class()
        lista     = list(sorted(datauso['clasificacion'].unique()))
        seleccion = st.multiselect('Tipo de inmueble(s)', options=lista, placeholder='Selecciona uno o varios inmuebles')

        if isinstance(seleccion,list) and seleccion!=[] and not any([x for x in seleccion if 'todo' in x.lower()]):
            datauso = datauso[datauso['clasificacion'].isin(seleccion)]
            
        lista   = list(sorted(datauso['usosuelo'].unique()))
        tipouso = st.multiselect('Tipo de uso(s)', options=lista, placeholder='Selecciona uno o varios inmuebles')

        if isinstance(tipouso,list) and tipouso!=[] and not any([x for x in tipouso if 'todo' in x.lower()]):
            datauso = datauso[datauso['usosuelo'].isin(tipouso)]
            
        if not datauso.empty:
            precuso = list(datauso['precuso'].unique())
        else: 
            precuso = []
                
        areamin          = st.number_input('Área construida mínima',value=0,min_value=0)
        areamax          = st.number_input('Área construida máxima',value=0,min_value=0)
        estratomin       = st.number_input('Estrato mínima',value=0,min_value=0)
        estratomax       = st.number_input('Estrato máximo',value=0,min_value=0)
        desde_antiguedad = st.number_input('Año de construido desde (yyyy)',value=0,min_value=0)
        hasta_antiguedad = st.number_input('Año de construido hasta (yyyy)',value=datetime.now().year,min_value=0)

        inputvar = {'areamin':areamin,
                    'areamax':areamax,
                    'desde_antiguedad':desde_antiguedad,
                    'hasta_antiguedad':hasta_antiguedad,
                    'pisosmin':0,
                    'pisosmax':0,
                    'estratomin':estratomin,
                    'estratomax':estratomax,
                    'precuso':precuso
                    }
    
    #---------------------------------------------------------------------#
    # Data radio
    output,data_lote,data_geometry,latitud,longitud, polygon = getradio(grupo=grupo,inputvar=inputvar)
    
    data_caracteristicas = pd.DataFrame()
    if not data_geometry.empty:
        listagrupos          = list(data_geometry['grupo'].unique())
        data_caracteristicas = datapredios(grupo=listagrupos)

    try: polygon = wkt.loads(polygon)
    except: pass

    if not data_geometry.empty and 'distancia' in data_geometry: 
        data_geometry = data_geometry[data_geometry['distancia']<=metros]
    
    with col2:
        htmlrender = generar_html(grupo,output[metros],datageometry=data_geometry,latitud=latitud,longitud=longitud,polygon=polygon,metros=metros, data_caracteristicas=data_caracteristicas)
        st.components.v1.html(htmlrender, height=5000, scrolling=True)
        
    with colb2:
        if st.button('Generar PDF'):
            with st.spinner('Procesando PDF...'):
                pdf_bytes = _principal_getpdf(htmlrender,seccion='_download_pdf_estudio_mercado')
                
                if pdf_bytes:
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_bytes,
                        file_name="reporte.pdf",
                        mime='application/pdf'
                    )
                else:
                    st.error("Error al generar el PDF. Por favor intente nuevamente.")
        
@st.cache_data(show_spinner=False)
def datapredios(grupo=None):
    data      = datacaracteristicas(grupo=grupo,variables='grupo,barmanpre,general_catastro,nombre_ph')
    resultado = data[['grupo','barmanpre']]
    
    variable  = 'general_catastro'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df)
        df.columns   = ['formato']
        df           = pd.json_normalize(df['formato'])
        if not df.empty:
            df        = df.groupby(['grupo','barmanpre']).agg({'formato_direccion':'first','prenbarrio':'first','preaconst':'max','preaterre':'max','prevetustzmin':'min','prevetustzmax':'max','estrato':'max','connpisos':'max','preusoph':'first'}).reset_index()
            resultado = resultado.merge(df,on=['grupo','barmanpre'],how='left',validate='m:1')
            
    variable  = 'nombre_ph'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df)
        df.columns   = ['formato']
        df           = pd.json_normalize(df['formato'])
        if not df.empty:
            df        = df.groupby(['grupo','barmanpre']).agg({'nombre_conjunto':'first'}).reset_index()
            resultado = resultado.merge(df,on=['grupo','barmanpre'],how='left',validate='m:1')
            
    return resultado
        

def style_page(maxwidth=None):
    letra_options = '0.65vw'
    letra_titulo  = '0.65vw'

    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #fff;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #000;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-black.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="collapsedControl"] button {{
            background-color: transparent;
            border: none;
            cursor: pointer;
            padding: 0;
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
            height:
                0%;
            }}
            
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        
        div[data-testid="stSpinner"] {{
            color: #000000;
            background-color: #F0F0F0; 
            padding: 10px; 
            border-radius: 5px;
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
            
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
        }}
        
        .stButton button {{
                background-color: #A16CFF;
                font-weight: bold;
                width: 100%;
                border: 2px solid #A16CFF;
                color:white;
            }}
        
        .stButton button:hover {{
            background-color: #A16CFF;
            color: white;
            border: #A16CFF;
        }}
        
        .stButton button:active {{
            background-color: #FFF;
            color: #A16CFF;
            border: 2px solid #FFF;
            outline: none;
        }}
    
        [data-testid="stMultiSelect"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
        li[role="option"] > div {{
            font-size: {letra_options};
        }}
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] span {{
            font-size: {letra_options};
        }}
        
        [data-baseweb="select"] > div {{
            background-color: #fff;
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;
            font-size: {letra_options};
        }}
    
    
        [data-testid="stSelectbox"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;  
        }}
        
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
            
        }}

        [data-testid="stNumberInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;
            font-size: 5px;
        }}
        
        [data-baseweb="input"] > div {{
            background-color: #fff;
        }}
        
        div[data-testid="stNumberInput-StepUp"]:hover {{
            background-color: #A16CFF;
        }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: {letra_titulo};
            font-weight: bold;
            color: #3C3840;
            font-family: 'Aptos Narrow';
        }}
        
        span[data-baseweb="tag"] {{
          background-color: #5F59EB;
        }}
        
        [data-testid="stDateInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
            
        .stDownloadButton button {{
            background-color: #DAE8D8;
            font-weight: bold;
            width: 100%;
            border: 2px solid #DAE8D8;
            color: black;
        }}
        
        .stDownloadButton button:hover {{
            background-color: #DAE8D8;
            color: black;
            border: #DAE8D8;
        }}        

        [data-testid="stNumberInput-Input"] {{
            font-size: {letra_options};
        }}
        
        [data-testid="stTextInput-Input"] {{
            font-size: {letra_options};
        }}

        </style>
        """,
        unsafe_allow_html=True
    )
