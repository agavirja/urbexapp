import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval

from data.circle_polygon import circle_polygon
from data.getlatlng import getlatlng

from display.stylefunctions  import style_function

from data.reporte_analisis_mercado import main as reporte_analisis_mercado
from data.getuso_destino import usosuelo_class

import pandas as pd

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
    direccion = None
    metros    = 500
    
    formato = {
               'latitud':4.652652,
               'longitud':-74.077899,
               'zoom_start':12,
               'polygon_am':None,
               'showmap_radio_am':False,
               'showresult_am':False,
               'usosuelo':[],
               'segmento':None,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
     
    col1,col2   = st.columns(2)
    colo1,colo2 = st.columns(2)
    colm1,colm2,colm3 = st.columns([0.025,0.95,0.025])
    colz1,colz2 = st.columns(2)
    
    with st.spinner('Buscando información'):
        datausosuelo = usosuelo_class()
        
    if st.session_state.showresult_am is False:
        
        with col1:
            seleccion = st.selectbox('Seleccione la forma de segmentar geográficamente',options=['poligono','radio'])
            st.session_state.segmento = seleccion

        if 'radio' in seleccion:

            with col2: 
                formato_select = st.selectbox('Seleccionar el punto central',options=['dirección','latitud y longitud'])
                
            if 'latitud y longitud' in formato_select:
                with colo1:
                    latitud_s = st.number_input('Latitud:',value=0.00000,step=1.00000)
                    if latitud_s>0 or latitud_s<0: st.session_state.latitud = latitud_s
                with colo2:
                    longitud_s = st.number_input('Longitud:',value=0.00000,step=1.00000)
                    if longitud_s>0 or longitud_s<0: st.session_state.longitud = longitud_s
                with colo2:
                    if (latitud_s>0 or latitud_s<0) and (longitud_s>0 or longitud_s<0):
                        if st.button('Ubicar en el mapa'):
                            st.session_state.showmap_radio_am = True
                    
            if 'dirección' in formato_select:
                with colo1:
                    ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
                with colo2:
                    direccion = st.text_input('Dirección:',value='')   
        
        with colo1:
            options = list(sorted(datausosuelo['clasificacion'].unique()))
            options = ['Todos']+options           
            clasificacion = st.selectbox('Segmento:',options=options)

        with colo2:
            options = list(sorted(datausosuelo['usosuelo'].unique()))
            options = ['Todos']+options
                                   
            if 'todo' not in clasificacion.lower():
                options = list(sorted(datausosuelo[datausosuelo['clasificacion']==clasificacion]['usosuelo'].unique()))
                options = ['Todos']+options
            tiposeleccion = st.multiselect('Uso del suelo:',options=options)
            
        if 'todo' not in clasificacion.lower():
            datausosuelo = datausosuelo[datausosuelo['clasificacion']==clasificacion]
        
        if isinstance(tiposeleccion,list) and tiposeleccion!=[] and not any([x for x in tiposeleccion if 'todo' in x.lower()]):
            datausosuelo = datausosuelo[datausosuelo['usosuelo'].isin(tiposeleccion)]
        
        st.session_state.usosuelo = list(datausosuelo['precuso'].unique())
        if 'todo' in clasificacion.lower() and (any([x for x in tiposeleccion if 'todo' in x.lower()]) or tiposeleccion==[]):
            st.session_state.usosuelo = []
            
        with colo1:
            if isinstance(direccion, str) and direccion!='' and st.session_state.polygon_am is None:
                if st.button('Ubicar en el mapa'):
                    with st.spinner('Buscando dirección'):
                        st.session_state.latitud,st.session_state.longitud = getlatlng(f'{direccion},{ciudad.lower()},colombia')
                        st.session_state.zoom_start = 16
                        st.session_state.showmap_radio_am = True
        #-------------------------------------------------------------------------#
        # Mapa
        m = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        if 'poligono' in seleccion:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
            
            if st.session_state.polygon_am is not None:
                folium.GeoJson(mapping(st.session_state.polygon_am), style_function=style_function).add_to(m)
    
        if st.session_state.showmap_radio_am:
            st.session_state.polygon_am = circle_polygon(metros,st.session_state.latitud,st.session_state.longitud)
            folium.GeoJson(mapping(st.session_state.polygon_am), style_function=style_function_color).add_to(m)
    
        with colm2:
            st_map = st_folium(m,width=mapwidth,height=mapheight)
        
        if 'poligono' in seleccion:
            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                       = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_am       = Polygon(coordenadas[0])
                        geojson_data_estudiomercado       = mapping(st.session_state.polygon_am)
                        polygon_shape                     = shape(geojson_data_estudiomercado)
                        centroid                          = polygon_shape.centroid
                        st.session_state.latitud          = centroid.y
                        st.session_state.longitud         = centroid.x
                        st.session_state.zoom_start       = 16
                        st.session_state.showmap_radio_am = False
                        st.rerun()
                 
        #-------------------------------------------------------------------------#
        # Buscar data
        if st.session_state.polygon_am is not None:  
            with colz1:
                if st.button('Buscar'):
                    with st.spinner('Buscando información'):
                        st.session_state.showresult_am = True
                        st.rerun()
        with colz2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
    
    if st.session_state.showresult_am:
        polygon = str(st.session_state.polygon_am) if st.session_state.polygon_am is not None else ''
        reporte_analisis_mercado(polygon=polygon,precuso=st.session_state.usosuelo,maxmetros=metros,tipo=st.session_state.segmento)
        
        col1,col2 = st.columns(2)
        with col1:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()     

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }
