import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
import shapely.wkt as wkt
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from datetime import datetime

from display.stylefunctions  import style_function_geojson

from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon
from functions._principal_getdatanalisis import main as getdatanalitycs

from display._principal_estudio_mercado import main as generar_html

from data.tracking import savesearch

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_estudio_mercado':None,
               'reporte_estudio_mercado':False,
               'data_lotes_busqueda': pd.DataFrame(),
               'geojson_data_estudio_mercado':None,
               'zoom_start_data_estudio_mercado':12,
               'latitud_estudio_mercado':4.652652, 
               'longitud_estudio_mercado':-74.077899,
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
    # Busqueda por direccion   
    col1,col2,col3,col4,col5 = st.columns([0.3,0.15,0.3,0.15,0.1],vertical_alignment='center')
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
            st.session_state.latitud_estudio_mercado,st.session_state.longitud_estudio_mercado = getlatlng(f'{direccion},{ciudad.lower()},colombia')
            st.session_state.polygon_estudio_mercado      = circle_polygon(metros,st.session_state.latitud_estudio_mercado,st.session_state.longitud_estudio_mercado)
            st.session_state.geojson_data_estudio_mercado = mapping(st.session_state.polygon_estudio_mercado)
            st.session_state.zoom_start_data_estudio_mercado = 16
            st.rerun()
    st.markdown('<div style="padding: 30px;"></div>', unsafe_allow_html=True)
    
    #-------------------------------------------------------------------------#
    # Formulario      
    col1,col2 = st.columns([0.15,0.85])      
    with col1: 
        datauso       = usosuelo_class()
        
        #lista        = ['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero']
        datauso   = usosuelo_class()
        lista     = list(sorted(datauso['clasificacion'].unique()))
        lista     = ['Todos']+lista
        seleccion = st.multiselect('Tipo de inmueble(s)', options=lista,default=['Todos'], placeholder='Selecciona uno o varios inmuebles')
        
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

        areamin       = st.number_input('Área construida mínima',value=0,min_value=0)
        areamax       = st.number_input('Área construida máxima',value=0,min_value=0)
        estratomin    = st.number_input('Estrato mínima',value=0,min_value=0)
        estratomax    = st.number_input('Estrato máximo',value=0,min_value=0)
        antiguedadmin = st.number_input('Año de construido desde (yyyy)',value=0,min_value=0)
        antiguedadmax = st.number_input('Año de construido hasta (yyyy)',value=datetime.now().year,min_value=0)

        inputvar = {
            'tipoinmueble':seleccion,
            'areamin':areamin,
            'areamax':areamax,
            'antiguedadmin':antiguedadmin,
            'antiguedadmax':antiguedadmax,
            'desde_antiguedad':antiguedadmin,
            'hasta_antiguedad':antiguedadmax,
            'estratomin':estratomin,
            'estratomax':estratomax,
            'precuso':precuso,
            'polygon':str(st.session_state.polygon_estudio_mercado)
                    }
        
    #-------------------------------------------------------------------------#
    # Mapa
    if st.session_state.reporte_estudio_mercado is False:
    
        with col2:
            m = folium.Map(location=[st.session_state.latitud_estudio_mercado, st.session_state.longitud_estudio_mercado], zoom_start=st.session_state.zoom_start_data_estudio_mercado,tiles="cartodbpositron")
            
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
            
            if st.session_state.geojson_data_estudio_mercado is not None:
                folium.GeoJson(st.session_state.geojson_data_estudio_mercado, style_function=style_function_color).add_to(m)
    
            st_map = st_folium(m,width=int(mapwidth*0.6),height=700,key=st.session_state.mapkey)

            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                                      = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_estudio_mercado         = Polygon(coordenadas[0])
                        st.session_state.geojson_data_estudio_mercado    = mapping(st.session_state.polygon_estudio_mercado)
                        polygon_shape                                    = shape(st.session_state.geojson_data_estudio_mercado)
                        centroid                                         = polygon_shape.centroid
                        st.session_state.latitud_estudio_mercado         = centroid.y
                        st.session_state.longitud_estudio_mercado        = centroid.x
                        st.session_state.zoom_start_data_estudio_mercado = 16
                        st.rerun()

        colb1,colb2,colb3 = st.columns([0.15,0.15,0.7])  
        with colb1:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
                        
        if st.session_state.polygon_estudio_mercado is not None:
            with colb2:
                if st.button('Buscar'):
                    st.session_state.reporte_estudio_mercado = True
                    _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_modulo_analisis_estudio_mercado', inputvar)
                    st.rerun()

    elif st.session_state.reporte_estudio_mercado:
        output,data_lote,data_geometry,latitud,longitud, polygon = getdatanalitycs(grupo=None, polygon=str(st.session_state.polygon_estudio_mercado), inputvar=inputvar)
        
        try: polygon = wkt.loads(polygon)
        except: pass
    
        with col1: 
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
                        
        with col2:
            htmlrender = generar_html(None,output,datageometry=data_geometry,latitud=latitud,longitud=longitud,polygon=polygon,metros=500)
            st.components.v1.html(htmlrender, height=5000, scrolling=True)

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }
