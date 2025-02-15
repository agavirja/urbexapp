import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from streamlit_folium import folium_static
from datetime import datetime

from data._principal_normativa_urbana  import getoptionsnormativa,getlotesnormativa

from display.stylefunctions  import style_function_geojson

from functions.getuso_destino import usosuelo_class

from data.tracking import savesearch

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_lotes_normativa_urbana':  pd.DataFrame(),

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
    # Formulario
    
    dataoptions = getoptionsnormativa()

    col1,col2 = st.columns([0.3,0.7])      
    with col1: 
        inputvar = []
        for items in list(dataoptions['variable'].unique()):
            
            datapaso = dataoptions[dataoptions['variable']==items]
            select   = st.selectbox(f'{items}',options=list(datapaso['input'].unique()))
            inputvar.append({'variable':items,'input':select,'indice':datapaso[datapaso['input']==select]['indice'].iloc[0]})
            
        st.write(inputvar)
        
        if st.button('Buscar'):
            # Guardar:
            _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_busqueda_lotes_normativa_urbana', inputvar)

            st.session_state.data_lotes_normativa_urbana = getlotesnormativa(inputvar)

    with col2:
        m = folium.Map(location=[st.session_state.latitud_busqueda_lotes_default, st.session_state.longitud_busqueda_lotes_default], zoom_start=st.session_state.zoom_start_data_busqueda_lotes_default,tiles="cartodbpositron")
        
        if not st.session_state.data_lotes_normativa_urbana.empty:
            geojson = data2geopandas(st.session_state.data_lotes_normativa_urbana)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        folium_static(m,width=int(mapwidth*0.6),height=700)
            
              
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }


@st.cache_data(show_spinner=False)
def data2geopandas(data):
    urlexport = "http://www.urbex.com.co/Lotes"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#003F2D' #'#003F2D'
        for idd,items in data.iterrows():
        
            params       = {'type':'combinacion_lote','grupo':items['grupo'],'barmanpre':items['barmanpre'],'token':st.session_state.token}
            params       = json.dumps(params)
            params       = base64.urlsafe_b64encode(params.encode()).decode()
            params       = urllib.parse.urlencode({'token': params})
            
            urllink  = f"{urlexport}?{params}"
            manzinfo = ""

            try:    manzinfo += f"""<b> Número de lotes:</b> {int(items['lotes'])}<br>""" if isinstance(items['lotes'],(float,int)) else ''
            except: pass
        
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {manzinfo}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content


        geojson = data.to_json()
    return geojson

def style_function_geojson_dash(feature):
    color = feature['properties']['color']
    return {
        'fillColor': color,
        'color': 'blue',
        'weight': 1, 
        'dashArray': '5, 5',
        'fillOpacity': 0.2,
    }
