import streamlit as st
import re
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup
from shapely.ops import cascaded_union,unary_union

from data.getdatalotes import main as getdatalotes
from data.getdatalotesedificios import main as getdatalotesedificios
from data.data_pot_manzana import consolidacionlotesselected
from data.coddir import coddir 

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

    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_cabida_lotes':None,
               'geojson_cabida_lotes':None,
               'zoom_cabida_lotes':12,
               'latitud_cabida_lotes':4.652652, 
               'longitud_cabida_lotes':-74.077899,
               'datalotes_cabida_lotes': pd.DataFrame(),
               'reporte_cabida_lotes':False,
               'estado':'search',
               'data_consolidacion_cabida_lotes':pd.DataFrame(),
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    
 
    colm1,colm2,colm3 = st.columns([0.025,0.95,0.025])
    colb1,colb2       = st.columns(2)

    #-------------------------------------------------------------------------#
    # Mapa
    with colm2:
        with st.container():
            m    = folium.Map(location=[st.session_state.latitud_cabida_lotes, st.session_state.longitud_cabida_lotes], zoom_start=st.session_state.zoom_cabida_lotes,tiles="cartodbpositron")
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
            if st.session_state.geojson_cabida_lotes is not None:
                if st.session_state.datalotes_cabida_lotes.empty:
                    folium.GeoJson(st.session_state.geojson_cabida_lotes, style_function=style_function).add_to(m)
                else:
                    folium.GeoJson(st.session_state.geojson_cabida_lotes, style_function=style_function_color).add_to(m)
        
            if not st.session_state.datalotes_cabida_lotes.empty:
                geojson = data2geopandas(st.session_state.datalotes_cabida_lotes,seleccion=[])
                popup   = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
                
            if not st.session_state.data_consolidacion_cabida_lotes.empty:
                geojson  = data2consolidacion(st.session_state.data_consolidacion_cabida_lotes)
                popup   = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_lineado,popup=popup).add_to(m)

            st_map = st_folium(m,width=mapwidth,height=mapheight)
    
            colb1,colb2,colb3  = st.columns(3)
            if 'search' in st.session_state.estado:
                if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                    if st_map['all_drawings']!=[]:
                        if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                            coordenadas                            = st_map['all_drawings'][0]['geometry']['coordinates']
                            st.session_state.polygon_cabida_lotes  = Polygon(coordenadas[0])
                            st.session_state.geojson_cabida_lotes  = mapping(st.session_state.polygon_cabida_lotes)
                            polygon_shape                          = shape(st.session_state.geojson_cabida_lotes)
                            centroid                               = polygon_shape.centroid
                            st.session_state.latitud_cabida_lotes  = centroid.y
                            st.session_state.longitud_cabida_lotes = centroid.x
                            st.session_state.zoom_cabida_lotes     = 16
                            st.session_state.estado                = 'consolidacion' 
                            st.rerun()

            if 'consolidacion' in st.session_state.estado:
                if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                    if st_map['all_drawings']!=[]:
                        if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                            coordenadas     = st_map['all_drawings'][0]['geometry']['coordinates']
                            polygonselected = Polygon(coordenadas[0])
                            col1,col2,col3  = st.columns([0.35,0.35,0.3])
                            if polygonselected is not None:
                                with colb3:
                                    if st.button('Consolidar lotes'):
                                        with st.spinner('Consolidando lotes'):
                                            st.session_state.data_consolidacion_cabida_lotes = consolidacionlotesselected(polygon=str(polygonselected))
                                            st.session_state.zoom_start = 16
                                            st.rerun()

    
    if st.session_state.polygon_cabida_lotes is not None:  
        inputvar = {'polygon':str(st.session_state.polygon_cabida_lotes)}
        with colb1:
            if st.button('Buscar'):
                st.session_state.reporte_cabida_lotes = True
                st.rerun()

        with colb2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
            
    if st.session_state.reporte_cabida_lotes:
        with colm2:
            with st.spinner('Buscando data'):
                st.session_state.datalotes_cabida_lotes = getdatalotes(inputvar)
                st.session_state.reporte_cabida_lotes   = False
                st.rerun()
        
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  

