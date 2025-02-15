import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from shapely import wkt
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from datetime import datetime

from display.stylefunctions  import style_function_geojson

from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon
from functions._principal_getdatalotes_combinacion import main as _principal_getlotes

from data._principal_normativa_urbana  import getoptionsnormativa
from data._principal_shapefile import localidad as datalocalidad
from data.tracking import savesearch

def main(screensize=1920,inputvar={}):

    try: inputvar = json.loads(inputvar)
    except: pass

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_lotes_combinacion_favoritos':  pd.DataFrame(),
               'search_button_clic_busqueda_lotes_default':False,
               'mapkey':None,
               'token':None,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'
        
    #-------------------------------------------------------------------------#
    # Data uso
    datauso          = usosuelo_class()
    dataoptions      = getoptionsnormativa()
    _,data_localidad = datalocalidad()
    
    
    #-------------------------------------------------------------------------#
    # Formulario      
    col1,col3 = st.columns([0.4,0.6])      
    with col1:
        
        # Primera fila
        colc1, colc2 = st.columns(2)
        
        with colc1:
            areaminlote = st.number_input('Área mínima del lote', value=inputvar['areaminlote'] if 'areaminlote' in inputvar else 0, min_value=0)
        
        with colc2:
            areamaxlote = st.number_input('Área máxima del lote', value=inputvar['areamaxlote'] if 'areamaxlote' in inputvar else 0, min_value=0)
        
        # Segunda fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista  = dataoptions[dataoptions['variable'] == 'pisos'].sort_values(by='indice')
            defaultidx = inputvar['pisos'] if 'pisos' in inputvar else 0
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '<2': 'Menor a 2 pisos', '<3': 'Menor a 3 pisos', '<4': 'Menor a 4 pisos', '>=4': 'Mayor o igual a 4 pisos'
            })
            select = st.selectbox('Pisos construidos actualmente en los lotes', options=list(datalista['input'].unique()),index=defaultidx)
            pisos = datalista[datalista['input'] == select]['indice'].iloc[0]
        
        with colc2:
            datalista  = dataoptions[dataoptions['variable'] == 'altura_min_pot'].sort_values(by='indice')
            defaultidx = inputvar['altura_min_pot'] if 'altura_min_pot' in inputvar else 0
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '<=3': 'Menor a 4 pisos', '>4': 'Mayor a 4 pisos', '>6': 'Mayor a 6 pisos',
                '>10': 'Mayor a 10 pisos', '>15': 'Mayor a 15 pisos'
            })
            select = st.selectbox('Altura mínima del P.O.T', options=list(datalista['input'].unique()),index=defaultidx)
            altura_min_pot = datalista[datalista['input'] == select]['indice'].iloc[0]
        
        # Tercera fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista          = dataoptions[dataoptions['variable']=='tratamiento'].sort_values(by='indice')
            defaultidx         = inputvar['tratamiento'] if 'tratamiento' in inputvar else 0
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Tratamiento urbanístico',options=list(datalista['input'].unique()),index=defaultidx)
            tratamiento        = datalista[datalista['input']==select]['indice'].iloc[0]
        
        with colc2:
            datalista          = dataoptions[dataoptions['variable']=='actuacion_estrategica'].sort_values(by='indice')
            defaultidx         = inputvar['actuacion_estrategica'] if 'actuacion_estrategica' in inputvar else 0
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Actuación estrategíca',options=list(datalista['input'].unique()),index=defaultidx)
            actuacion_estrategica = datalista[datalista['input']==select]['indice'].iloc[0]
        
        
        # Cuarta fila
        colc1 = st.columns(1)[0]
        with colc1:
            datalista          = dataoptions[dataoptions['variable']=='area_de_actividad'].sort_values(by='indice')
            defaultidx         = inputvar['area_de_actividad'] if 'area_de_actividad' in inputvar else 0
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Área de actividad',options=list(datalista['input'].unique()),index=defaultidx)
            area_de_actividad  = datalista[datalista['input']==select]['indice'].iloc[0]
    
        # Quinta fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista          = dataoptions[dataoptions['variable'] == 'numero_propietarios'].sort_values(by='indice')
            defaultidx         = inputvar['numero_propietarios'] if 'numero_propietarios' in inputvar else 0
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '1': 'Un propietario', '<5': 'Menos de 5 propietarios', '<10': 'Menos de 10 propietarios',
                '<20': 'Menos de 20 propietarios', '>=20': 'Más de 20 propietarios'
            })
            select = st.selectbox('Número de propietarios', options=list(datalista['input'].unique()),index=defaultidx)
            numero_propietarios = datalista[datalista['input'] == select]['indice'].iloc[0]

        with colc2:
            datalista          = dataoptions[dataoptions['variable']=='via_principal'].sort_values(by='indice')
            defaultidx         = inputvar['via_principal'] if 'via_principal' in inputvar else 0
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Vía principal',options=list(datalista['input'].unique()),index=defaultidx)
            via_principal      = datalista[datalista['input']==select]['indice'].iloc[0]
            
        # Sexta fila
        colc1, colc2 = st.columns(2)
        with colc1:
            estratomin = st.number_input('Estrato mínimo', value=inputvar['estratomin'] if 'estratomin' in inputvar else 0, min_value=0)
        
        with colc2:
            estratomax = st.number_input('Estrato máximo', value=inputvar['estratomax'] if 'estratomax' in inputvar else 0, min_value=0)

        # septima fila
        colc1 = st.columns(1)[0]
        with colc1:
            options = list(sorted(data_localidad['locnombre'].unique()))
            options = ['Todas'] + options
            defaultidx = options.index(inputvar['localidad']) if 'localidad' in inputvar else 0
            localidad  = st.selectbox('Localidad', options=options,index=defaultidx)
            
    #-------------------------------------------------------------------------#
    # Mapa
    with col3:

        try:
            polygon_lotes_default_favoritos = wkt.loads(inputvar['polygon'])
            latitud  = polygon_lotes_default_favoritos.centroid.y
            longitud = polygon_lotes_default_favoritos.centroid.x
        except: 
            polygon_lotes_default_favoritos = None
            latitud  = 4.652652
            longitud = -74.077899

        m = folium.Map(location=[latitud, longitud], zoom_start=12,tiles="cartodbpositron")
                
        if polygon_lotes_default_favoritos is not None:
            folium.GeoJson(polygon_lotes_default_favoritos, style_function=style_function_color).add_to(m)

        if not st.session_state.data_lotes_combinacion_favoritos.empty:
            geojson = data2geopandas(st.session_state.data_lotes_combinacion_favoritos)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        folium_static(m,width=int(mapwidth*0.6),height=700)


    inputvar = {
        'areaminlote':areaminlote,
        'areamaxlote':areamaxlote,
        'estratomin':estratomin,
        'estratomax':estratomax,
        'pisos':pisos,
        'altura_min_pot':altura_min_pot,
        'tratamiento':tratamiento,
        'actuacion_estrategica':actuacion_estrategica,
        'area_de_actividad':area_de_actividad,
        'via_principal':via_principal,
        'numero_propietarios':numero_propietarios,
        'localidad':localidad,
        'polygon':str(polygon_lotes_default_favoritos)
        }

    col1,col2 = st.columns([0.4,0.6])      
    with col1:
        if st.button('Buscar'):
            with st.spinner('Buscando información'):
                st.session_state.data_lotes_combinacion_favoritos = _principal_getlotes(inputvar=inputvar)
                st.session_state.search_button_clic_busqueda_lotes_default = True
                st.rerun()

    if st.session_state.search_button_clic_busqueda_lotes_default and st.session_state.data_lotes_combinacion_favoritos.empty:
        st.error('No se encontraron lotes que cumplen con las características')
        
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

