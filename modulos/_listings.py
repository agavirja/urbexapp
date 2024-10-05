import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,Point,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup

from data.data_listings import listingsPolygonActive

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
    mapwidth   = int(screensize*0.6)
    mapheight  = int(screensize*0.3)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize*0.6)
        mapheight  = int(screensize*0.3)
    except: pass
 
    if st.session_state.access:
        landing(mapwidth,mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(mapwidth,mapheight):

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_am':None,
               'data_mls':pd.DataFrame(),
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               'reporte_mls':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    col1,col2,col3 = st.columns([1,1,3])
    
    tipoinmueble    = None
    tiponegocio     = None
    areamin         = 0
    areamax         = 0
    valormin        = 0
    valormax        = 0
    habitacionesmin = 0
    habitacionesmax = 0
    banosmin        = 0
    banosmax        = 0
    garajesmin      = 0
    garajesmax      = 0

    #-------------------------------------------------------------------------#
    # Formulario  
    with col1:
        tipoinmueble = st.selectbox('Tipo de inmueble', options=['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina'])
    with col2:
        tiponegocio = st.selectbox('Tipo de negocio',options=['Venta', 'Arriendo'])
    with col1:
        areamin = st.number_input('Área mínima',value=0,min_value=0)
    with col2:
        areamax = st.number_input('Área máxima',value=0,min_value=0)
    with col1:
        valormin = st.number_input('Valor mínimo',value=0,min_value=0)
    with col2:
        valormax = st.number_input('Valor máximo',value=0,min_value=0)
            
    habitacionesmin,habitacionesmax,banosmin,banosmax,garajesmin,garajesmax = [0]*6
        
    if any([x for x in ['Apartamento','Casa'] if x in tipoinmueble]):
        with col1:
            habitacionesmin = st.selectbox('Habitaciones mínimas',options=[1,2,3,4,5,6],index=0)
        with col2:
            habitacionesmax = st.selectbox('Habitaciones máximas',options=[1,2,3,4,5,6],index=5)
        with col1:
            banosmin = st.selectbox('Baños mínimos',options=[1,2,3,4,5,6],index=0)
        with col2:
            banosmax = st.selectbox('Baños máximos',options=[1,2,3,4,5,6],index=5)       
        with col1:
            garajesmin = st.selectbox('Garajes mínimos',options=[0,1,2,3,4],index=0)
        with col2:
            garajesmax = st.selectbox('Garajes máximos',options=[0,1,2,3,4,5,6],index=6)

    #-------------------------------------------------------------------------#
    # Mapa
    
    m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
    
    if st.session_state.data_mls.empty:
        draw = Draw(
                    draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                    edit_options={"poly": {"allowIntersection": False}}
                    )
        draw.add_to(m)
    
    if st.session_state.polygon_am is not None:
        folium.GeoJson(mapping(st.session_state.polygon_am), style_function=style_function).add_to(m)

    if not st.session_state.data_mls.empty:
        geojson = data2geopandas(st.session_state.data_mls,tiponegocio=tiponegocio)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    with col3:
        if st.session_state.data_mls.empty:
        
            st_map = st_folium(m,width=mapwidth,height=mapheight)
    
            polygonType = ''
            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry']:
                        polygonType = st_map['all_drawings'][0]['geometry']['type']
                
            if 'polygon' in polygonType.lower():
                coordenadas                 = st_map['all_drawings'][0]['geometry']['coordinates']
                st.session_state.polygon_am = Polygon(coordenadas[0])
                geojson_data_mls            = mapping(st.session_state.polygon_am)
                polygon_shape               = shape(geojson_data_mls)
                centroid                    = polygon_shape.centroid
                st.session_state.latitud    = centroid.y
                st.session_state.longitud   = centroid.x
                st.session_state.zoom_start = 16
                st.rerun()
                
        if not st.session_state.data_mls.empty:
            folium_static(m,width=mapwidth,height=mapheight)

    if st.session_state.polygon_am is not None:        
        polygon = str(st.session_state.polygon_am)
        with col1:
            if st.button('Buscar'):
                with st.spinner('Buscando información'):
                    st.session_state.data_mls = listingsPolygonActive(polygon=polygon, tipoinmueble=tipoinmueble, tiponegocio=tiponegocio, areamin=areamin, areamax=areamax, valormin=valormin, valormax=valormax, habitacionesmin=habitacionesmin, habitacionesmax=habitacionesmax, banosmin=banosmin, banosmax=banosmax, garajesmin=garajesmin, garajesmax=garajesmax)
                st.session_state.reporte_mls = True
                st.rerun()

        with col2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
            
    
    if st.session_state.reporte_mls:
        with st.spinner('Buscando información de listings'):
            showlistings(st.session_state.data_mls,tiponegocio=tiponegocio)

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  
    
@st.cache_data(show_spinner=False)
def data2geopandas(data,tiponegocio=None):
    
    urlexport = "http://www.urbex.com.co/Ficha"
    geojson   = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = ''
        img_style = '''
                <style>               
                    .property-image{
                      flex: 1;
                    }
                    img{
                        width:200px;
                        height:120px;
                        object-fit: cover;
                        margin-bottom: 2px; 
                    }
                </style>
                '''
        for idd,items in data.iterrows():
            urllink = urlexport+f"?code={items['code']}&tiponegocio={items['tiponegocio'].lower()}&tipoinmueble={items['tipoinmueble'].lower()}"
    
            imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
            precio           = f"<b> Precio:</b> ${items['valor']:,.0f}<br>" if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)) else ''
            direccion        = f"<b> Dirección:</b> {items['direccion']}<br>" if 'direccion' in items and isinstance(items['direccion'], str) else ''
            valormt2         = f"<b> Valor m²:</b> ${items['valormt2']:,.0f} m²<br>" if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)) else ''
            tiponegocio      = f"<b> Tipo de negocio:</b> {items['tiponegocio']}<br>" if 'tiponegocio' in items and isinstance(items['tiponegocio'], str) else ''
            tipoinmueble     = items['tipoinmueble'] if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else None
            caracteristicas  = f"<b> Área construida:</b> {items['areaconstruida']}<br>" if 'areaconstruida' in items and (isinstance(items['areaconstruida'], float) or isinstance(items['areaconstruida'], int)) else ''
            barrio           = f"<b> Barrio:</b> {items['scanombre']}<br>"  if 'scanombre' in items and isinstance(items['scanombre'], str) else ''
            
            if any([x for x in ['apartamento','casa'] if x in tipoinmueble.lower()]):
                if all([x for x in ['habitaciones','banos','garajes'] if x in items]):
                    try:    caracteristicas = f"{items['areaconstruida']} m<sup>2</sup> | {int(float(items['habitaciones']))} H | {int(float(items['banos']))} B | {int(float(items['garajes']))} G <br>"
                    except: caracteristicas = "" 
            tipoinmueble = f"<b> Tipo de inmueble:</b> {items['tipoinmueble']}<br>" if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else ''

            popup_content = f'''
            <!DOCTYPE html>
            <html>
              <head>
                {img_style}
              </head>
              <body>
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                    <a href="{urllink}" target="_blank" style="color: black;">
                        <div class="property-image">
                          <img src="{imagen_principal}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                        </div>
                        {precio}
                        {valormt2}
                        {caracteristicas}
                        {direccion}
                        {tipoinmueble}
                        {tiponegocio}
                        {barrio}
                    </a>
                </div>
              </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        data          = data[['popup','geometry']]
        data['color'] = 'blue'
        geojson       = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def showlistings(data,tiponegocio=None):
    css_format = """
        <style>
            .card {
                background-color: #F0F0F0;
            }
          .property-image {
            width: 100%;
            height: 250px;
            overflow: hidden; 
            margin-bottom: 10px;
          }
          .price-info {
            font-family: 'Roboto', sans-serif;
            font-size: 20px;
            margin-bottom: 2px;
            text-align: center;
          }
          .caracteristicas-info {
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
            margin-bottom: 2px;
            text-align: center;
          }
          img{
            max-width: 100%;
            width: 100%;
            height:100%;
            object-fit: cover;
            margin-bottom: 10px; 
          }
        </style>
    """
    urlexport = "http://www.urbex.com.co/Ficha"
    imagenes  = ''
    for i, items in data.iterrows():
        urllink = urlexport+f"?code={items['code']}&tiponegocio={items['tiponegocio'].lower()}&tipoinmueble={items['tipoinmueble'].lower()}"

        imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
        precio           = f"<b> Precio:</b> ${items['valor']:,.0f}<br>" if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)) else ''
        direccion        = f"<b> Dirección:</b> {items['direccion']}<br>" if 'direccion' in items and isinstance(items['direccion'], str) else ''
        valormt2         = f"<b> Valor m²:</b> ${items['valormt2']:,.0f} m²<br>" if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)) else ''
        tiponegocio      = f"<b> Tipo de negocio:</b> {items['tiponegocio']}<br>" if 'tiponegocio' in items and isinstance(items['tiponegocio'], str) else ''
        tipoinmueble     = items['tipoinmueble'] if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else None
        caracteristicas  = f"<b> Área construida:</b> {items['areaconstruida']}<br>" if 'areaconstruida' in items and (isinstance(items['areaconstruida'], float) or isinstance(items['areaconstruida'], int)) else ''
        barrio           = f"<b> Barrio:</b> {items['scanombre']}<br>"  if 'scanombre' in items and isinstance(items['scanombre'], str) else ''
        
        if any([x for x in ['apartamento','casa'] if x in tipoinmueble.lower()]):
            if all([x for x in ['habitaciones','banos','garajes'] if x in items]):
                try:    caracteristicas = f"{items['areaconstruida']} m<sup>2</sup> | {int(float(items['habitaciones']))} H | {int(float(items['banos']))} B | {int(float(items['garajes']))} G <br>"
                except: caracteristicas = "" 
        tipoinmueble = f"<b> Tipo de inmueble:</b> {items['tipoinmueble']}<br>" if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else ''

        imagenes += f'''
        <div class="col-xl-3 col-sm-6 mb-xl-2 mb-2">
          <div class="card h-100">
            <div class="card-body p-3">
            <a href="{urllink}" target="_blank" style="color: black;">
                <div class="property-image">
                  <img src="{imagen_principal}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                </div>
                {tiponegocio}
                {precio}
                {valormt2}
                {caracteristicas}
                {direccion}
                {tipoinmueble}
                {barrio}
            </a>
            </div>
          </div>
        </div>            
        '''
    if imagenes!='':
        texto = f"""
            <!DOCTYPE html>
            <html>
              <head>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" id="pagestyle" rel="stylesheet"/>
              {css_format}
              </head>
              <body>
              <div class="container-fluid py-4">
                <div class="row">
                {imagenes}
                </div>
              </div>
              </body>
            </html>
            """
        texto = BeautifulSoup(texto, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)
        #st.components.v1.html(texto,height=2000)      

if __name__ == "__main__":
    main()
