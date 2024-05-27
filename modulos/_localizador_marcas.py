import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from shapely.geometry import Point
from streamlit_js_eval import streamlit_js_eval

from data.getdataBrands import getoptions,getdatabrans

from display.stylefunctions  import style_function_geojson


from folium.features import CustomIcon

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
        dataoptions = getoptions()
        tipomarca   = st.selectbox('Busqueda por:',options=sorted(list(dataoptions['label'].unique())))
        idxlabel    = dataoptions[dataoptions['label']==tipomarca]['idxlabel'].iloc[0]
        inputvar    = {'mpio_ccdgo':'11001','idxlabel':idxlabel}
        
    with col2:
        st.write('')
        st.write('')
        st.write('')
        if st.button('Buscar'):
            with st.spinner('Buscando data'):
                st.session_state.data           = getdatabrans(inputvar)
                st.session_state.show_brand_map = True
                st.rerun()
    if not st.session_state.data.empty:
        display_brand_map(st.session_state.data,latitud,longitud,mapwidth,mapheight)
    

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
        
        #geopoints = geopoint_brand(data)
        #marker = folium.Circle(radius=8)
        #marker = folium.Marker(icon=folium.Icon(icon='star'))
        #folium.GeoJson(geopoints,style_function=style_function_geojson,marker=marker).add_to(m)

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
        data['color'] = '#5A189A'    
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
            
            urlexport = "http://urbex.com.co/Busqueda_avanzada"
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

@st.cache_data(show_spinner=False)
def geopoint_brand(data):
    geojson = pd.DataFrame().to_json()
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data             = data[['geometry','marker']]
        data['color']    = 'black'
        geojson          = data.to_json()
    return geojson

if __name__ == "__main__":
    main()
