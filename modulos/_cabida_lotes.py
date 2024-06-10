import streamlit as st
import json
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
import plotly.express as px
from shapely import wkt
from shapely.geometry import mapping
from bs4 import BeautifulSoup
from streamlit_folium import st_folium
from shapely.geometry import mapping,Point
from shapely.affinity import scale
from shapely.ops import unary_union
from area import area as areapolygon
from sqlalchemy import create_engine 
from sklearn.cluster import KMeans
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime, timedelta

from data.circle_polygon import circle_polygon
from data.getdatalotes import main as getdatalotes
from data.data_estudio_mercado_general import builddata
from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.datacomplemento import main as datacomplemento
from data.getuso_destino import getuso_destino

def main(barmanpre):
    
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
        collogo1,collogo2,collogo3 = st.columns([6,1,1])
        with collogo2:
            st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
            
        landing(barmanpre,mapwidth,mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(barmanpre,mapwidth,mapheight):
    
    colm1,colm2 = st.columns([0.3,0.7])
    colf1,colf2 = st.columns(2)
    colp1,colp2,colp3,colp4,colp5 = st.columns(5)
    
    with colf1:
        idc = st.number_input('índice de ocupación:',value=70,min_value=0,max_value=100)
        
    with colf2:
        pac = st.number_input('Porcentaje de área común en la planta:',value=20,min_value=0,max_value=100)
        pac = pac/100
        
    #-------------------------------------------------------------------------#
    # Data
    with st.spinner('Buscando información'):
        polygon_wkt  = getpolygons(barmanpre)
        polygon      = wkt.loads(polygon_wkt)
        newpolygon   = reduce_polygon(polygon,idc)
        try:
            latitud  = polygon.centroid.y
            longitud = polygon.centroid.x
        except:
            latitud  = 4.690419
            longitud = -74.052086
        #---------------------------------------------------------------------#
        # Data complemento
        input_complemento = datacomplemento(barmanpre=barmanpre,latitud=latitud,longitud=longitud,direccion=None,polygon=None,precuso=None)
        #---------------------------------------------------------------------#
        # Data Tipologias
        input_cifras_generales = cifrasgenerales(barmanpre)
        
    #-------------------------------------------------------------------------#
    # Tomar el numero de pisos del POT
    alturamax = None
    if 'POT' in input_complemento:
        for i in input_complemento['POT']:
            if 'data' in i and "Altura máx" in i['data']:
                try:    alturamax = int(i['data']["Altura máx"])
                except: pass
    #-------------------------------------------------------------------------#
    # Duplicar area si es receptora de vivienda VIS
    msn = None
    if 'POT' in input_complemento:
        for i in input_complemento['POT']:
            if "nombre" in i and "Área de actividad" in i["nombre"]:
                if "data" in i and "Nombre" in i['data']:
                    if any( [x for x in ["Receptora de vivienda de interés social","vivienda de interés social","vivienda de interes social"] if x in i['data']['Nombre']]):
                        msn = 'Al ser receptora de vivienda de interés social se puede duplicar el número de pisos'
                        if isinstance(alturamax,int) and alturamax>0:
                            alturamax = int(alturamax*2)
    
    with colf1:
        index = 0
        if isinstance(alturamax,int) and alturamax>0: index = alturamax
        numero_pisos = st.selectbox('Número de pisos construidos:',options=range(21),index=index)
    
    with colf2:
        altura_pisos = st.number_input('Altura de placas (metros):',value=3.5,min_value=2.0,step=0.5)
        
    if isinstance(msn,str) and msn!="":
        with colf1:
            st.success(msn)
        
    #-------------------------------------------------------------------------#
    # Calculos
    areapoligonocompleto = areapolygon(mapping(polygon))
    areaplantas          = areapolygon(mapping(newpolygon))
    areatotalconstruida  = areaplantas*numero_pisos
    areatotalvendible    = areaplantas*numero_pisos*(1-pac)
    alturabuilding       = numero_pisos*altura_pisos
        
    #-------------------------------------------------------------------------#
    # Configuracion de plantas
    inputvar = []
    porcentajeacumulado = 0
    index = 1
    while porcentajeacumulado<1:
        colp1, colp2, colp3, colp4, colp5 = st.columns(5)
        with colp2:
            planta = st.text_input('Planta 1', disabled=True, placeholder='Planta 1', label_visibility="hidden", key=f'planta_1_{index}')
        with colp3:
            tipoinmueble = st.selectbox('Tipo de inmueble:', options=['Áreas comunes','Apartamento', 'Bodega', 'Casa', 'Local', 'Oficina','Áreas comunes'], key=f'tipoinmueble_1_{index}')
        with colp4:
            max_value = (1 - porcentajeacumulado) * 100.0
            porcentaje = st.number_input('Porcentaje:', value=max_value, min_value=0.0, max_value=max_value, key=f'porcentaje_1_{index}') / 100
            porcentajeacumulado += porcentaje
        with colp5:
            areavendible = st.number_input('Área vendible:', value=porcentaje * areaplantas, key=f'areavendible_1_{index}', disabled=True)
        inputvar.append({'planta':'1','pisomin': 1, 'pisomax': 1,'tipoinmueble': tipoinmueble, 'porcentaje': porcentaje, 'areavendible': areavendible})
        index += 1
    
    index = 1
    if numero_pisos > 1:
        pisomax = 0
        while pisomax < numero_pisos:
            index += 1
            colp1, colp2, colp3, colp4, colp5 = st.columns(5)
            
            with colp1:
                if pisomax == 0:
                    pisomin_options = [2]
                else:
                    pisomin_options = [pisomax + 1]
                pisomin = st.selectbox('Desde el piso:', options=pisomin_options, key=f'planta_2_min_{index}')
            
            with colp2:
                if pisomin is not None:
                    options = list(range(pisomin, numero_pisos + 1))
                    pisomax = st.selectbox('Hasta el piso:', options=options, index=len(options) - 1, key=f'planta_2_max_{index}')
            with colp3:
                tipoinmueble = st.selectbox('Tipo de inmueble:', options=['Apartamento', 'Oficina'], key=f'tipoinmueble_2_{index}')
            with colp4:
                porcentaje = st.number_input('Porcentaje:', value=100.0, min_value=0.0, max_value=100.0, disabled=True, key=f'porcentaje_2_{index}') / 100
            with colp5:
                if pisomin is not None and pisomax is not None:
                    areavendible = st.number_input('Área vendible:', value=(pisomax - pisomin + 1) * areaplantas, key=f'areavendible_2_{index}', disabled=True)
                else:
                    areavendible = 0 
            inputvar.append({'planta':'2+','pisomin': pisomin, 'pisomax': pisomax, 'tipoinmueble': tipoinmueble, 'porcentaje': porcentaje, 'areavendible': areavendible})
    
    #-----------------------------------------------------------------------------#
    # Mapa 2D
    with colm1:
        m = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
        folium.GeoJson(mapping(polygon), style_function=style_function_bigpolygon).add_to(m)
        folium.GeoJson(mapping(newpolygon), style_function=style_function_smallpolygon).add_to(m)
        st_map = st_folium(m,width=500,height=600)
    
    #-----------------------------------------------------------------------------#
    # Mapa 3D
    with colm2:
    
        geojson_feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [list(newpolygon.exterior.coords)]
            }
        }
        geojson_feature['geometry']['coordinates'] = [[list(coord) for coord in geojson_feature['geometry']['coordinates'][0]]]
    
        geojson_feature2 = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [list(polygon.exterior.coords)]
            }
        }
        geojson_feature2['geometry']['coordinates'] = [[list(coord) for coord in geojson_feature2['geometry']['coordinates'][0]]]
    
    
        access_token = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'
        
        mapa = """
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <title>3D Building</title>
        <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
        <link href="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.css" rel="stylesheet">
        <script src="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.js"></script>
        <style>
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        </style>
        </head>
        <body>
        <div id="map"></div>
        <script>
            mapboxgl.accessToken = 'replace_access_token';
            const map = new mapboxgl.Map({
                style: 'mapbox://styles/mapbox/light-v11',
                center: [centerlng, centerlat],
                zoom: 18,
                pitch: 45,
                bearing: -17.6,
                container: 'map',
                antialias: true
            });
        
            map.on('style.load', () => {
                const polygon = geojsonpolygon;
                
                map.addSource('polygon', {
                    'type': 'geojson',
                    'data': {
                        'type': 'FeatureCollection',
                        'features': [polygon]
                    }
                });
                            
                map.addLayer({
                    'id': 'polygon-2d-layer',
                    'type': 'fill',
                    'source': 'polygon',
                    'paint': {
                        'fill-color': '#0074D9',
                        'fill-opacity': 0.5
                    }
                });
        
                const numFloors = numero_pisos;
                const floorHeight = altura_pisos;
                for (let i = 0; i < numFloors; i++) {
                    map.addLayer({
                        'id': `polygon-layer-${i}`,
                        'type': 'fill-extrusion',
                        'source': 'polygon',
                        'paint': {
                            'fill-extrusion-color': '#0074D9',
                            'fill-extrusion-height': (i + 1) * floorHeight,
                            'fill-extrusion-base': i * floorHeight,
                            'fill-extrusion-opacity': 0.6
                        }
                    });
                }
                
            });
        </script>
        
        </body>
        </html>
        """
        mapa = mapa.replace('centerlat', f'{latitud}').replace('centerlng', f'{longitud}').replace('replace_access_token', access_token)
        mapa = mapa.replace('geojsonpolygon', f'{geojson_feature}').replace('numero_pisos',f'{numero_pisos}').replace('altura_pisos',f'{altura_pisos}')
        mapa = mapa.replace('geojsonpolygon2', f'{geojson_feature2}')
        mapa = BeautifulSoup(mapa, 'html.parser')
        st.components.v1.html(str(mapa), width=1200,height=600)

    #-------------------------------------------------------------------------#
    # Datos de mercado
    with st.spinner('información del mercado'):
        polygon         = str(circle_polygon(500,latitud,longitud))
        inputvar_search =  {
            'polygon':polygon,
            'latitud':latitud,
            'longitud':longitud,
            }
        datalotes                      = getdatalotes(inputvar_search)
        datacatastro,datatransacciones = builddata(polygon=polygon)

    tipoinmueble = []
    for i in inputvar:
        tipoinmueble.append(i['tipoinmueble'])
    if tipoinmueble!=[]:
        tipoinmueble = list(set(tipoinmueble))

    if not datatransacciones.empty and not datacatastro.empty:
        precuso           = inmueble2usosuelo(tipoinmueble)
        datacatastro      = datacatastro[datacatastro['precuso'].isin(precuso)]
        datatransacciones = datatransacciones[datatransacciones['precuso'].isin(precuso)]
        datatransacciones['fecha_documento_publico_original'] = pd.to_datetime(datatransacciones['fecha_documento_publico_original'])

    #-------------------------------------------------------------------------#
    # Data Tipologias
    datatipologias = pd.DataFrame(inputvar)
    datagrupada    = pd.DataFrame()
    if not datatipologias.empty:
        datagrupada = datatipologias.groupby('tipoinmueble')['areavendible'].sum().reset_index()
        datagrupada.columns = ['tipoinmueble','areavendible']
        
    valores_referencia = []
    if not datagrupada.empty:
        for tipoinmueble in datagrupada['tipoinmueble'].unique():
            datan       = datagrupada[datagrupada['tipoinmueble']==tipoinmueble]
            datan.index = range(len(datan))
            precuso     = inmueble2usosuelo([tipoinmueble])
            if isinstance(precuso, list) and precuso!=[]:
                datapaso = datatransacciones[datatransacciones['precuso'].isin(precuso)]
                if not datapaso.empty and 'codigo' in datapaso:
                    datapaso = datapaso[datapaso['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
                if not datapaso.empty:
                    filtrodate    = datetime.now()-timedelta(days=365)
                    datapaso      = datapaso[datapaso['fecha_documento_publico_original']>=filtrodate]
                if not datapaso.empty:
                    valormt2      = datapaso['valormt2_transacciones'].median()
                    areavendible  = datan['areavendible'].iloc[0]
                    valorestimado = areavendible*valormt2
                    valores_referencia.append({'variable':tipoinmueble,'valormt2':valormt2,'areavendible':areavendible,'valorestimado':valorestimado})
    dataestimado = pd.DataFrame(valores_referencia)
    if not dataestimado.empty:
        datappend    = pd.DataFrame([{'variable':'Total','areavendible':dataestimado['areavendible'].sum(),'valormt2':'','valorestimado':dataestimado['valorestimado'].sum()}])
        dataestimado = pd.concat([dataestimado,datappend])
        
    #-------------------------------------------------------------------------#
    # Tabla de resumen
    resumen = {'indiceocupacion':idc,'alturaconstruccion':alturabuilding,'areapoligonocompleto':areapoligonocompleto,'numero_pisos':numero_pisos,'areaplantas':areaplantas,'areatotalconstruida':areatotalconstruida,'areatotalvendible':areatotalvendible}
    html    = htmltable(resumen=resumen,data=datatipologias,dataestimado=dataestimado,input_complemento=input_complemento,input_cifras_generales=input_cifras_generales)
    st.components.v1.html(html,height=1000,scrolling=True)

    #---------------------------------------------------------------------#
    # Graficas: Transacciones
    if not datatransacciones.empty:
        for tipoinmueble in datatipologias['tipoinmueble'].unique():
            precuso = inmueble2usosuelo([tipoinmueble])
            df      = datatransacciones[datatransacciones['precuso'].isin(precuso)]
            if not df.empty:
                st.write(tipoinmueble)
                cols1,cols2 = st.columns(2,gap='large')
                df         = df.groupby('fecha_documento_publico').agg({'valormt2_transacciones':['count','median']}).reset_index()
                df.columns = ['fecha','count','value']
                df.index = range(len(df))
                fig = px.bar(df, x="fecha", y="count", text="count", title='Número de transacciones')
                fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_xaxes(tickmode='linear', dtick=1)
                fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                    'legend':dict(bgcolor='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                with cols1:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                    
                fig = px.bar(df, x="fecha", y="value", text="value", title='Valor promedio de las transacciones por m²')
                fig.update_traces(texttemplate='$%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                with cols2:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
        
    if not datatransacciones.empty:

        precuso = inmueble2usosuelo(['Apartamento'])
        df      = datatransacciones[datatransacciones['precuso'].isin(precuso)]
        
        X                    = df[['preaconst']].values
        optimal_k            = optimal_k_elbow_method(X)
        kmeans               = KMeans(n_clusters=optimal_k, random_state=42)
        df['cluster']        = kmeans.fit_predict(X)
        df['cluster_center'] = df['cluster'].apply(lambda x: kmeans.cluster_centers_[x][0])
        dfrango              = df.groupby('cluster').agg({'prechip':'count','preaconst':'median','valormt2_transacciones':'median'}).reset_index()
        dfrango.columns      = ['cluster','count','area','valormt2']
        dfrango              = dfrango.sort_values(by='count',ascending=False)
        dfrango.index        = range(len(dfrango))
        
        cluster_counts       = df['cluster'].value_counts().sort_index().reset_index()
        numcluster           = cluster_counts[cluster_counts['count']==cluster_counts['count'].max()]['cluster'].iloc[0]
        dfrango              = df[df['cluster']==numcluster]
        v = {'min':dfrango['preaconst'].min(),'max':dfrango['preaconst'].max(),'median':dfrango['preaconst'].median(),'mean':dfrango['preaconst'].mean(),'median_value':dfrango['valormt2_transacciones'].median()}

        


    
    # poner todos los demas edificios en 3D
    # poner en el resumen altura de las placas 
    # poner area de aislamiento (calcular le poligono restante) 
    # metricas o valores
    
    # Que edificios son similares a los que estan 
    # en cuanto se estan vendiendo 
    # quien los construyo (galeria inmobiliaria) 
    
    # Valores de mercado
    
@st.cache_data(show_spinner=False)
def optimal_k_elbow_method(X, max_k=10):
    inertias = []
    for k in range(1, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
    differences       = np.diff(inertias)
    second_derivative = np.diff(differences)
    optimal_k         = np.argmin(second_derivative) + 2 
    return optimal_k

@st.cache_data(show_spinner=False)
def getpolygons(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datalotes = ""
    query     = ""
    if isinstance(barmanpre,str):
        lista = "','".join(barmanpre.split('|'))
        query = f" lotcodigo IN ('{lista}')"
    if query!="":
        datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
    if not datalotes.empty:
        if len(datalotes)>1:
            datalotes['geometry'] = gpd.GeoSeries.from_wkt(datalotes['wkt'])
            datalotes             = gpd.GeoDataFrame(datalotes, geometry='geometry')
            polygon               = unary_union(datalotes['geometry'].to_list())
            datalotes             = polygon.wkt
        else:
            datalotes = datalotes['wkt'].iloc[0]
    engine.dispose()
    return datalotes
    
def reduce_polygon(geometry, percentage):
    centroid     = geometry.centroid
    scale_factor = percentage / 100.0
    return scale(geometry, xfact=scale_factor, yfact=scale_factor, origin=centroid)

def htmltable(resumen={},data=pd.DataFrame(),dataestimado=pd.DataFrame(),input_complemento=pd.DataFrame(),input_cifras_generales={}):
    
    tablaubicacion       = ""
    tablaresumen         = ""
    tablademografica     = ""
    tablatransporte      = ""
    tablavias            = ""
    tablagalerianuevos   = ""
    tablapot             = ""
    tablasitp            = ""
    tablacifrasterreno   = ""
    tablatipoliguasactuales = ""
    #---------------------------------------------------------------------#
    # Seccion ubicacion
    try:    localidad = input_complemento['localidad'] if isinstance(input_complemento['localidad'], str) else None
    except: localidad = None
    try:    barrio = input_complemento['barrio'] if isinstance(input_complemento['barrio'], str) else None
    except: barrio = None
    try:    estrato = int(input_complemento['estrato'])
    except: estrato = None
    try:    codigoupl = input_complemento['codigoupl'] if isinstance(input_complemento['codigoupl'], str) else None
    except: codigoupl = None       
    try:    upl = input_complemento['upl'] if isinstance(input_complemento['upl'], str) else None
    except: upl = None      
    try:    nombre_conjunto = input_complemento['nombre_conjunto'] if isinstance(input_complemento['nombre_conjunto'], str) else None
    except: nombre_conjunto = None  

    direccion       = None
    nombre_conjunto = None
    if 'direccion' in input_complemento and isinstance(input_complemento['direccion'], str): 
        direccion = input_complemento['direccion']
    if 'nombre_conjunto' in input_complemento and isinstance(input_complemento['nombre_conjunto'], str): 
        nombre_conjunto = input_complemento['nombre_conjunto']
        
    formato   = {'Dirección:':direccion,'Localidad:':localidad,'Código UPL:':codigoupl,'UPL:':upl,'Barrio:':barrio,'Estrato:':estrato,'Nombre:':nombre_conjunto}
    html_paso = ""
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
    if html_paso!="":
        labeltable     = "Ubicación"
        tablaubicacion = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaubicacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaubicacion}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion resumen general
    if resumen!={}:
        areapoligonocompleto = f"{resumen['areapoligonocompleto']:,.2f}"  if 'areapoligonocompleto' in resumen else None
        numero_pisos         = f"{resumen['numero_pisos']:,.0f}"  if 'numero_pisos' in resumen else None
        areaplantas          = f"{resumen['areaplantas']:,.2f}"  if 'areaplantas' in resumen else None
        areatotalconstruida  = f"{resumen['areatotalconstruida']:,.2f}"  if 'areatotalconstruida' in resumen else None
        areatotalvendible    = f"{resumen['areatotalvendible']:,.2f}"  if 'areatotalvendible' in resumen else None
        indiceocupacion      = f"{resumen['indiceocupacion']:,.2f}%"  if 'indiceocupacion' in resumen else None  
        alturaconstruccion   = f"{resumen['alturaconstruccion']:,.0f} mt"  if 'alturaconstruccion' in resumen else None  

        formato     = [
            {'variable':'Área total del poligono:','value':areapoligonocompleto},
            {'variable':'índice de ocupación:','value':indiceocupacion},
            {'variable':'Altura de la construcción:','value':alturaconstruccion},
            {'variable':'Número de pisos construidos:','value':numero_pisos},
            {'variable':'Área total de cada planta:','value':areaplantas},
            {'variable':'Área total construida:','value':areatotalconstruida},
            {'variable':'Área total vendible (removiendo áreas comunes):','value':areatotalvendible},
            ]
        
        html_paso = ""
        for i in formato: 
            key   = i['variable']
            value = i['value']
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            labeltable     = "Resumen:"
            tablaresumen = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablaresumen = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaresumen}</tbody></table></div></div>"""
        
    #---------------------------------------------------------------------#
    # Seccion Tipologias
    tablatipologias = "" 
    if not data.empty:
        html_paso   = ""
        for j in ['1','2+']:
            dataP       = data[data['planta']==j]
            dataP.index = range(len(dataP))
            conteo      = -1
            spaceline   = ""
            if '1' in j:
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Planta 1</h6></td></tr>"""
                titulov    = ['']*len(dataP)
                titulov[0] = titulo
                
            for i in range(len(dataP)):
                if '2+' in j:
                    titulo  = f'Planta {dataP["pisomin"].iloc[i]}-{dataP["pisomax"].iloc[i]}'
                    titulo  = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{titulo}</h6></td></tr>"""
                    titulov = [titulo]
                    conteo  = -1
                    spaceline = """<tr><td style="border: none;"><h6></h6></td></tr>"""
                    
                conteo    += 1
                htmlline   = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['tipoinmueble'].iloc[i]}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['porcentaje'].iloc[i]*100:,.1f}%</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['areavendible'].iloc[i]:,.2f}</h6></td></tr>"""
                html_paso += f"""
                {spaceline}
                {titulov[conteo]}
                {spaceline}
                {htmlline}
                {spaceline}
                """
        if html_paso!="":
            labeltable      = "Tipologías"
            tablatipologias = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">% del Área</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área vendible</h6></td>
            </tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablatipologias = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatipologias}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion valores de recaudo
    tablavalores = "" 
    if not dataestimado.empty:
        html_paso = ""
        df        = dataestimado.copy()
        df.index  = range(len(df))
        idd       = df.index<len(df)-1
        if 'variable'      in df: df.loc[idd,'variable']      = df.loc[idd,'variable'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{x}</h6></td>"""  if not pd.isnull(x) and isinstance(x, str) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'areavendible'  in df: df.loc[idd,'areavendible']  = df.loc[idd,'areavendible'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{x:,.2f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'valormt2'      in df: df.loc[idd,'valormt2']      = df.loc[idd,'valormt2'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">${x:,.0f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'valorestimado' in df: df.loc[idd,'valorestimado'] = df.loc[idd,'valorestimado'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">${x:,.0f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        idd = df.index==df.index[-1]
        if 'variable'      in df: df.loc[idd,'variable']      = df.loc[idd,'variable'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{x}</h6></td>"""  if not pd.isnull(x) and isinstance(x, str) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'areavendible'  in df: df.loc[idd,'areavendible']  = df.loc[idd,'areavendible'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{x:,.2f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'valormt2'      in df: df.loc[idd,'valormt2']      = df.loc[idd,'valormt2'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        if 'valorestimado' in df: df.loc[idd,'valorestimado'] = df.loc[idd,'valorestimado'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
        variables    = [x for x in ['variable','areavendible','valormt2','valorestimado'] if x in df]
        df['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
        html_paso += f"""
        {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(df['output'].unique())}
        """                                                       
        if html_paso!="":
            labeltable    = "Recaudo potencial estimado:"
            tablavalores = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área vendible</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor venta por mt2</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor recaudo estimado</h6></td>
            </tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablavalores = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavalores}</tbody></table></div></div>"""
             
    #---------------------------------------------------------------------#
    # Cifras actuales del lote
    if isinstance(input_cifras_generales, dict) and input_cifras_generales!={}:
        html_paso = ""
        formato = [{'variable':'Número de predios','value':'predios'},
                   {'variable':'Pisos construidos','value':'pisos'},
                   {'variable':'Sotanos','value':'sotanos'},
                   {'variable':'Esquinero','value':'esquinero'},
                   {'variable':'Estrato','value':'estrato'},
                   {'variable':'Área construida total','value':'areaconstruidatotal'},
                   {'variable':'Avalúo catastral','value':'avaluocatastral'},
                   {'variable':'Predial','value':'predialtotal'}]
        for i in formato:
            value    = i['value']
            variable = i['variable'] 
            if value in input_cifras_generales:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{variable}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{input_cifras_generales[value]}</h6></td></tr>"""
        if html_paso!="":
            labeltable       = "¿Qué hay actualmente en terreno?"
            tablacifrasterreno = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablacifrasterreno = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablacifrasterreno}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Tipos de inmuebles actuales en el terreno
    if isinstance(input_cifras_generales, dict) and input_cifras_generales!={}:
        if 'precuso' in input_cifras_generales:
            df = pd.DataFrame(input_cifras_generales['precuso'])
            if not df.empty:
                html_paso = ""
                df        = df.sort_values(by='preaconst_precuso',ascending=False)
                df.index  = range(len(df))
                if 'usosuelo'          in df: df['usosuelo']          = df['usosuelo'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{x}</h6></td>"""  if not pd.isnull(x) and isinstance(x, str) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
                if 'predios_precuso'   in df: df['predios_precuso']   = df['predios_precuso'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{x:,.0f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
                if 'preaconst_precuso' in df: df['preaconst_precuso'] = df['preaconst_precuso'].apply(lambda x:   f"""<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{x:,.2f}</h6></td>"""  if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>""")
                variables    = [x for x in ['usosuelo','predios_precuso','preaconst_precuso'] if x in df]
                df['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
                html_paso += f"""
                {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(df['output'].unique())}
                """                                                       
                if html_paso!="":
                    labeltable    = "Tipoligías actuales en el terreno:"
                    tablatipoliguasactuales = f"""
                    <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    <tr>
                        <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Uso del suelo</h6></td>
                        <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># Predios</h6></td>
                        <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área construida total</h6></td>
                    </tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    {html_paso}
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    """
                    tablatipoliguasactuales = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatipoliguasactuales}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion POT
    if 'POT' in input_complemento and input_complemento['POT']!=[]:
        html_paso = ""
        for items in input_complemento['POT']:
            if 'data' in items:
                if len(items['data'])>1:
                    html_paso += f"""
                    <tr><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{items['nombre']}:</h6></td></tr>
                    """
                    for key,value in items['data'].items():
                        html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                else:
                    for key,value in items['data'].items():
                        html_paso += f"""
                        <tr><td style="border: none;"><h6></h6></td></tr>
                        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{items['nombre']}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>
                        """
                conteo += 1
            
        if html_paso!="":
            labeltable = "P.O.T"
            tablapot   = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablapot = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablapot}</tbody></table></div></div>"""

    labelbarrio = ""
    try:
        if 'barrio' in input_complemento and isinstance(input_complemento['barrio'], str): 
            labelbarrio = f'[{input_complemento["barrio"].title()}]'
    except: pass
    #---------------------------------------------------------------------#
    # Seccion Demografica
    if 'dane' in input_complemento:
        html_paso = ""
        for key,value in input_complemento['dane'].items():
            try: 
                valor = "{:,}".format(int(value))
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{valor}</h6></td></tr>"""
                conteo    += 1
            except: pass
        if html_paso!="":
            labeltable         = f"Información Demográfica {labelbarrio}"
            tablademografica = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablademografica = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablademografica}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion Transporte
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso       = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        labeltable      = "Transmilenio"
        tablatransporte = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablatransporte = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatransporte}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion SITP
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso  = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        labeltable = "SITP"
        tablasitp  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablasitp = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablasitp}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion Vias
    if 'vias' in input_complemento and isinstance(input_complemento['vias'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['vias']}</h6></td></tr>"""
        labeltable = "Vías"
        tablavias  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablavias = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavias}</tbody></table></div></div>"""
        conteo    += 1    

           
    style = """
    <style>
        .css-table {
            overflow-x: auto;
            overflow-y: auto;
            width: 100%;
            height: 100%;
        }
        .css-table table {
            width: 100%;
            padding: 0;
            table-layout: fixed; 
            border-collapse: collapse;
        }
        .css-table td {
            text-align: left;
            padding: 0;
            overflow: hidden; 
            text-overflow: ellipsis; 
        }
        .css-table h6 {
            line-height: 1; 
            font-size: 50px;
            padding: 0;
        }
        .css-table td[colspan="labelsection"] {
          text-align: left;
          font-size: 15px;
          color: #A16CFF;
          font-weight: bold;
          border: none;
          border-bottom: 2px solid #A16CFF;
          margin-top: 20px;
          display: block;
          font-family: 'Inter';
          width: 100%
        }
        .css-table td[colspan="labelsectionborder"] {
          text-align: left;
          border: none;
          border-bottom: 2px solid blue;
          margin-top: 20px;
          display: block;
          padding: 0;
          width: 100%;
        }
        
        #top {
            position: absolute;
            top: 0;
        }
        
        #top:target::before {
            content: '';
            display: block;
            height: 100px; 
            margin-top: -100px; 
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
      <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      {style}
    </head>
    <body>
      <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: -50px;">
        <div class="row">
          <div class="col-md-12 mb-md-0 mb-2">
            <div class="card h-100">
              <div class="card-body p-3">
                <div class="container-fluid py-4">
                  <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                    {tablaubicacion}
                    {tablaresumen}
                    {tablatipologias}
                    {tablavalores}
                    {tablacifrasterreno}
                    {tablatipoliguasactuales}
                    {tablapot}
                    {tablademografica}
                    {tablatransporte}
                    {tablavias}
                    {tablasitp}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return html

@st.cache_data(show_spinner=False)
def cifrasgenerales(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    inputvar = {}
    query         = ""
    databarmanpre = pd.DataFrame()
    if isinstance(barmanpre,str):
        lista = "','".join(barmanpre.split('|'))
        query = f" barmanpre IN ('{lista}')"
    if isinstance(barmanpre,list):
        lista = "','".join(barmanpre)
        query = f" barmanpre IN ('{lista}')"
    if query!="":
        databarmanpre = pd.read_sql_query(f"SELECT * FROM bigdata.bogota_barmanpre_general WHERE {query}" , engine)
        
    if not databarmanpre.empty:
        databarmanpre['predialtotal'] = None
        if 'predialmt2' in databarmanpre and 'preaconst_precuso' in databarmanpre:
            databarmanpre['predialtotal'] = databarmanpre['predialmt2']*databarmanpre['preaconst_precuso']
            databarmanpre['predialtotal'] = pd.to_numeric(databarmanpre['predialtotal'],errors='coerce')
        for i in ['preaconst','connpisos','avaluocatastral','predios_precuso','preaconst_precuso','connpisos','connsotano']:
            databarmanpre[i] = pd.to_numeric(databarmanpre[i],errors='coerce')
        
        # Cifras generales
        databarmanpre['isin'] = 1
        dd         = databarmanpre.groupby('isin').agg({'predios_precuso':'sum','connpisos':'max','connsotano':'max','esquinero':'max','estrato':'max','predialtotal':'sum'}).reset_index()
        dd.columns = ['isin','predios','pisos','sotanos','esquinero','estrato','predialtotal']
        inputvar.update(dd.iloc[0].to_dict())
        
        # Cifras por barmanpre
        d1         = databarmanpre.groupby('barmanpre').agg({'avaluocatastral':'max','preaconst':'max'}).reset_index()
        d1.columns = ['barmanpre','avaluocatastral','areaconstruidatotal']
        d1['isin'] = 1
        d1         = d1.groupby('isin').agg({'avaluocatastral':'sum','areaconstruidatotal':'sum'}).reset_index()
        inputvar.update(d1.iloc[0].to_dict())

        # Por precuso
        d2 = databarmanpre.groupby('precuso').agg({'predios_precuso':'sum','preaconst_precuso':'sum'}).reset_index()
        d2.columns = ['precuso','predios_precuso','preaconst_precuso']
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        d2 = d2.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        inputvar.update({'precuso':d2.to_dict(orient='records')})
    engine.dispose()
    return inputvar

def style_function_bigpolygon(feature):
    return {
        'fillColor': '#DE5478',
        'color':'#DE5478',
        'weight': 1,
    }

def style_function_smallpolygon(feature):
    return {
        'fillColor': '#0074D9',
        'color':'#0074D9',
        'weight': 1,
    }

#if __name__ == "__main__":
#    main(barmanpre)