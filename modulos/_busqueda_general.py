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
from datetime import datetime

from display.stylefunctions  import style_function_geojson

from functions._principal_getdatalotes import main as getdatalotes
from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon

from data.tracking import savesearch,update_save_status

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_default':None,
               'reporte_busqueda_default':False,
               'data_lotes_busqueda': pd.DataFrame(),
               'geojson_data_busqueda_default':None,
               'zoom_start_data_busqueda_default':12,
               'latitud_busqueda_default':4.652652, 
               'longitud_busqueda_default':-74.077899,
               'barmanpre_ref':[],
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
    # Guardar la consulta 
    if isinstance(st.session_state.token,str) and st.session_state.token!='' and isinstance(st.session_state.id_consulta,int):
        colf1,colf2,colf3 = st.columns([0.66,0.24,0.1])
        with colf2:
            if st.session_state.favorito is False:
                on = st.toggle('Guardar en favoritos',False)
                if on:
                    with st.spinner('Guardando'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,1):
                            st.session_state.favorito = True
                            st.rerun()
            if st.session_state.favorito:
                on = st.toggle('Guardado',True)
                if on is False:
                    with st.spinner('Removiendo'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,0):
                            st.session_state.favorito = False
                            st.rerun()
                            
    #-------------------------------------------------------------------------#
    # Busqueda por direccion 
    if screensize>1280:
        col1,col2,col3,col4,col5 = st.columns([0.3,0.15,0.3,0.15,0.1],vertical_alignment='center')
    else:
        col1, col2, col3 = st.columns([0.4,0.2,0.4],vertical_alignment='center')
        col4, col5 = st.columns([0.4,0.6],vertical_alignment='center')
    
    with col1:
        tipobusqueda = st.selectbox('Ubicación por:',options=['Dirección','Nombre de la copropiedad'])
    with col2:
        ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
    with col3:
        direccion = st.text_input('Dirección:',value='')   
    with col4:
        metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=0)   
    with col5:
        disabled = False if isinstance(direccion,str) and direccion!='' and metros<=500 else True
        if st.button('Ubicar en el mapa',disabled=disabled):
            st.session_state.latitud_busqueda_default,st.session_state.longitud_busqueda_default, st.session_state.barmanpre_ref = getlatlng(f'{direccion},{ciudad.lower()},colombia')
            st.session_state.polygon_busqueda_default         = circle_polygon(metros,st.session_state.latitud_busqueda_default,st.session_state.longitud_busqueda_default)
            st.session_state.geojson_data_busqueda_default    = mapping(st.session_state.polygon_busqueda_default)
            st.session_state.zoom_start_data_busqueda_default = 16
            st.rerun()
    st.markdown('<div style="padding: 30px;"></div>', unsafe_allow_html=True)

    #-------------------------------------------------------------------------#
    # Formulario      
    col1,col2 = st.columns([0.3,0.7])      
    with col1: 
        
        #lista        = ['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero']
        lista         = list(sorted(datauso['clasificacion'].unique()))
        lista         = ['Todos'] + lista
        
        seleccion     = st.multiselect('Tipo de inmueble(s)', key='seleccion',options=lista, default=['Todos'],placeholder='Selecciona uno o varios inmuebles')
        areamin       = st.number_input('Área construida mínima',value=0,min_value=0)
        areamax       = st.number_input('Área construida máxima',value=0,min_value=0)
        estratomin    = st.number_input('Estrato mínima',value=0,min_value=0)
        estratomax    = st.number_input('Estrato máximo',value=0,min_value=0)
        antiguedadmin = st.number_input('Año de construido desde (yyyy)',value=0,min_value=0)
        antiguedadmax = st.number_input('Año de construido hasta (yyyy)',value=datetime.now().year,min_value=0)

    #-------------------------------------------------------------------------#
    # Mapa
    with col2:
        m = folium.Map(location=[st.session_state.latitud_busqueda_default, st.session_state.longitud_busqueda_default], zoom_start=st.session_state.zoom_start_data_busqueda_default,tiles="cartodbpositron")
        
        if st.session_state.data_lotes_busqueda.empty:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
        if st.session_state.geojson_data_busqueda_default is not None:
            folium.GeoJson(st.session_state.geojson_data_busqueda_default, style_function=style_function_color).add_to(m)

        if not st.session_state.data_lotes_busqueda.empty:
            geojson = data2geopandas(st.session_state.data_lotes_busqueda, st.session_state.barmanpre_ref)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
        if st.session_state.data_lotes_busqueda.empty:
            st_map = st_folium(m,width=int(mapwidth*0.6),height=700,key=st.session_state.mapkey)

            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                                       = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_busqueda_default         = Polygon(coordenadas[0])
                        st.session_state.geojson_data_busqueda_default    = mapping(st.session_state.polygon_busqueda_default)
                        polygon_shape                                     = shape(st.session_state.geojson_data_busqueda_default)
                        centroid                                          = polygon_shape.centroid
                        st.session_state.latitud_busqueda_default         = centroid.y
                        st.session_state.longitud_busqueda_default        = centroid.x
                        st.session_state.zoom_start_data_busqueda_default = 16
                        st.rerun()
        else:
            folium_static(m,width=int(mapwidth*0.6),height=700)
            
    col1,col2,col3 = st.columns([0.15,0.15,0.7],vertical_alignment='center')  
    cols1,cols2    = st.columns([0.3,0.7])
    with col1:
        if st.button('Resetear'):
            
            variable_reset = formato.copy()
            del variable_reset['token']
            for key,value in variable_reset.items():
                del st.session_state[key]
            st.rerun()
                    
    if st.session_state.polygon_busqueda_default is not None:
        with col2:
            if st.button('Buscar'):
                inputvar = {
                    'tipoinmueble':seleccion,
                    'areamin':areamin,
                    'areamax':areamax,
                    'antiguedadmin':antiguedadmin,
                    'antiguedadmax':antiguedadmax,
                    'estratomin':estratomin,
                    'estratomax':estratomax,
                    'polygon':str(st.session_state.polygon_busqueda_default)
                    }
                with cols1:
                    with st.spinner('Buscando informacion'):
                        st.session_state.data_lotes_busqueda = getdatalotes(inputvar=inputvar)
                        st.session_state.reporte_busqueda_default = True
                
                # Guardar:
                _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_busqueda_general', inputvar)
                st.rerun()
                
    if st.session_state.reporte_busqueda_default and st.session_state.data_lotes_busqueda.empty:
        with col3:
            st.error('No se encontraron predios que cumplen con las características')

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }


@st.cache_data(show_spinner=False)
def data2geopandas(data, barmanpre_ref=None):
    
    data      = getitems(data)
    urlexport = "http://www.urbex.com.co/Reporte"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
        
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        
        if isinstance(barmanpre_ref,list) and barmanpre_ref!=[] and 'barmanpre' in data:
            idd = data['barmanpre'].isin(barmanpre_ref)
            if sum(idd)>0:
                data.loc[idd,'color'] = '#003F2D'
            
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
                        <a href="{urllink}" target="_blank" style="color: black; text-decoration: none;">
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
