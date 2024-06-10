import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval

from data.circle_polygon import circle_polygon
from data.getlatlng import getlatlng

from display.stylefunctions  import style_function

from data.data_estudio_mercado_general import main as  data_estudio_mercado_general

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
    direccion = None
    metros    = 500
    
    formato = {
               'latitud':4.652652,
               'longitud':-74.077899,
               'zoom_start':12,
               'polygon_emg':None,   # Poligono Estudio de Mercado General
               'showmap_radio_em':False,
               'polygon_emg_search':None,
               'showresult_emg':False,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
     
    if st.session_state.showresult_emg is False:
        col1, col2  = st.columns(2)
        with col1:
            seleccion = st.selectbox('Seleccione la forma de segmentar geográficamente',options=['radio','poligono'])
        
        if 'radio' in seleccion:
            with col2: 
                formato_select = st.selectbox('Seleccionar el punto central',options=['dirección','lat-long'])
            
            col1, col2  = st.columns(2)
            if 'lat-long' in formato_select:
                with col1:
                    latitud_s = st.number_input('Latitud:',value=0.00000,step=1.00000)
                    if latitud_s>0 or latitud_s<0: st.session_state.latitud = latitud_s
                with col2:
                    longitud_s = st.number_input('Longitud:',value=0.00000,step=1.00000)
                    if longitud_s>0 or longitud_s<0: st.session_state.longitud = longitud_s
                with col1:
                    metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=4)
                with col2:
                    st.write('')
                    st.write('')
                    st.write('')
                    if (latitud_s>0 or latitud_s<0) and (longitud_s>0 or longitud_s<0):
                        if st.button('Ubicar en el mapa'):
                            st.session_state.showmap_radio_em = True
                    
            if 'dirección' in formato_select:
                with col1:
                    ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
                with col2:
                    direccion = st.text_input('Dirección:',value='')
                with col1:
                    metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=4)
                with col2:
                    st.write('')
                    st.write('')
                    st.write('')
                    if isinstance(direccion, str) and direccion!='':
                        if st.button('Ubicar en el mapa'):
                            with st.spinner('Buscando dirección'):
                                st.session_state.latitud,st.session_state.longitud = getlatlng(f'{direccion},{ciudad.lower()},colombia')
                                st.session_state.zoom_start = 16
                                st.session_state.showmap_radio_em = True
    
        #-------------------------------------------------------------------------#
        # Mapa
        m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        if 'poligono' in seleccion:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
            
            if st.session_state.polygon_emg is not None:
                folium.GeoJson(mapping(st.session_state.polygon_emg), style_function=style_function).add_to(m)
    
        if st.session_state.showmap_radio_em:
            st.session_state.polygon_emg  = circle_polygon(metros,st.session_state.latitud,st.session_state.longitud)
            folium.GeoJson(mapping(st.session_state.polygon_emg), style_function=style_function_color).add_to(m)
    
        st_map = st_folium(m,width=mapwidth,height=mapheight)
        
        if 'poligono' in seleccion:
            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                       = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_emg      = Polygon(coordenadas[0])
                        geojson_data_estudiomercado       = mapping(st.session_state.polygon_emg)
                        polygon_shape                     = shape(geojson_data_estudiomercado)
                        centroid                          = polygon_shape.centroid
                        st.session_state.latitud          = centroid.y
                        st.session_state.longitud         = centroid.x
                        st.session_state.zoom_start       = 16
                        st.session_state.showmap_radio_em = False
                        st.rerun()
                    
        colk1,colk2 = st.columns(2)
        if st.session_state.polygon_emg is not None:
            with colk1:
                if st.button('Buscar'):
                    st.session_state.showresult_emg     = True
                    st.session_state.polygon_emg_search = None
                    if 'poligono' in seleccion:
                        st.session_state.polygon_emg_search = str(st.session_state.polygon_emg)
                    
            with colk2:
                if st.button('Resetear búsqueda'):
                    for key,value in formato.items():
                        del st.session_state[key]
                    st.rerun()
            
    if st.session_state.showresult_emg:
        colz1,colz2 = st.columns(2)
        with colz1:
            if st.button(' Resetear búsqueda '):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
        data_estudio_mercado_general(code=None,polygon=st.session_state.polygon_emg_search,latitud=st.session_state.latitud,longitud=st.session_state.longitud,precuso=None,metros_default=metros)
        
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

if __name__ == "__main__":
    main()