@st.cache_data(show_spinner=False)
def data2geopandas(data):

    urlexport = "http://localhost:8501/Lotes"
    geojson   = pd.DataFrame().to_json()
    if 'geometry' in data: 
        data = data[data['geometry'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['geometry'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#003F2D' #'#003F2D' - #5A189A
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            if 'grupo' in items:
                params       = {'type':'combinacion_lote','grupo':items['grupo'],'barmanpre':items['barmanpre'] if 'barmanpre' in items else None,'token':st.session_state.token}
                params       = json.dumps(params)
                params       = base64.urlsafe_b64encode(params.encode()).decode()
                params       = urllib.parse.urlencode({'token': params})
                
                urllink  = f"{urlexport}?{params}"
                generalinfo = ""
                
                areapolygon = "{:.2f} m²".format(items['areamaxcombinacion']) if 'areamaxcombinacion' in items and isinstance(items['areamaxcombinacion'],(float,int)) else None
                generalinfo += f"""<b> Número máximo de lotes para consolidar:</b> {len(items['grupo'].split('|'))}<br>"""
                generalinfo += f"""<b> Área máxima consolidación de lotes:</b> {areapolygon}<br>"""  if areapolygon is not None else ''
                generalinfo += "<b> Ver lotes</b><br>"
            
                popup_content =  f'''
                <!DOCTYPE html>
                <html>
                    <body>
                        <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:300px;font-size: 12px;">
                            <a href="{urllink}" target="_blank" style="color: black;">
                                {generalinfo}
                            </a>
                        </div>
                    </body>
                </html>
                '''
                data.loc[idd,'popup'] = popup_content
            
        geojson = data.to_json()
    return geojson