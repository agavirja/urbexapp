import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from shapely import wkt
from datetime import datetime

from display.stylefunctions  import style_function_geojson

from functions._principal_getdatalotes import main as getdatalotes
from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon

from data.tracking import savesearch,update_save_status

def main(screensize=1920,inputvar={}):

    try: inputvar = json.loads(inputvar)
    except: pass

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_default_favoritos':None,
               'reporte_busqueda_default_favoritos':False,
               'data_lotes_busqueda_favoritos': pd.DataFrame(),
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
    
    
    if not st.session_state.data_lotes_busqueda_favoritos.empty:
        if 'fecha_update' in st.session_state.data_lotes_busqueda_favoritos: 
            del st.session_state.data_lotes_busqueda_favoritos['fecha_update']
            
    #-------------------------------------------------------------------------#
    # Clasificacion / uso del suelo
    datauso = usosuelo_class()
    
    #-------------------------------------------------------------------------#
    # Formulario      
    col1,col2 = st.columns([0.3,0.7])      
    with col1: 
        
        #lista        = ['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero']
        lista         = list(sorted(datauso['clasificacion'].unique()))
        lista         = ['Todos'] + lista
        
        seleccion     = st.multiselect('Tipo de inmueble(s)', key='seleccion',options=lista, default=inputvar['tipoinmueble'] if 'tipoinmueble' in inputvar else ['Todos'],placeholder='Selecciona uno o varios inmuebles')
        areamin       = st.number_input('Área construida mínima',value=inputvar['areamin'] if 'areamin' in inputvar else 0,min_value=0)
        areamax       = st.number_input('Área construida máxima',value=inputvar['areamax'] if 'areamax' in inputvar else 0,min_value=0)
        estratomin    = st.number_input('Estrato mínima',value=inputvar['estratomin'] if 'estratomin' in inputvar else 0,min_value=0)
        estratomax    = st.number_input('Estrato máximo',value=inputvar['estratomax'] if 'estratomax' in inputvar else 0,min_value=0)
        antiguedadmin = st.number_input('Año de construido desde (yyyy)',value=inputvar['antiguedadmin'] if 'antiguedadmin' in inputvar else 0,min_value=0)
        antiguedadmax = st.number_input('Año de construido hasta (yyyy)',value=datetime.now().year,min_value=0)

    #-------------------------------------------------------------------------#
    # Mapa
    with col2:
        
        try:
            st.session_state.polygon_busqueda_default_favoritos = wkt.loads(inputvar['polygon'])
            latitud  = st.session_state.polygon_busqueda_default_favoritos.centroid.y
            longitud = st.session_state.polygon_busqueda_default_favoritos.centroid.x
        except: 
            st.session_state.polygon_busqueda_default_favoritos = None
            latitud  = None
            longitud = None
            
        m = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
        
        if st.session_state.polygon_busqueda_default_favoritos is not None:
            folium.GeoJson(st.session_state.polygon_busqueda_default_favoritos, style_function=style_function_color).add_to(m)

        if not st.session_state.data_lotes_busqueda_favoritos.empty:
            geojson = data2geopandas(st.session_state.data_lotes_busqueda_favoritos)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
        folium_static(m,width=int(mapwidth*0.6),height=700)
                
    if st.session_state.polygon_busqueda_default_favoritos is not None:
        with col1:
            if st.button('Buscar'):
                inputvar = {
                    'tipoinmueble':seleccion,
                    'areamin':areamin,
                    'areamax':areamax,
                    'antiguedadmin':antiguedadmin,
                    'antiguedadmax':antiguedadmax,
                    'estratomin':estratomin,
                    'estratomax':estratomax,
                    'polygon':str(st.session_state.polygon_busqueda_default_favoritos)
                    }
                with st.spinner('Buscando informacion'):
                    st.session_state.data_lotes_busqueda_favoritos = getdatalotes(inputvar=inputvar)
                    st.session_state.reporte_busqueda_default_favoritos = True
                st.rerun()
                
                
                
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }


