import streamlit as st
import folium
import re
import pandas as pd
import random
import hashlib
from streamlit_folium import folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from datetime import datetime

from functions._principal_propietarios_polygon import main as _principal_propietarios
from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon

from display._principal_generador_leads import main as generar_html

from data.tracking import savesearch

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_leads_default':None,
               'reporte_leads_default':False,
               'data_leads': pd.DataFrame(),
               'datalotes': pd.DataFrame(),
               'geojson_data_leads_default':None,
               'zoom_start_data_leads_default':12,
               'latitud_leads_default':4.652652, 
               'longitud_leads_default':-74.077899,
               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'

    #-------------------------------------------------------------------------#
    # Clasificacion / uso del suelo
    datauso = usosuelo_class()

    #-------------------------------------------------------------------------#
    # Busqueda por direccion   
    col1,col2,col3,col4,col5 = st.columns([0.3,0.15,0.3,0.15,0.1],vertical_alignment='center')
    with col1:
        tipobusqueda = st.selectbox('Ubicación por:',options=['Dirección'])
    with col2:
        ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
    with col3:
        direccion = st.text_input('Dirección:',value='')   
    with col4:
        metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=0)   
    with col5:
        disabled = False if isinstance(direccion,str) and direccion!='' and metros<=500 else True
        if st.button('Ubicar en el mapa',disabled=disabled):
            st.session_state.latitud_leads_default,st.session_state.longitud_leads_default,barmanpre_ref = getlatlng(f'{direccion},{ciudad.lower()},colombia')
            st.session_state.polygon_leads_default      = circle_polygon(metros,st.session_state.latitud_leads_default,st.session_state.longitud_leads_default)
            st.session_state.geojson_data_leads_default = mapping(st.session_state.polygon_leads_default)
            st.session_state.zoom_start_data_leads_default = 16
            st.rerun()
    st.markdown('<div style="padding: 30px;"></div>', unsafe_allow_html=True)
    
    #-------------------------------------------------------------------------#
    # Formulario      
    col1,col2,col3 = st.columns([0.25,0.25,0.5])      
    with col1: 
        
        #lista        = ['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero']
        lista         = list(sorted(datauso['clasificacion'].unique()))
        lista         = ['Todos'] + lista
        
        seleccion       = st.multiselect('Tipo de inmueble(s) que sean propietarios:', key='seleccion',options=lista, default=['Todos'],placeholder='Selecciona uno o varios inmuebles')
        propiedades     = st.number_input('Número mínimo de propiedades:',value=1,min_value=0)
        actuales        = st.selectbox('Actualmente que sean propietarios?:',options=['Todos','Si', 'No'])
        valormin        = st.number_input('Valor mínimo de las propiedades (total propiedades):',value=0,min_value=0)
        areamin         = st.number_input('Área construida mínima:',value=0,min_value=0)
        edadmin         = st.number_input('Edad mínima:',value=0,min_value=0)
        precuso         = []
        if not any([x for x in seleccion if 'tod' in x.lower()]):
            datauso = datauso[datauso['clasificacion'].isin(seleccion)]
            if not datauso.empty:
                precuso = list(datauso['precuso'].unique())
                
    with col2: 
        tipopropietario = st.selectbox('Tipo de propietario:',options=['Todos','PERSONA NATURAL', 'PERSONA JURIDICA'])
        hacecuanto      = st.number_input('Hace cuanto es propietario (años):',value=0,min_value=0)
        credito         = st.selectbox('Hayan sacado un crédito en los últimos 5 años?:',options=['Todos','Si', 'No'])
        valormax        = st.number_input('Valor máximo de las propiedades (total propiedades):',value=0,min_value=0)
        areamax         = st.number_input('Área construida máxima:',value=0,min_value=0)
        edadmax         = st.number_input('Edad máxima:',value=0,min_value=0)

    #-------------------------------------------------------------------------#
    # Mapa
    with col3:
        m = folium.Map(location=[st.session_state.latitud_leads_default, st.session_state.longitud_leads_default], zoom_start=st.session_state.zoom_start_data_leads_default,tiles="cartodbpositron")
        
        if st.session_state.data_leads.empty:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
        if st.session_state.geojson_data_leads_default is not None:
            folium.GeoJson(st.session_state.geojson_data_leads_default, style_function=style_function_color).add_to(m)

        folium_static(m,width=int(mapwidth*0.4),height=700)
            
    col1,col2,col3 = st.columns([0.25,0.25,0.5])  
    with col1:
        if st.button('Resetear búsqueda'):
            for key,value in formato.items():
                del st.session_state[key]
            st.rerun()

    if st.session_state.polygon_leads_default is not None:
        with col2:
            if st.button('Buscar'):
                inputvar = {
                    'precuso':precuso,
                    'tipopropietario':tipopropietario,
                    'propiedades':propiedades,
                    'hacecuanto':hacecuanto,
                    'actuales':actuales,
                    'valormin':valormin,
                    'valormax':valormax,
                    'areamin':areamin,
                    'areamax':areamax,
                    'edadmin':edadmin,
                    'edadmax':edadmax,
                    'credito':credito,
                    'polygon':str(st.session_state.polygon_leads_default)
                    }
                with st.spinner('Buscando información'):
                    st.session_state.data_leads, st.session_state.datalotes = _principal_propietarios(polygon=str(st.session_state.polygon_leads_default),grupo=None,inputvar=inputvar)
                    st.session_state.reporte_leads_default = True
                
                # Guardar:
                _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_comercial_generador_leads', inputvar)
                st.rerun()

    if st.session_state.reporte_leads_default and not st.session_state.data_leads.empty:
        try:
            df          = st.session_state.data_leads.copy()
            df['email'] = df['email'].str.split('|')
            df          = df.explode('email')
            df['email'] = df['email'].str.strip()
            df          = df[df['email'].notnull()]
            df          = df.sort_values(by='tipoPropietario',ascending=False)
            
            variables = [x for x in ['fechaDocumento','precuso',] if x in df]
            if variables!=[]: 
                df.drop(columns=variables,inplace=True)
                
            try:
                idd = (df['email'].astype(str).str.contains('.')) & (df['email'].astype(str).str.contains('@'))
                df  = df[idd]
                idd = df['email'].astype(str).str.lower().contains('notaria')
                df  = df[~idd]
            except: pass
                
            encriptar = True
            if encriptar:
                df["email"]     = df["email"].apply(hash_email) if 'email' in df else None
                df["nombre"]    = df["nombre"].apply(anonymize_text)  if 'nombre' in df else None
                df["numero"]    = df["numero"].astype(str).apply(anonymize_text)  if 'numero' in df else None
                df["telefonos"] = df["telefonos"].astype(str).apply(anonymize_phone)  if 'telefonos' in df else None

            df.rename(columns={"tipo":"Tipo documento",	"numero":"documento",	"tipoPropietario":"Tipo de propietario",	"nombre":"Nombre",	"propiedades":"Propiedades",	"areamin":"Area construida minima",	"areamax":"Area construida maxima",	"valor":"Valor total",	"minyaer":"Antiguedad min",	"maxyear":"Antiguedad max",	"email":"Email",	"credito":"Tiene credito",	"edad":"Edad"},inplace=True)
            
            maxlen = len(df)
            df     = df.iloc[0:1000,:]
            
            col1,col2,col2 = st.columns([6,1,1])
            with col2:
                if st.button('Descargar Leads'):
                    download_excel(df)
                    if maxlen>1000:
                        with col1:
                            st.write('Por políticas de manejo de la información se permite bajar un máximo de 1,000 registros, si necesita más información por favor ponerse en contacto con un comercial de Urbex')
        except: pass

        htmlrender = generar_html(data=st.session_state.data_leads.copy(), datageometry=st.session_state.datalotes.copy(), latitud=st.session_state.latitud_leads_default, longitud=st.session_state.longitud_leads_default,polygon=str(st.session_state.polygon_leads_default))
        st.components.v1.html(htmlrender, height=5000, scrolling=True)


def download_excel(df):
    excel_file = df.to_excel('urbex_leads.xlsx', index=False)
    with open('urbex_leads.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Haz clic aquí para descargar",
        data=data,
        file_name='data_urbex_leads.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
def hash_email(email):
    if pd.isna(email) or email == "":
        return ""
    email = email.strip().lower()  # Estandarizar (el hashing es sensible a mayúsculas/minúsculas)
    return hashlib.sha256(email.encode()).hexdigest()

# Función para anonimizar nombres y documentos
def anonymize_text(text):
    if pd.isna(text) or text == "":
        return ""
    words = text.split()
    masked_words = []
    for word in words:
        if len(word) > 3:
            masked_words.append(word[:3] + "*" * (len(word) - 3))
        else:
            masked_words.append(word)  # Si la palabra tiene 3 caracteres o menos, se deja igual
    return " ".join(masked_words)

# Función para anonimizar números de teléfono
def anonymize_phone(phone):
    if pd.isna(phone) or phone == "":
        return ""
    phones = phone.split(" | ")
    masked_phones = [p[:3] + "***" if len(p) > 3 else p for p in phones]
    return " | ".join(masked_phones)

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }
