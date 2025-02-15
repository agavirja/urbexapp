import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import random
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_folium import folium_static
from datetime import datetime

from data._principal_heatmap import main as dataheatmap
from data.getuso_destino import usosuelo_class
from data.tracking import savesearch

from display.stylefunctions  import style_function_geojson

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_localizador_marcas':pd.DataFrame(),               

               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_modulo_analisis_heat_map', None)

    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'
        
    #-------------------------------------------------------------------------#
    # Formulario  
    coll1, coll2 = st.columns([0.2,0.8])
    col1, col2   = st.columns([0.2,0.8])
    duso         = usosuelo_class()
    with col1:
        year    = st.selectbox('Año:',options=['Todos',2024,2023,2022,2021,2020])
        formato = st.selectbox('Segmentación:',options=['Cuadrantes','Barrios'])
        if 'Cuadrantes' in formato: formato = 'grid'
        elif 'Barrios'  in formato: formato = 'barrios'
        
        options = sorted(duso['clasificacion'].unique())
        options = ['Todos'] + options
        claasificacion = st.selectbox('Tipo de inmueble:',options=options)
        if 'todo' not in claasificacion.lower():
            duso = duso[duso['clasificacion']==claasificacion]

        options  = sorted(duso['usosuelo'].unique())
        options  = ['Todos'] + options
        usosuelo = st.selectbox('Uso del suelo:',options=options)
        precuso  = []
        if 'todo' not in usosuelo.lower():
            precuso = list(duso[duso['usosuelo']==usosuelo]['precuso'].unique())

        tipoconsulta = st.selectbox('Tipo de busqueda:',options=['Valor transacciones','# Transacciones'])
        if 'Valor transacciones' in tipoconsulta: 
            tipoconsulta = 'valormt2_transacciones'
        elif '# Transacciones' in tipoconsulta:
            tipoconsulta = 'transacciones'
                
        data,label = dataheatmap(year=year,formato=formato,precuso=precuso,tipoconsulta=tipoconsulta)

    #-------------------------------------------------------------------------#
    # Heat Map
    #-------------------------------------------------------------------------#
    with coll2:
        if not label.empty:
            html = labelhtml(label)
            st.components.v1.html(html, height=60)
        
    with col2:
        m    = folium.Map(location=[4.652652, -74.077899], zoom_start=12,tiles="cartodbpositron") #"cartodbdark_matter"
    
        if not data.empty:
            geojson = data2geopandas(data)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
        
        folium_static(m,width=int(mapwidth*0.8),height=800)
            
        
      

@st.cache_data(show_spinner=False)
def data2geopandas(data):
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            
            popuptext = ""
            try:    popuptext += f"""<b>Valor transacciones mt2:</b> ${items['valormt2_transacciones']:,.0f} m²<br>"""
            except: pass
            try:    popuptext += f"""<b>Número de transacciones:</b> {items['transacciones']}<br>"""
            except: pass
            try:
                if isinstance(items['scanombre'], str) and items['scanombre']!="":
                    popuptext += f"""<b>Barrio catastral:</b> {items['scanombre']}<br>"""
            except: pass       
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                    {popuptext}
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def labelhtml(data):
    
    data['color'] = data['color'].apply(lambda x: f'<span class="legend-color" style="background:{x};"></span>')
    data['value'] = data['value'].apply(lambda x: f'<span>{x}</span>')
    colors        = ''.join(data['color'])
    valores       = ''.join(data['value'])

    style = """
    <style>
        .legend-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 20px;
        }
        .legend-bar {
            display: flex;
            align-items: center;
            position: relative;
        }
        .legend-color {
            height: 20px;
            width: 100px; /* Width of each color box */
            margin: 0; /* Remove margin */
        }
        .legend-numbers {
            display: flex;
            justify-content: space-between;
            position: absolute;
            top: 20px; 
            left: calc(50% + 60px); /* Move numbers a bit to the right */
            transform: translateX(-50%); /* Adjust to center relative to the new position */
            width: calc(100px * 6); /* Width based on the number of colors */
            font-size: 12px;
            color: #555;
            margin: 0; /* Remove margin */
            padding: 0; /* Remove padding */
            text-align: center; /* Center numbers horizontally within their space */
        }
        .legend-numbers span {
            display: block;
            width: 100px; /* Same width as color boxes */
            text-align: center;
            margin: 0; /* Remove margin */
            padding: 0; /* Remove padding */
        }
    </style>

    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
    </head>
    <body>
        <!-- Leyenda del Mapa de Calor -->
        <div class="legend-container">
            <div class="legend-bar">
                {colors}
                <div class="legend-numbers">
                {valores}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html