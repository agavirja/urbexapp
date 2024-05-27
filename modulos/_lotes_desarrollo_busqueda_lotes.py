import streamlit as st
import copy
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from data.getdatalotes import main as getdatalotes
from data.getdataconsolidacionlotes import main as getdataconsolidacionlotes

from display.stylefunctions  import style_function,style_function_geojson

def main():
    initialformat = {
        'access':False,
        'token':'',
        }
    for key,value in initialformat.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = 1920
    mapwidth   = int(screensize*0.85)
    mapheight  = int(screensize*0.25)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize*0.85)
        mapheight  = int(screensize*0.25)
    except: pass
 
    if st.session_state.access:
        landing(mapwidth,mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(mapwidth,mapheight):
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_lotes':None,
               'reporte_busqueda_lotes':False,
               'datalotes_busqueda_lotes': pd.DataFrame(),
               'geojson_data':None,
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               'options':        ['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'optionsoriginal':['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'default':[],
               'resetear':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
            
    colm1,colm2,colm3    = st.columns([0.025,0.95,0.025])
    colf1,colf2          = st.columns(2)
    colb1,colb2          = st.columns(2)

    areamin              = 0
    areamax              = 0
    antiguedadmin        = 0
    antiguedadmax        = 0
    maxpiso              = 6
    alturaminpot         = 0
    maxpredios           = 0
    maxpropietario       = 0 
    maxavaluo            = 0 
    loteesquinero        = 'Todos'
    viaprincipal         = 'Todos'
    usodelsuelo          = 'Todos'
    tratamiento          = []
    areaactividad        = []
    actuacionestrategica = 'Todos'

    with colf1: areamin              = st.number_input('Área de terreno mínima',value=0,min_value=0)
    with colf2: areamax              = st.number_input('Área de terreno máxima',value=0,min_value=0)
    with colf1: maxpiso              = st.number_input('Número máximo de pisos construidos actualmente',value=2,min_value=0)
    with colf2: alturaminpot         = st.number_input('Altura mínima P.O.T',value=0,min_value=0)
    with colf1: tratamiento          = st.multiselect('Tratamiento P.O.T',['CONSOLIDACION', 'DESARROLLO', 'RENOVACION', 'CONSERVACION', 'MEJORAMIENTO INTEGRAL'])
    with colf2: actuacionestrategica = st.selectbox('Actuación estrategica', options=['Todos','Si','No'])
    with colf1: areaactividad        = st.multiselect('Área de actividad P.O.T',['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
    with colf2: maxpropietario       = st.number_input('Número máximo de propietarios',value=0,min_value=0)
    with colf1: loteesquinero        = st.selectbox('Lote esquinero', options=['Todos','Si','No'])
    with colf2: viaprincipal         = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])
    with colf1: frente               = st.number_input('Área de frente mínima',value=0,min_value=0)
    with colf1: maxavaluo            = st.number_input('Valor máximo de avalúo catastral',value=0,min_value=0)
    with colf2: maxpredios           = st.number_input('Número máximo de predios actuales en el lote',value=0,min_value=0)

    #usodelsuelo   = st.selectbox('Uso del suelo', options=['Todos','Si','No'])
        
    #-------------------------------------------------------------------------#
    # Mapa
    m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)

    if st.session_state.geojson_data is not None:
        if st.session_state.datalotes_busqueda_lotes.empty:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function).add_to(m)
        else:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function_color).add_to(m)

    if not st.session_state.datalotes_busqueda_lotes.empty:
        geojson = data2geopandas(st.session_state.datalotes_busqueda_lotes)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    with colm2:
        st_map = st_folium(m,width=mapwidth,height=mapheight)

    if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
        if st_map['all_drawings']!=[]:
            if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                coordenadas                              = st_map['all_drawings'][0]['geometry']['coordinates']
                st.session_state.polygon_busqueda_lotes = Polygon(coordenadas[0])
                st.session_state.geojson_data            = mapping(st.session_state.polygon_busqueda_lotes)
                polygon_shape                            = shape(st.session_state.geojson_data)
                centroid                                 = polygon_shape.centroid
                st.session_state.latitud                 = centroid.y
                st.session_state.longitud                = centroid.x
                st.session_state.zoom_start              = 16
                st.rerun()
                
    if 'last_circle_polygon' in st_map and st_map['last_circle_polygon'] is not None:
        if st_map['last_circle_polygon']!=[]:
            coordenadas = st_map['last_circle_polygon']['coordinates'][0]
            st.session_state.polygon_busqueda_lotes = Polygon(coordenadas)
            st.session_state.geojson_data            = mapping(st.session_state.polygon_busqueda_lotes)
            polygon_shape                            = shape(st.session_state.geojson_data)
            centroid                                 = polygon_shape.centroid
            st.session_state.latitud                 = centroid.y
            st.session_state.longitud                = centroid.x
            st.session_state.zoom_start              = 16
            st.rerun()
            
    #-------------------------------------------------------------------------#
    # Reporte
    inputvar = {
        'areamin':areamin,
        'areamax':areamax,
        'antiguedadmin':antiguedadmin,
        'antiguedadmax':antiguedadmax,
        'maxpiso':maxpiso,
        'maxpredios':maxpredios,
        'maxpropietario':maxpropietario,
        'maxavaluo':maxavaluo,
        'loteesquinero':loteesquinero,
        'viaprincipal':viaprincipal,
        'usodelsuelo':usodelsuelo,
        'pot':[{'tipo':'tratamientourbanistico','alturaminpot':alturaminpot,'tratamiento':tratamiento},
               {'tipo':'areaactividad','nombreare':areaactividad},
               {'tipo':'actuacionestrategica','isin':actuacionestrategica},
               ]
        }

    if st.session_state.polygon_busqueda_lotes is not None:  
        inputvar['polygon'] = str(st.session_state.polygon_busqueda_lotes)
        with colb1:
            if st.button('Buscar'):
                with st.spinner('Buscando información'):
                    _d,st.session_state.datalotes_busqueda_lotes = getdataconsolidacionlotes(inputvar)
                    st.rerun()

        with colb2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
                    
@st.cache_data(show_spinner=False)
def data2geopandas(data):
    
    urlexport = "http://urbex.com.co/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
                        
            combinacionlotes = ""
            urllink = ""
            combinacion = items['combinacion'] if 'combinacion' in items and isinstance(items['combinacion'], str) else None
            if combinacion is not None:
                urllink = urlexport+f"?type=lote&code={combinacion}&token={st.session_state.token}"
            if 'num_lotes_comb' in items:
                combinacionlotes += """
                <b> Ver lote<br>
                """
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {combinacionlotes}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  
