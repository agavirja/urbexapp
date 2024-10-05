import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import base64
import json
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval

from data.getdatamanzanas import main as getdatamanzanas

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

    #-------------------------------------------------------------------------#
    # Variables 
    direccion = None
    metros    = 500
    
    formato = {
               'latitud':4.652652,
               'longitud':-74.077899,
               'zoom_start':12,
               'data':pd.DataFrame(),
               'datalocalidades':pd.DataFrame(),
               'codseleccion':None,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
     
    colb1,colb2          = st.columns([0.8,0.2])
    coll1,coll2          = st.columns([0.3,0.7])
    colf1,colf2          = st.columns([0.3,0.7])
    maxpiso              = 6
    alturaminpot         = 0
    maxpropietario       = 0 
    maxavaluo            = 0 
    viaprincipal         = 'Todos'
    tratamiento          = []
    areaactividad        = []
    actuacionestrategica = 'Todos'

    with colf1:
        maxpiso              = st.number_input('Número máximo de pisos construidos actualmente',value=2,min_value=0)
        alturaminpot         = st.number_input('Altura mínima P.O.T',value=0,min_value=0)
        tratamiento          = st.multiselect('Tratamiento P.O.T',['CONSOLIDACION', 'DESARROLLO', 'RENOVACION', 'CONSERVACION', 'MEJORAMIENTO INTEGRAL'])
        actuacionestrategica = st.selectbox('Actuación estrategica', options=['Todos','Si','No'])
        areaactividad = st.multiselect('Área de actividad P.O.T',['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
        maxpropietario       = st.number_input('Número máximo de propietarios por lote',value=0,min_value=0)
        maxavaluo            = st.number_input('Valor máximo de avalúo catastral de la manzana',value=0,min_value=0)
        viaprincipal         = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])

    inputvar = {
        'maxpiso':maxpiso,
        'maxpropietario':maxpropietario,
        'maxavaluo':maxavaluo,
        'viaprincipal':viaprincipal,
        'pot':[{'tipo':'tratamientourbanistico','alturaminpot':alturaminpot,'tratamiento':tratamiento},
               {'tipo':'areaactividad','nombreare':areaactividad},
               {'tipo':'actuacionestrategica','isin':actuacionestrategica},
               ]
        }

    with colf1:
        if st.button('Buscar'):
            with st.spinner('Buscando información'):
                st.session_state.data,st.session_state.datalocalidades = getdatamanzanas(inputvar)

    with colb2:
        if st.button('Resetear búsqueda'):
            for key,value in formato.items():
                del st.session_state[key]
            st.rerun()
                
            
    data            = st.session_state.data.copy()
    datalocalidades = st.session_state.datalocalidades.copy()
    datacompilado   = pd.DataFrame(columns=['wkt','type'])  

    if not data.empty:
        #-----------------------#
        # Seleccion de manzanas #
        data = data[(data['avaluo_catastral']>0) | (data['propietarios']>0)]
    if not data.empty:   
        datalocalidades         = datalocalidades[datalocalidades['loccodigo'].isin(data['loccodigo'])]
        datalocalidades['type'] = 'localidad'
        if isinstance(st.session_state.codseleccion,str):
            idd             = datalocalidades['loccodigo']==st.session_state.codseleccion
            datalocalidades = datalocalidades[~idd]
            
        data['type']  = 'manzanas'
        data          = data[data['loccodigo']==st.session_state.codseleccion]
        datacompilado = pd.concat([datalocalidades,data])
        if 'geometry' in datacompilado: 
            del datacompilado['geometry']
            datacompilado = pd.DataFrame(datacompilado)

        idd  = datacompilado['type']=='localidad'
        datacompilado.loc[idd,'label'] = datacompilado.loc[idd].apply(lambda x: f'<b style="font-size:12px;">Localidad: </b> <span style="font-size:12px;">{x["locnombre"]}</span><br><b style="font-size:12px;"># Manzanas: </b> <span style="font-size:12px;">{int(x["countmanzanas"])}</span>', axis=1)

        idd  = datacompilado['type']=='manzanas'
        datacompilado.loc[idd,'label']  = datacompilado.loc[idd].apply(lambda x: f'<b style="font-size:12px;">Manzana: </b> <span style="font-size:12px;">{x["mancodigo"]}</span><br><b style="font-size:12px;"># Lotes: </b> <span style="font-size:12px;">{int(x["lotes"])}</span>', axis=1)

    m = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")

    if not datacompilado.empty:
        geojson = data2geopandas(datacompilado,constraints=inputvar)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        
        tooltip=folium.features.GeoJsonTooltip(
            fields=['label'],  # Campo a mostrar en el tooltip
            aliases=[''],  # Etiquetas para los campos
            localize=False)
            
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup,highlight_function=highlight_function,tooltip=tooltip).add_to(m)
        
    if datacompilado.empty:
        with colf2:
            st_map = st_folium(m,width=int(mapwidth*0.7),height=900)
        
            if "last_active_drawing" in st_map and st_map['last_active_drawing'] is not None and 'properties' in st_map['last_active_drawing']  and 'popup' in st_map['last_active_drawing']['properties'] and st_map['last_active_drawing']['properties']['popup']:
                text = st_map['last_active_drawing']['properties']['popup'].strip()
                if 'Localidad' in str(text):
                    localidad = str(text).split('Localidad:')[-1].split('</b>')[-1].split('<br>')[0].strip()
                    codigo = st.session_state.datalocalidades[st.session_state.datalocalidades['locnombre'] == localidad]['loccodigo'].iloc[0]
                    if st.session_state.codseleccion is None or (isinstance(codigo, str) and isinstance(st.session_state.codseleccion, str) and st.session_state.codseleccion != codigo):
                        st.session_state.codseleccion = codigo
                        st.rerun()
    if not datacompilado.empty:
        with colf2:
            folium_static(m,width=int(mapwidth*0.7),height=900)
        
         
    label = None
    if not datacompilado.empty:
        if not 'manzanas' in datacompilado['type'].unique():
            _,label = colormap(datacompilado,'countmanzanas')
        else:
            _,label = colormap(datacompilado,'avaluo_catastral')
    
    with coll2:
        if label is not None:
            html = labelhtml(label)
            st.components.v1.html(html, height=60)

