import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval

from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.dataheatmap  import main as dataheatmap, selectpolygon
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
    
    style()
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Variables 
    initialformat = {
               'polygon_busquedavanzada':None,
               'geojson_data':None,
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               }
    
    for key,value in initialformat.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1, col2 = st.columns([0.2,0.8])
    with col1:
        year    = st.selectbox('Año:',options=['Todos',2024,2023,2022,2021,2020])
        formato = st.selectbox('Segmentación:',options=['Cuadrantes','Barrios'])
        if 'Cuadrantes' in formato: formato = 'grid'
        elif 'Barrios'  in formato: formato = 'barrios'
        
    with col2:
        with st.spinner('Buscando información'):
            data = dataheatmap(year=year,formato=formato)
            
    usosuelo = None
    if not data.empty:
        with col1:
            tipoinmueble = st.selectbox('Tipo de inmueble:',options=['Todos','Apartamento', 'Bodega', 'Casa', 'Hotel', 'Local','Oficina'])
            if 'todo' not in tipoinmueble.lower():
                precusofilter = inmueble2usosuelo([tipoinmueble])
                data          = data[data['precuso'].isin(precusofilter)]
            
            options      = sorted(list(data['usosuelo'].unique()))
            options      = ['Todos']+options
            usosuelo     = st.selectbox('Uso del suelo:',options=options)
            tipoconsulta = st.selectbox('Tipo de busqueda:',options=['Valor transacciones','# Transacciones'])
            if 'Valor transacciones' in tipoconsulta: 
                tipoconsulta = 'valormt2_transacciones'
            elif '# Transacciones' in tipoconsulta:
                tipoconsulta = 'transacciones'
            
    if isinstance(usosuelo,str) and usosuelo!='' and 'todo' not in usosuelo.lower():
        data = data[data['usosuelo']==usosuelo]
        
    
    if st.session_state.polygon_busquedavanzada is not None:
        with st.spinner('Cargando'):
            r = selectpolygon(polygon=str(st.session_state.polygon_busquedavanzada),formato=formato)
        if isinstance(r,list):
            data = data[data['id_map'].isin(r)]
            with col1:
                if st.button('Resetear búsqueda'):
                    for key,value in initialformat.items():
                        del st.session_state[key]
                    st.rerun()
                
    # Group data
    data = datagroupby(data,tipoconsulta)
    
    #-------------------------------------------------------------------------#
    # Heat Map
    #-------------------------------------------------------------------------#
    m    = folium.Map(location=[4.652652, -74.077899], zoom_start=12,tiles="cartodbpositron") #"cartodbdark_matter"

    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)
    
    if not data.empty:
        geojson = data2geopandas(data)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    with col2:
        st_map = st_folium(m,width=mapwidth,height=800)
        
    if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
        if st_map['all_drawings']!=[]:
            if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                coordenadas                              = st_map['all_drawings'][0]['geometry']['coordinates']
                st.session_state.polygon_busquedavanzada = Polygon(coordenadas[0])
                st.session_state.geojson_data            = mapping(st.session_state.polygon_busquedavanzada)
                polygon_shape                            = shape(st.session_state.geojson_data)
                centroid                                 = polygon_shape.centroid
                st.session_state.latitud                 = centroid.y
                st.session_state.longitud                = centroid.x
                st.session_state.zoom_start              = 16
                st.rerun()
                
@st.cache_data(show_spinner=False)
def data2geopandas(data):
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            
            popuptext = ""
            try:    popuptext += f"""<b>Valor transacciones mt2:</b> ${items['valormt2_transacciones']:,.0f} m²<br>"""
            except: pass
            try:    popuptext += f"""<b>Número de transacciones:</b> {items['transacciones']}<br>"""
            except: pass
            try:
                if isinstance(items['scanombre'], str) and items['scanombre']!="":
                    popuptext += f"""<b>Barrio catastral:</b> {items['scanombre']}<br>"""
            except: pass       
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                    {popuptext}
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def datagroupby(data,tipoconsulta):
    if not data.empty:
        data['prod']  = data['transacciones']*data['valormt2_transacciones']
        data          = data.groupby('id_map').agg({'transacciones':'sum','valormt2_transacciones':'median','prod':'sum','wkt':'first','scanombre':'first'}).reset_index()
        data.columns  = ['id_map','transacciones','valormt2_transacciones','prod','wkt','scanombre']
        data['valormt2_transacciones'] = data['prod']/data['transacciones']
        data['color'] = '#5A189A'
    
    #------------------#
    # Remover Outliers #
    #if not data.empty:
    #    mean = data[tipoconsulta].mean()
    #    std  = data[tipoconsulta].std()
    #    LB   = mean-3*std
    #    UB   = mean+3*std
    #    data = data[(data[tipoconsulta]>=LB) & (data[tipoconsulta]<=UB)]

    #---------#
    # Colores #
    try:
        data['normvalue'] = data[tipoconsulta].rank(pct=True)
        cmap = plt.cm.RdYlGn # plt.cm.viridis
        data['color'] = data['normvalue'].apply(lambda x: to_hex(cmap(x)))
    except: pass
    return data

def style():
    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #fff;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #000;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-black.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="collapsedControl"] button {{
            background-color: transparent;
            border: none;
            cursor: pointer;
            padding: 0;
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
    
        #MainMenu {{
        visibility: hidden; 
        height: 0%;
        }}
        header {{
            visibility: hidden; 
            height: 0%;
            }}
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        div[data-testid="stSpinner"] {{
            color: #000000;
            }}
        
        a[href="#responsive-table"] {{
            visibility: hidden; 
            height: 0%;
            }}
        
        a[href^="#"] {{
            /* Estilos para todos los elementos <a> con href que comienza con "#" */
            visibility: hidden; 
            height: 0%;
            overflow-y: hidden;
        }}

        div[class="table-scroll"] {{
            background-color: #a6c53b;
            visibility: hidden;
            overflow-x: hidden;
            }}
            
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;

        }}
        
        [data-testid="stSelectbox"] {{
            border: 5px solid #F2F2F2;
            background-color: #F2F2F2;
            border-radius: 5px;
        }}
        
        .stButton button {{
                background-color: #5CE6A2;
                font-weight: bold;
                width: 100%;
                border: 2px solid #5CE6A2;
                
            }}
        </style>
        """,
        unsafe_allow_html=True
    )
        
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  
    