@st.cache_data(show_spinner=False)
def data2consolidacion(data):
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        barmanpre        = "|".join(data['barmanpre'].unique())
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        polygon          = unary_union(data['geometry'].to_list())
        data             = pd.DataFrame([{'geometry':polygon}])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A'
        urllink          = f"http://www.urbex.com.co/Cabida?code={barmanpre}&token={st.session_state.token}"
        data['popup']    = f'''
        <!DOCTYPE html>
        <html>
            <body>
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                    <a href="{urllink}" target="_blank" style="color: black;">
                        Ver cabida lote
                    </a>
                </div>
            </body>
        </html>
        '''
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def data2geopandas(data,seleccion=[],color=None):
    
    urlexport = "http://www.urbex.com.co/Cabida"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A'
        if isinstance(color, str): data['color'] = color #  '#5A189A','#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
                        
            buildinfinfo     = ""
            infoprecuso      = ""
                
            urllink = ""
            barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?code={barmanpre}&token={st.session_state.token}"
                
            if 'infoByprecuso' in items: 
                itemsu      = items['infoByprecuso'][0]
                infoprecuso = ""
                try:    infoprecuso += f"""<b> Dirección:</b> {itemsu['formato_direccion']}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Barrio:</b> {itemsu['prenbarrio']}<br>  """
                except: pass
                try:    infoprecuso += f"""<b> Área construida total:</b> {round(itemsu['preaconst_total'],2)}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Área de terreno:</b> {round(itemsu['preaterre_total'],2)}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Estrato:</b> {int(itemsu['estrato'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Pisos:</b> {int(itemsu['connpisos'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Antiguedad:</b> {int(itemsu['prevetustzmin'])}<br>"""
                except: pass            
                try:    infoprecuso += f"""<b> Total de matriculas:</b> {int(itemsu['predios_total'])}<br> """
                except: pass                    

                for witer in items['infoByprecuso']:
                    hmtl_paso = ""
                    if witer['usosuelo'] is not None and not pd.isnull(witer['usosuelo']):
                        hmtl_paso += f"<b> Uso del suelo:</b> {witer['usosuelo']}<br>"
                    if witer['predios_precuso'] is not None and not pd.isnull(witer['predios_precuso']):
                        hmtl_paso += f"<b> Predios:</b> {witer['predios_precuso']}<br> "
                    
                    if hmtl_paso!="":
                        infoprecuso += f"""
                        <b><br>
                        {hmtl_paso}
                        """
                    try:
                        infoprecuso += f"""
                        <b> Área: </b>{witer['preaconst_precuso']/witer['preaconst_total']:,.1%}<br>
                        """
                    except: pass
            
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {infoprecuso}
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
def direccion2barmanpre(direccion):
    barmanpre = None
    if direccion is not None and direccion!="" and isinstance(direccion,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"coddir='{coddir(direccion)}'"
        data     = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            barmanpre = data['barmanpre'].iloc[0]
        engine.dispose()
    return barmanpre

@st.cache_data(show_spinner=False)
def matricula2chip(matricula):
    chip = None
    if matricula is not None and matricula!="" and isinstance(matricula,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
        matriculah1 = re.sub('[^0-9a-zA-Z]','',matricula)
        matriculah2 = re.sub('[^0-9a-zA-Z]','',matricula).lstrip('0')
        matriculah3 = re.sub('[^0-9a-zA-Z]','',matricula).lstrip('0')[3:]
        query = f" matriculainmobiliaria IN ('0{matricula.replace('-','')}','{matricula.replace('-','')}','{matricula}','{matricula.split('-')[-1]}','{matriculah1}','{matriculah2}','{matriculah3}')"
        data     = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
        if not data.empty:
            chip = data['chip'].iloc[0]
        engine.dispose()
    return chip

@st.cache_data(show_spinner=False)
def confirmeChip(chip):
    result = None
    if chip is not None and chip!="" and isinstance(chip,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"prechip='{chip}'"
        data     = pd.read_sql_query(f"SELECT prechip FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            result = data['prechip'].iloc[0]
        engine.dispose()
    return result

@st.cache_data(show_spinner=False)
def coddir2barmanpre(fcoddir):
    barmanpre = None
    query     = ""
    if isinstance(fcoddir,str) and fcoddir!="":
        query = f"coddir='{fcoddir}'"
    if isinstance(fcoddir,list):
        query = "','".join(fcoddir)
        query = f" coddir IN ('{query}')" 

    if query!="":
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
        if not data.empty:
            barmanpre = data['barmanpre'].iloc[0]
        engine.dispose()
    return barmanpre

@st.cache_data(show_spinner=False)
def buildinglist():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query("SELECT nombre_conjunto,coddir FROM  bigdata.bogota_nombre_conjuntos " , engine)
    engine.dispose()
    data = data[~data['nombre_conjunto'].str.contains(r'^\d+$')]
    data = pd.concat([pd.DataFrame([{'nombre_conjunto':'','coddir':''}]),data])
    return data 

def style_function_lineado(feature):
    return {
        'fillColor': '#fff',
        'color': 'blue',
        'weight': 2,
        'dashArray': '3, 3'
    }

if __name__ == "__main__":
    main()