@st.cache_data(show_spinner=False)
def data2geopandas(data,constraints={}):
    
    geojson = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
        
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
                
        if not 'manzanas' in data['type'].unique():
            data,_ = colormap(data,'countmanzanas')
        else:
            data,_ = colormap(data,'avaluo_catastral')
            idd  = data['type']=='localidad'
            data.loc[idd,'color'] = '#CFCFCF'
        
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            if 'type' in items:
                popupinfo     = "" 
                popup_content = ""
                if 'localidad' in items['type']:
                    try:    popupinfo += f"""<b> Localidad:</b>{items['locnombre']}<br>"""
                    except: pass
                    popup_content =  f'''
                    <!DOCTYPE html>
                    <html>
                        <body>
                            <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                                {popupinfo}
                            </div>
                        </body>
                    </html>
                    '''
                    
                if 'manzanas' in items['type']:
                    encryptjson = {'latitud':items['geometry'].centroid.y,
                                   'longitud':items['geometry'].centroid.x,
                                   'zoom':18,
                                   'polygon':items['wkt'],
                                   'estado':'search',
                                   'constraints':constraints}
                    encryptjson = json.dumps(encryptjson)
                    encryptjson = encryptjson.encode('utf-8')
                    encryptjson = base64.b64encode(encryptjson)
                    encryptjson = encryptjson.decode('utf-8')
                    urllink     = f"http://www.urbex.com.co/Lotes_y_Cabidas?code={encryptjson}&token={st.session_state.token}"
        
                    try:    popupinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>"""
                    except: pass
                    try:    popupinfo += f"""<b> # Lotes:</b> {items['lotes']}<br>"""
                    except: pass
                    #try:    popupinfo += f"""<b> # Predios:</b> {items['predios']}<br>"""
                    #except: pass
                    try:    popupinfo += f"""<b> Área de terreno:</b> {round(items['preaterre'],2)}<br> """
                    except: pass
                    #try:    popupinfo += f"""<b> Área construida:</b> {round(items['preaconst'],2)}<br>"""
                    #except: pass
                    #try:    popupinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br> """
                    #except: pass
                    try:    popupinfo += f"""<b> Pisos:</b> {int(items['connpisos'])}<br> """
                    except: pass
                    try:    popupinfo += f"""<b> Avalúo catastral:</b> ${items['avaluo_catastral']:,.0f} <br>"""
                    except: pass            
                    try:    popupinfo += f"""<b> Propietarios:</b> {int(items['propietarios'])}<br> """
                    except: pass
        
                    if popupinfo=="": popupinfo = "<b> Ver análisis de la manzana</b>"
                    popup_content =  f'''
                    <!DOCTYPE html>
                    <html>
                        <body>
                            <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                                <a href="{urllink}" target="_blank" style="color: black;">
                                    {popupinfo}
                                </a>
                            </div>
                        </body>
                    </html>
                    '''

                data.loc[idd,'popup'] = popup_content
        data    = data[['popup','color','label','geometry']]
        geojson = data.to_json()
    return geojson

