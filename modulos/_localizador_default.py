import streamlit as st
import copy
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,Point,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from data.getdataBrands import getoptions,getdatabrans
from data.getpropertiesbyID import main as getpropertiesbyID

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
    
    formato = {
               'data':pd.DataFrame(),
               'dataprocesos':pd.DataFrame(),
               'show_brand_map':False,
               'show_owner_map':False,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    style()
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
    latitud   = 4.652652 
    longitud  = -74.077899
    col1,col2 = st.columns(2)
    with col1:
        seleccion = st.selectbox('Busqueda por:',options=['Por segmento de negocio, marca o establecimiento','Por ID del propietario','Por nombre del propietario'])
    
    if 'Por segmento de negocio, marca o establecimiento' in seleccion:
        st.session_state.show_owner_map = False
        with col1:
            dataoptions = getoptions()
            tipomarca   = st.selectbox('Busqueda por:',options=sorted(list(dataoptions['label'].unique())))
            idxlabel    = dataoptions[dataoptions['label']==tipomarca]['idxlabel'].iloc[0]
            inputvar    = {'mpio_ccdgo':'11001','idxlabel':idxlabel}
            if st.button('Buscar'):
                with st.spinner('Buscando data'):
                    st.session_state.data           = getdatabrans(inputvar)
                    st.session_state.show_brand_map = True
                    st.rerun()
                    
    elif 'Por ID del propietario' in seleccion:  
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

    if st.session_state.show_brand_map and not st.session_state.data.empty:
        display_brand_map(st.session_state.data,latitud,longitud,mapwidth,mapheight)
    
    elif st.session_state.show_owner_map and not st.session_state.data.empty:
        display_owner_map(st.session_state.data,latitud,longitud,mapwidth,mapheight)

    
def display_brand_map(data,latitud,longitud,mapwidth,mapheight):

    data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty:
        label = data['label'].iloc[0]
        col1, col2, col3, col4, col5 = st.columns(5)
        
        options    = list(data['empresa'].unique())
        isdisabled = True
        if len(options)>1:
            options    = ['Todas'] + options
            isdisabled = False
        with col1:
            empresa = st.selectbox('Filtro por marca', options=options, disabled=isdisabled)
            if 'Todas' not in empresa:
                data = data[data['empresa']==empresa]
        with col2:
            options = ['Todas']+list(data[data['nombre'].notnull()]['nombre'].unique())
            nombre = st.selectbox(f'{label}', options=options)
            if 'Todas' not in nombre:
                data = data[data['nombre']==nombre]
        with col3:
            options = ['Todos']+list(data[data['prenbarrio'].notnull()]['prenbarrio'].unique())
            barrio = st.selectbox('Barrio', options=options)
            if 'Todos' not in barrio:
                data = data[data['prenbarrio']==barrio]
        with col4:
            options   = list(data[data['direccion'].notnull()]['direccion'].unique())+ list(data[data['predirecc'].notnull()]['predirecc'].unique())
            options   = ['Todas']+options
            direccion = st.selectbox('Dirección', options=options)
            if 'Todas' not in direccion:
                idd  = (data['direccion']==direccion) | (data['predirecc']==direccion)
                data = data[idd]
        with col5:
            id_trans = st.selectbox('Transacciones', options=['Todo','Si'])
            if 'Si' in id_trans:
                data = data[data['fuente']=='snr']

        #---------------------------------------------------------------------#
        # Mapa
        m = folium.Map(location=[latitud, longitud], zoom_start=12,tiles="cartodbpositron")
        geojson = data2geopandas_brand(data)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
        
        geopoints = geopoint_brand(data)
        #marker = folium.Circle(radius=4)
        #marker = folium.Marker(icon=folium.Icon(
        #                             icon_color='#ff033e',
        #                             icon_size='certificate',
        #                             prefix='fa'))
        #folium.GeoJson(geopoints,style_function=style_function_geojson22,marker=marker).add_to(m)
        for _,items in data.iterrows():
            icon = folium.features.CustomIcon(
                icon_image = items["marker"],
                icon_size  = (15, 15),
            )
            folium.Marker(location=[items["latitud"], items["longitud"]], icon=icon).add_to(m)
        
        st_map = st_folium(m,width=mapwidth,height=mapheight)

@st.cache_data(show_spinner=False)
def data2geopandas_brand(data):
    
    geojson = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color'] = '#B20256'    
        data['popup'] = None
        data.index    = range(len(data))
        for idd,items in data.iterrows():
            try:    empresa = f"<b> Empresa:</b> {items['empresa']}<br>"
            except: empresa = "<b> Empresa:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>" 
            try:    nombre = f"<b> Nombre:</b> {items['nombre']}<br>"
            except: nombre = "<b> Nombre:</b> Sin información <br>" 
            try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>"
            except: barrio = "<b> Barrio:</b> Sin información <br>"      
            
            urlexport = "http://localhost:8501/Busqueda_avanzada"
            urllink   = urlexport+f"?type=predio&code={items['lotcodigo']}&vartype=barmanpre&token={st.session_state.token}"

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {empresa}
                            {direccion}
                            {nombre}
                            {barrio}
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

#@st.cache_data(show_spinner=False)
def geopoint_brand(data):
    geojson = pd.DataFrame().to_json()
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data             = data[['geometry','marker']]
        data['color']    = 'black'
        geojson          = data.to_json()
    return geojson

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

@st.cache_data(show_spinner=False)
def data2geopandas_owner(data):
    
    geojson = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color'] = '#B20256'    
        data['popup'] = None
        data.index    = range(len(data))
        for idd,items in data.iterrows():
            try:    titular = f"<b> Empresa:</b> {items['titular']}<br>"
            except: titular = "<b> Empresa:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['predirecc']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>" 
            try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>"
            except: barrio = "<b> Barrio:</b> Sin información <br>" 
            try:    fecha = f"<b> Fecha del documento:</b> {items['fecha_documento_publico']}<br>"
            except: fecha = "<b> Fecha del documento:</b> Sin información <br>" 
           
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="http://localhost:8501/Due_dilligence_digital?code={items['barmanpre']}&variable=barmanpre" target="_blank" style="color: black;">
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

@st.cache_data
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

def style():
    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #3C3840;        
            opacity: 1;
            background-size: cover;
        }}
    
        header {{
            visibility: hidden; 
            height: 0%;
            }}
        
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-white.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="stToolbar"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stDecoration"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stStatusWidget"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: 14px;
            font-weight: bold;
            color: #05edff;
            font-family: 'Roboto', sans-serif;
        }}
                
        span[data-baseweb="tag"] {{
          background-color: #007bff;
        }}
        
        .stButton button {{
                background-color: #05edff;
                font-weight: bold;
                width: 100%;
                border: 2px solid #05edff;
                
            }}
        
        .stButton button:hover {{
            background-color: #05edff;
            color: black;
            border: #05edff;
        }}
        
        div[data-testid="stSpinner"] {{
            color: #fff;
            }}
        
        [data-testid="stNumberInput"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stMultiSelect"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px; 
            padding: 5px;
        }}
        
        [data-testid="stMultiSelect"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stSelectbox"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;

        }}
        
        </style>
        """,
        unsafe_allow_html=True
    )
        
if __name__ == "__main__":
    main()