@st.cache_data(show_spinner=False)
def data2geopandas(data):
    
    try: data = getitems(data)
    except: pass
    urlexport = "http://localhost:8501/Reporte"
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
        
            params       = {'type':'predio','grupo':items['grupo'],'barmanpre':items['barmanpre'],'token':st.session_state.token}
            params       = json.dumps(params)
            params       = base64.urlsafe_b64encode(params.encode()).decode()
            params       = urllib.parse.urlencode({'token': params})
            
            urllink      = f"{urlexport}?{params}"
            buildinfinfo = ""

            try:    buildinfinfo += f"""<b> Dirección:</b> {items['formato_direccion']}<br>""" if isinstance(items['formato_direccion'],str) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Nombre Edificio:</b> {items['nombre_conjunto']}<br>""" if isinstance(items['nombre_conjunto'],str) else ''
            except: pass     
            try:    buildinfinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """ if isinstance(items['prenbarrio'],str) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br>  """ if isinstance(items['estrato'],(float,int)) and items['estrato']>0 else ''
            except: pass
            try:    buildinfinfo += f"""<b> Área construida total:</b> {items['preaconst']:.2f}<br>""" if isinstance(items['preaconst'],(float,int)) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Área de terreno total:</b> {items['preaterre']:.2f}<br>""" if isinstance(items['preaterre'],(float,int)) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>""" if isinstance(items['prevetustzmin'],(float,int)) else ''
            except: pass            
            try:    buildinfinfo += f"""<b> Total de predios:</b> {int(items['predios'])}<br> """ if isinstance(items['predios'],(float,int)) else ''
            except: pass                    
            try:    buildinfinfo += f"""<b> Número transacciones:</b> {int(items['numero_transacciones'])}<br> """
            except: pass    

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {buildinfinfo}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def getitems(data):
    
    datamerge = data[['barmanpre']]
    formato   = [
        {'column':'general_catastro','variables':['barmanpre','formato_direccion', 'prenbarrio', 'preaconst', 'preaterre', 'prevetustzmin', 'estrato', 'predios']},
        {'column':'nombre_ph','variables':['barmanpre','nombre_conjunto']},
        {'column':'localizacion','variables':['barmanpre','locnombre']}
                 ]
    for i in formato:
        item       = i['column']
        variables  = i['variables']
        df         = data[['barmanpre',item]]
        df         = df[df[item].notnull()]
        df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df[df[item].notnull()]
        df         = df.explode(item)
        df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
        if isinstance(variables,list) and variables!=[]:
            df     = df[variables]
            df     = df.sort_values(by=variables, na_position='last')
        datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
            
    dataresultado = data[['grupo','barmanpre','wkt']]

    if not datamerge.empty:
        vargroup      = {'prenbarrio': 'first', 'preaconst': 'sum', 'preaterre': 'sum', 'prevetustzmin': 'min', 'estrato': 'max', 'predios': 'sum', 'locnombre': 'first'} 
        vargroup      = {k: v for k, v in vargroup.items() if k in datamerge.columns}
        datapaso      = datamerge.groupby('barmanpre').agg(vargroup).reset_index()
        dataresultado = dataresultado.merge(datapaso,on='barmanpre',how='left',validate='1:1')
        
        for j in ['formato_direccion','nombre_conjunto']:
            if j in datamerge:
                datapaso         = datamerge[datamerge[j].notnull()]
                datapaso         = datapaso.drop_duplicates(subset=['barmanpre',j],keep='first')
                datapaso         = datapaso[['barmanpre',j]]
                datapaso         = datapaso.groupby('barmanpre')[j].agg(lambda x: ' | '.join(x)).reset_index()
                datapaso.columns = ['barmanpre',j]
                dataresultado    = dataresultado.merge(datapaso,on='barmanpre',how='left',validate='1:1')
            
    return dataresultado