def colormap(data,tipoconsulta):
    label = pd.DataFrame(columns=['pos','color','value'])
    if not data.empty and tipoconsulta in data: 
        data['normvalue'] = data[tipoconsulta].rank(pct=True)
        #cmap              = plt.cm.RdYlGn.reversed() # plt.cm.RdYlGn - plt.cm.viridis
        cmap              = plt.cm.coolwarm # plt.cm.RdYlGn - plt.cm.viridis
        data['color']     = data['normvalue'].apply(lambda x: to_hex(cmap(x)))
        
        label  = []
        conteo = 0
        for j in [0,0.2,0.4,0.6,0.8,1]:
            conteo    += 1
            df         = data.copy()
            df['diff'] = abs(j-df['normvalue'])
            df         = df.sort_values(by='diff',ascending=True)
            color      = df['color'].iloc[0]
            value      = df[tipoconsulta].iloc[0]
            if 'avaluo_catastral' in tipoconsulta: 
                value = f"${value /1000000:,.2f} mm"
            elif 'countmanzanas' in tipoconsulta:
                value = f'{value}    '
            label.append({'pos':conteo,'color':color,'value':value})
        label = pd.DataFrame(label) 
    return data,label

def highlight_function(feature):
    return {
        'fillColor': '#f0f8ff',  # Color de relleno cuando haces hover
        'color': '#f0f8ff',      # Color del borde cuando haces hover
        'weight': 0,             # Grosor del borde cuando haces hover
        'fillOpacity': 0.1,      # Opacidad del relleno cuando haces hover
    }

@st.cache_data(show_spinner=False)
def labelhtml(data):
    
    data['color'] = data['color'].apply(lambda x: f'<span class="legend-color" style="background:{x};"></span>')
    data['value'] = data['value'].apply(lambda x: f'<span>{x}</span>')
    colors        = ''.join(data['color'])
    valores       = ''.join(data['value'])

    style = """
    <style>
        .legend-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 20px;
        }
        .legend-bar {
            display: flex;
            align-items: center;
            position: relative;
        }
        .legend-color {
            height: 20px;
            width: 100px; /* Width of each color box */
            margin: 0; /* Remove margin */
        }
        .legend-numbers {
            display: flex;
            justify-content: space-between;
            position: absolute;
            top: 20px; 
            left: calc(50% + 60px); /* Move numbers a bit to the right */
            transform: translateX(-50%); /* Adjust to center relative to the new position */
            width: calc(100px * 6); /* Width based on the number of colors */
            font-size: 12px;
            color: #555;
            margin: 0; /* Remove margin */
            padding: 0; /* Remove padding */
            text-align: center; /* Center numbers horizontally within their space */
        }
        .legend-numbers span {
            display: block;
            width: 100px; /* Same width as color boxes */
            text-align: center;
            margin: 0; /* Remove margin */
            padding: 0; /* Remove padding */
        }
    </style>

    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
    </head>
    <body>
        <!-- Leyenda del Mapa de Calor -->
        <div class="legend-container">
            <div class="legend-bar">
                {colors}
                <div class="legend-numbers">
                {valores}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html
