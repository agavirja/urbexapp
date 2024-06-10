import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from shapely.geometry import Point
from streamlit_js_eval import streamlit_js_eval

from data.getpropertiesbyID import main as getpropertiesbyID

from display.stylefunctions  import style_function_geojson

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
               'data':pd.DataFrame(),
               'dataprocesos':pd.DataFrame(),
               'show_brand_map':False,
               'show_owner_map':False,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
    latitud   = 4.652652 
    longitud  = -74.077899
    col1,col2 = st.columns(2)
    with col1:
        seleccion = st.selectbox('Busqueda por:',options=['Por ID del propietario','Por nombre del propietario'])
    
    if 'Por ID del propietario' in seleccion:  
        st.session_state.show_brand_map = False
        col1,col2 = st.columns(2)
        with col1:
            tipodocumento  = st.selectbox('Tipo de documento',options=['','C.C.', 'N.I.T.', 'C.E.', 'PASAPORTE', 'T.I.'])
        with col1:
            identificacion = st.text_input('Número de documento',value='')
              
        with col1:
            inputvar = {'tipodocumento':tipodocumento, 'identificacion':identificacion,'titular':''}
            if st.button('Buscar'):
                with st.spinner('Buscando data'):
                    st.session_state.data,st.session_state.dataprocesos = getpropertiesbyID(inputvar)
                    st.session_state.show_owner_map = True
                    st.rerun()
                    
    elif 'Por nombre del propietario' in seleccion:
        st.session_state.show_brand_map = False
        with col1:
            titular = st.text_input('Nombre del titular',value='')
        inputvar = {'tipodocumento':'', 'identificacion':'','titular':titular}
        with col1:
            if st.button('Buscar'):
                with st.spinner('Buscando data'):
                    st.session_state.data,st.session_state.dataprocesos = getpropertiesbyID(inputvar)
                    st.session_state.show_owner_map = True
                    st.rerun()

    if st.session_state.show_owner_map and not st.session_state.data.empty:
        display_owner_map(st.session_state.data,latitud,longitud,mapwidth,mapheight)
    elif st.session_state.show_owner_map and st.session_state.data.empty:
        st.error('No se encontró información de predios')
    

def display_owner_map(data,latitud,longitud,mapwidth,mapheight):
    if not data.empty:
        #---------------------------------------------------------------------#
        # Mapa de transacciones en el radio
        m = folium.Map(location=[latitud, longitud], zoom_start=12,tiles="cartodbpositron")
        geojson = data2geopandas_owner(data)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
        geopoints = point2geopandas_owner(data)
        folium.GeoJson(geopoints).add_to(m)
        st_map = st_folium(m,width=mapwidth,height=mapheight)
    else:
        st.error('No se encontró información de predios')
        
@st.cache_data(show_spinner=False)
def data2geopandas_owner(data):
    
    geojson = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color'] = '#5A189A'    
        data['popup'] = None
        data.index    = range(len(data))
        for idd,items in data.iterrows():
            try:    titular = f"<b> titular:</b> {items['titular']}<br>"
            except: titular = "<b> titular:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['predirecc']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>" 
            try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>"
            except: barrio = "<b> Barrio:</b> Sin información <br>" 
            try:    fecha = f"<b> Fecha del documento:</b> {items['fecha_documento_publico']}<br>"
            except: fecha = "" 
           
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="http://localhost:8501/Busqueda_avanzada?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}" target="_blank" style="color: black;">
                            {titular}
                            {direccion}
                            {barrio}
                            {fecha}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        variables = [x for x in ['color','popup','geometry'] if x in data]
        data      = data[variables]
        geojson   = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def point2geopandas_owner(data):
    
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data      = data[['geometry']]
        geojson   = data.to_json()
        
    return geojson

if __name__ == "__main__":
    main()