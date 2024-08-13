import streamlit as st
import pandas as pd
import numpy as np
import folium
import base64
import json
from shapely import wkt
from shapely.geometry import mapping
from bs4 import BeautifulSoup
from streamlit_folium import st_folium
from shapely.affinity import scale
from area import area as areapolygon
from sklearn.cluster import KMeans
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime, timedelta

from data.circle_polygon import circle_polygon
from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.datacomplemento import main as datacomplemento

from data.getdatabuilding import main as getdatabuilding
from data.getdatalotescombinacion import getdatacombinacionlotes,mergedatabybarmanpre
from data.getdata_market_analysis import main as getdata_market_analysis
from data.getdataproyectosnuevos import main as getdataproyectosnuevos
from data.getuso_destino import usosuelo_class
from data.data_referencia_cabidas import valor_referencia_avaluo,cargas_fijas_variables

from modulos._busqueda_avanzada_descripcion_lote import analytics_transacciones

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
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass
 
    if st.session_state.access:
        landing(barmanpre,mapwidth,mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(barmanpre,mapwidth,mapheight):
    
    colm1,colm2 = st.columns([0.3,0.7])
    
    st.write('')
    titulo = 'Variables'
    html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
    texto  = BeautifulSoup(html, 'html.parser')
    st.markdown(texto, unsafe_allow_html=True)
    
    colf1,colf2 = st.columns(2)
    
    st.write('')
    titulo = 'Configuración'
    html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
    texto  = BeautifulSoup(html, 'html.parser')
    st.markdown(texto, unsafe_allow_html=True)
    
    colp1,colp2,colp3,colp4,colp5 = st.columns(5)
    with colf1:
        idc = st.number_input('índice de ocupación:',value=70,min_value=0,max_value=100)
        
    with colf2:
        pac = st.number_input('Porcentaje de área común en la planta:',value=20,min_value=0,max_value=100)
        pac = pac/100
        
    #-------------------------------------------------------------------------#
    # Data
    with st.spinner('Construyendo la Cabida'):
        
        datapredios,datalotescatastro,datausosuelo = getdatacombinacionlotes(barmanpre)

        polygon_wkt  = datapredios['wkt'].iloc[0]
        polygon      = wkt.loads(polygon_wkt)
        newpolygon   = reduce_polygon(polygon,idc)
        try:
            latitud  = polygon.centroid.y
            longitud = polygon.centroid.x
        except:
            latitud  = 4.690419
            longitud = -74.052086
            
        #-------------------------------------------------------------------------#       
        # Data de referencia avaluo terreno y comercial de la manzana y antejardin
        data_avaluo_ref,data_antejardin = valor_referencia_avaluo(latitud=None,longitud=None,polygon=str(polygon))

        #-------------------------------------------------------------------------#
        # Data vigencia y transacciones
        #-------------------------------------------------------------------------#
        datavigencia,datatransacciones_market,datadirecciones,datactl,_du,_dl = [pd.DataFrame()]*6
        input_transacciones = {}
        if isinstance(barmanpre, str) and barmanpre!='':
            barmanprelist = barmanpre.split('|')
            datadirecciones,_du,_dl,datavigencia,datatransacciones_market,datactl = getdatabuilding(barmanprelist)
            datalotescatastro = mergedatabybarmanpre(datalotescatastro.copy(),_du.copy(),['prenbarrio','formato_direccion','construcciones','prevetustzmin'])
            
        if not datatransacciones_market.empty and not datavigencia.empty:
            input_transacciones = analytics_transacciones(datatransacciones_market,datavigencia)
                
        #-------------------------------------------------------------------------#
        # Data complemento
        #-------------------------------------------------------------------------#
        precuso    = None
        direccion  = None
        if not _du.empty and 'formato_direccion' in _du:
            direccion = list(_du['formato_direccion'].unique())

        if not datausosuelo.empty and 'precuso' in datausosuelo: 
            precuso = list(datausosuelo['precuso'].unique())

        barmanprelist = barmanpre.split('|')
        input_complemento = datacomplemento(barmanpre=barmanprelist,latitud=latitud,longitud=longitud,direccion=direccion,polygon=polygon_wkt,precuso=precuso)
        try:    input_complemento['direcciones'] = ' | '.join(direccion)
        except: input_complemento['direcciones'] = ''

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
        areapoligonocompleto = datapredios['areapolygon'].iloc[0]
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
    

        with st.spinner('información del mercado'):
            
            #-----------------------------------------------------------------#
            # Agrupacion por tipologia
            datatipologias = pd.DataFrame(inputvar)
            datagrupada    = pd.DataFrame()
            precuso        = None
            duso           = usosuelo_class()
            if not datatipologias.empty:
                datagrupada         = datatipologias.groupby('tipoinmueble')['areavendible'].sum().reset_index()
                datagrupada.columns = ['tipoinmueble','areavendible']
                datagrupada['categoria'] = datagrupada['tipoinmueble'].replace(['Apartamento','Casa','Local','Bodega','Oficina'],['Residencial','Residencial','Comercio','Bodegas','Oficinas'])
                dusopaso = duso[duso['clasificacion'].isin(datagrupada['categoria'])]
                if not dusopaso.empty:
                    precuso = list(dusopaso['precuso'].unique())
                    
            #-----------------------------------------------------------------#
            # Datos de mercado
            
                #-------------------------------------------------------------#
                # Precios de transacciones
            polygon = str(circle_polygon(500,latitud,longitud))
            _dpredios,datacatastro_market,_dvigencia,datatransacciones_market,datamarket = getdata_market_analysis(polygon=polygon)
            #_dpredios,datacatastro_market,_dvigencia,datatransacciones_market,datamarket = getdata_market_analysis(polygon=polygon,precuso=precuso)

            if not datacatastro_market.empty and precuso is not None:
                datacatastro_market = datacatastro_market[datacatastro_market['precuso'].isin(precuso)]
            
            if not datatransacciones_market.empty and precuso is not None:
                datatransacciones_market = datatransacciones_market[datatransacciones_market['precuso'].isin(precuso)]
                datatransacciones_market['fecha_documento_publico'] = pd.to_datetime(datatransacciones_market['fecha_documento_publico'])
    
                #-------------------------------------------------------------#
                # Proyectos Nuevos
            datainfoproyectos = pd.DataFrame(columns=['tipoinmueble','cuantiamt2','precuso','metros'])
            metros_proyectos  = 0
            for metros_iter in [500,800,1000]:
                polygon_proyectos = str(circle_polygon(metros_iter,latitud,longitud))
                dataproyectos,dataformulada,datalongproyectos,datapricing = getdataproyectosnuevos(str(polygon_proyectos))
                if not datapricing.empty:
                    filtro_fecha = datetime.now() - timedelta(days=365)
                    datapricing  = datapricing[datapricing['fecha']>=filtro_fecha]
                if not datapricing.empty:
                    datamerge   = dataformulada.drop_duplicates(subset=['codproyecto','codinmueble'],keep='first')
                    datapricing = datapricing.merge(datamerge[['codproyecto','codinmueble','tipo']],on=['codproyecto','codinmueble'],how='left',validate='m:1')
                    
                    datapricing       = datapricing.resample('M', on='fecha').apply(lambda x: x.groupby('tipo')['valormt2'].max()).reset_index()
                    datainfoproyectos = []
                    vartipo           = list(datapricing)
                    vartipo.remove('fecha')
                    for j in vartipo:
                        datainfoproyectos.append({'tipoinmueble':j,'cuantiamt2':datapricing[j].median()})
                    datainfoproyectos = pd.DataFrame(datainfoproyectos)
                    if not datainfoproyectos.empty:
                        datainfoproyectos['precuso'] = datainfoproyectos['tipoinmueble'].apply(lambda x: inmueble2usosuelo([x])[-1] if isinstance(inmueble2usosuelo([x]),list) and inmueble2usosuelo([x])!=[] else None)
                        datainfoproyectos['metros']  = metros_iter 
                        metros_proyectos             = metros_iter
                        break

            #-----------------------------------------------------------------#
            # Data Tipologias
            valores_referencia = []
            if not datagrupada.empty:
                for tipoinmueble in datagrupada['tipoinmueble'].unique():
                    datan       = datagrupada[datagrupada['tipoinmueble']==tipoinmueble]
                    datan.index = range(len(datan))
                    precuso     = inmueble2usosuelo([tipoinmueble])
                    if isinstance(precuso, list) and precuso!=[]:
                        datapaso          = datatransacciones_market[datatransacciones_market['precuso'].isin(precuso)]
                        datapasoproyectos = datainfoproyectos[datainfoproyectos['precuso'].isin(precuso)]
                        if not datapaso.empty and 'codigo' in datapaso:
                            datapaso = datapaso[datapaso['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
                        if not datapaso.empty:
                            filtrodate    = datetime.now()-timedelta(days=365)
                            datapaso      = datapaso[datapaso['fecha_documento_publico']>=filtrodate]
                        
                        valormt2 = None
                        if not datapaso.empty: # Transacciones realizadas 
                            valormt2 = datapaso['cuantiamt2'].median()
                            fuente   = 'market'
                        if not datapasoproyectos.empty: # Proyectos nuevos
                            valormt2 = datapasoproyectos['cuantiamt2'].median()
                            fuente   = 'proyectos'
                        if valormt2 is not None:
                            areavendible  = datan['areavendible'].sum()
                            valorestimado = areavendible*valormt2
                            valores_referencia.append({'variable':tipoinmueble,'valormt2':valormt2,'areavendible':areavendible,'valorestimado':valorestimado,'fuente':fuente})
                        else: 
                            if not _dvigencia.empty:
                                dpaso = _dvigencia[_dvigencia['precuso'].isin(precuso)]
                                if not dpaso.empty:
                                    w         = dpaso.groupby('chip')['vigencia'].max().reset_index()
                                    w.columns = ['chip','vigencia_max']
                                    dpaso     = dpaso.merge(w,on='chip',how='left',validate='m:1')
                                    dpaso     = dpaso[dpaso['vigencia']==dpaso['vigencia_max']]
                                    dpaso     = dpaso.groupby('chip')['avaluomt2'].max().reset_index()
                                    
                                    valormt2      = dpaso['avaluomt2'].median()
                                    areavendible  = datan['areavendible'].sum()
                                    valorestimado = areavendible*valormt2
                                    valores_referencia.append({'variable':tipoinmueble,'valormt2':valormt2,'areavendible':areavendible,'valorestimado':valorestimado,'fuente':'market'})

            dataestimado = pd.DataFrame(valores_referencia)
            datamissing  = pd.DataFrame()
            if not datatipologias.empty:
                if not dataestimado.empty:
                    idd         = datatipologias['tipoinmueble'].isin(dataestimado['variable'])
                    datamissing = datatipologias[~idd][['tipoinmueble','areavendible']]
                else: 
                    datamissing = datatipologias[['tipoinmueble','areavendible']]
                if not datamissing.empty:
                    valormt2default              = 4000000
                    datamissing['valormt2']      = valormt2default
                    datamissing['valorestimado'] = datamissing['areavendible']*datamissing['valormt2']
                    datamissing.rename(columns={'tipoinmueble':'variable'},inplace=True)
                    idd         = datamissing['variable']=='Áreas comunes'
                    datamissing = datamissing[~idd]
                    datamissing['fuente'] = 'market'
                    dataestimado = pd.concat([dataestimado,datamissing])
                    
            if not dataestimado.empty:
                dataestimado['valormt2'] = dataestimado['valormt2'].apply(lambda x: int(x // 1000 * 1000) if (isinstance(x,float) or isinstance(x,int)) else None)
                datappend    = pd.DataFrame([{'variable':'Total','areavendible':dataestimado['areavendible'].sum(),'valormt2':'','valorestimado':dataestimado['valorestimado'].sum()}])
                dataestimado = pd.concat([dataestimado,datappend])
                
            st.write('')
            titulo = 'Precio por m²'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
        
            dataestimado.index   = range(len(dataestimado))
            datapricing          = dataestimado.copy()
            keycount             = 0
            for items in range(len(dataestimado)):
                colpr1,colpr2,colpr3 = st.columns([0.45,0.45,0.1])
                keycount += 1
                variable     = dataestimado['variable'].iloc[items] if 'variable' in dataestimado and isinstance(dataestimado['variable'].iloc[items],str) else ''
                valormt2     = dataestimado['valormt2'].iloc[items] if 'valormt2' in dataestimado else None
                tipoinmueble = dataestimado['variable'].iloc[items] 
                fuente       = dataestimado['fuente'].iloc[items] if 'fuente' in dataestimado and isinstance(dataestimado['fuente'].iloc[items],str) else None

                if isinstance(variable,str) and 'total' not in variable.lower():
                    with colpr1:
                        st.text_input('Tipo de inmueble' ,value=variable,key=f'tipoinmueble{keycount}')
                if valormt2 is not None:
                    try:
                        valormt2 = int(float(valormt2))
                        with colpr2:
                            valormt2 = st.number_input('Valor por m²' ,value=valormt2,key=f'valuetipoinmueble{keycount}')
                            datapricing.loc[items,'valormt2'] = valormt2
                        with colpr3:
                            st.write('')
                            st.write('')
                            st.write('')
                            barmanprelist = ''
                            if isinstance(barmanpre, str) and barmanpre!='':
                                barmanprelist = '|'.join(barmanpre.split('|'))
                            elif isinstance(barmanpre, list) and barmanpre!=[]:
                                barmanprelist = '|'.join(barmanpre)
                            
                            precuso     = inmueble2usosuelo(tipoinmueble) 
                            precusolist = ''
                            if isinstance(precuso, list) and precuso!=[]:
                                precusolist = '|'.join(precuso)
                            
                            urllink = f"http://www.urbex.com.co/Busqueda_avanzada?type=lote&code={barmanprelist}&vartype=barmanpre&_market_precuso={precusolist}&_market_select=edm&token={st.session_state.token}"
                            if isinstance(fuente,str) and 'proyectos' in fuente and metros_proyectos>0:
                                encryptjson = {'metros': metros_proyectos, 'latitud': latitud, 'longitud':longitud}
                                encryptjson = json.dumps(encryptjson)
                                encryptjson = encryptjson.encode('utf-8')
                                encryptjson = base64.b64encode(encryptjson)
                                encryptjson = encryptjson.decode('utf-8')

                                urllink = f"http://www.urbex.com.co/Análisis_de_mercado?type=polygon&modulo=proyectos&code={encryptjson}&token={st.session_state.token}"
                            style_button = """
                            <style>
                            .custom-button {
                                display: inline-block;
                                padding: 10px 20px;
                                background-color: #A16CFF;
                                color: white !important;
                                font-weight: bold;
                                text-decoration: none;
                                border-radius: 10px;
                                width: 100%;
                                height: 40px;
                                border: 0px solid #A16CFF;
                                cursor: pointer;
                                text-align: center;
                                letter-spacing: 0px;
                                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                                margin-bottom: 20px;
                            }
                            
                            .custom-button:hover {
                                background-color: #21D375;
                                color: white; 
                                border: 0px solid #21D375;
                            }
                            </style>
                            """
                            nombre = 'Detalle'
                            html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button}</head><body><a href="{urllink}" class="custom-button" target="_blank">{nombre}</a></body></html>"""
                            html = BeautifulSoup(html, 'html.parser')
                            st.markdown(html, unsafe_allow_html=True)  
                            #st.write('Ver de donde sale este numero')
                    except: pass
    
            for i in ['valormt2','areavendible','valorestimado']:
                datapricing[i] = pd.to_numeric(datapricing[i],errors='coerce')
            datapricing['valorestimado'] = datapricing['valormt2']*datapricing['areavendible']
            idd = datapricing['variable']=='Total'
            if sum(idd)>0:
                datapricing.loc[idd,'valorestimado'] = datapricing[~idd]['valorestimado'].sum()
            
            #-----------------------------------------------------------------#
            # Tabla de recaudo
            st.write('')
            titulo = 'Análisis de prefractibilidad'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            resumen = {'indiceocupacion':idc,'alturaconstruccion':alturabuilding,'areapoligonocompleto':areapoligonocompleto,'numero_pisos':numero_pisos,'areaplantas':areaplantas,'areatotalconstruida':areatotalconstruida,'areatotalvendible':areatotalvendible}
            html,conteo = htmlrecaudo(resumen=resumen,datapredios=datapredios,datatipologias=datatipologias,dataestimado=datapricing)
            st.components.v1.html(html,height=int(conteo*600/30),scrolling=True)
        
            #-----------------------------------------------------------------#
            # Tabla de resumen
            st.write('')
            titulo = 'Características del terreno'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            resumen = {'indiceocupacion':idc,'alturaconstruccion':alturabuilding,'areapoligonocompleto':areapoligonocompleto,'numero_pisos':numero_pisos,'areaplantas':areaplantas,'areatotalconstruida':areatotalconstruida,'areatotalvendible':areatotalvendible}
            html,conteo = principal_table(resumen={},datapredios=datapredios,datatipologias=datatipologias,datausosuelo=datausosuelo,input_complemento=input_complemento,input_transacciones=input_transacciones,data_antejardin=data_antejardin)
            st.components.v1.html(html,height=int(conteo*600/26),scrolling=True)
        
            #-----------------------------------------------------------------#
            # Calculadoras
            st.write('')
            titulo = 'Calculadoras de cargas'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
                # Avaluo de referencia del terreno, comercial y catastral
            avaluo_terreno = (data_avaluo_ref[data_avaluo_ref['grupopter'].isin(['LOTES'])]['vref'].max() if not data_avaluo_ref.empty else None)
            if pd.isna(avaluo_terreno): avaluo_terreno = None
            if not isinstance(avaluo_terreno, (float, int)) and not data_avaluo_ref.empty:
                avaluo_terreno = data_avaluo_ref['vref'].max()
                
            avaluo_comercial_manzana = (data_avaluo_ref[data_avaluo_ref['grupopter'].isin(['LOTES'])]['avaluocom'].max() if not data_avaluo_ref.empty else None)
            if pd.isna(avaluo_comercial_manzana): avaluo_comercial_manzana = None
            if not isinstance(avaluo_comercial_manzana, (float, int)) and not data_avaluo_ref.empty:
                avaluo_comercial_manzana = data_avaluo_ref['avaluocom'].max()
    
            avaluo_catastral_manzana = (data_avaluo_ref[data_avaluo_ref['grupopter'].isin(['LOTES'])]['avaluocat'].max() if not data_avaluo_ref.empty else None)
            if pd.isna(avaluo_catastral_manzana): avaluo_catastral_manzana = None
            if not isinstance(avaluo_catastral_manzana, (float, int)) and not data_avaluo_ref.empty:
                avaluo_catastral_manzana = data_avaluo_ref['avaluocat'].max()
    
            # Cargo:
            proyecto_options    = {"CONSTRUCCIÓN":"CONSTRUCCION", "URBANISMO":"URBANISMO"}
            uso_options         = {"VIVIENDA":"VIVIENDA", "OTROS USOS":"OTROS_USOS"}
            vivienda_options    = {"VIS":"INTERES_SOCIAL", "NO VIS":"NO_INTERES_SOCIAL"}
            composicion_options = {"UNIFAMILIAR":"UNIFAMILIAR","BIFAMILIAR":"BIFAMILIAR","MULTIFAMILIAR":"MULTIFAMILIAR"}
            modalidad_options   = {'OBRA NUEVA':'OBRA NUEVA', 'AMPLIACIÓN':'AMPLIACION', 'ADECUACIÓN':'ADECUACION', 'MODIFICACIÓN':'MODIFICACION', 'REFORZAMIENTO ESTRUCTURAL':'REFORZAMIENTO ESTRUCTURAL', 'DEMOLICION TOTAL':'DEMOLICION TOTAL', 'DEMOLICION PARCIAL':'DEMOLICION PARCIAL', 'CERRAMIENTO':'CERRAMIENTO'}
            estrato_options     = [1, 2, 3, 4, 5, 6]

            col1,col2 = st.columns(2)

            with col1: 
                tipo_proyecto_r = st.selectbox('Tipo de proyecto',options=list(proyecto_options))
                tipo_proyecto   = proyecto_options[tipo_proyecto_r]
            
            with col2:
                uso_proyecto_r = st.selectbox('Uso',options=list(uso_options))
                uso_proyecto   = uso_options[uso_proyecto_r]
            
            with col1: 
                isdisabled    = False if 'VIVIENDA' in uso_proyecto else True
                tipo_vivienda_r = st.selectbox('Tipo de vivienda',options=list(vivienda_options),disabled=isdisabled)
                tipo_vivienda   = vivienda_options[tipo_vivienda_r] 
                
            with col2: 
                isdisabled    = False if 'VIVIENDA' in uso_proyecto and 'CONSTRUCCION' in tipo_proyecto else True
                composicion_proyecto_r = st.selectbox('Composición',options=list(composicion_options),disabled=isdisabled)
                composicion_proyecto   = composicion_options[composicion_proyecto_r] 
                
            with col1: 
                isdisabled    = False if 'CONSTRUCCION' in tipo_proyecto else True
                modalidad_proyecto_r = st.selectbox('Modalidad',options=list(modalidad_options),disabled=isdisabled)
                modalidad_proyecto   = modalidad_options[modalidad_proyecto_r] 
                
            with col2: 
                isdisabled = False if 'VIVIENDA' in uso_proyecto else True
                estrato    = st.selectbox('Estrato',options=estrato_options,disabled=isdisabled)

            with col1: 
                area = st.number_input('Área',value=0,min_value=0)


            # Liquidación para Aumento de Edificabilidad
            with col2:
                avaluo_terreno      = int(avaluo_terreno) if isinstance(avaluo_terreno, (float, int)) else 0
                valorcatastralsuelo = st.number_input('Valor catastral del metro cuadrado del suelo',value=avaluo_terreno,min_value=0)
            with col1:
                area_adicional = st.number_input('Área de Construcción Adicional Deseada por Encima del Índice Básico',value=0,min_value=0)
                
            # Simulador de Liquidación del Valor a Compensar de Estacionamiento
            with col2:
                area_adicional_estacionamientos = st.number_input('Metros cuadrados de area adicional destinada a estacionamientos',value=0,min_value=0)
                 
            # Liquidacion Pago Compensatorio de Cesiones Públicas para Parques y Equipamientos
            with col1:
                areabrutaproyecto = st.number_input('Área Bruta del Proyecto Urbano Objeto de Licencia',value=0,min_value=0)
            with col2:
                areautilproyecto = st.number_input('Área Útil del Proyecto Urbano Objeto de Licencia',value=0,min_value=0)
            with col1:
                mtcompensar = st.number_input('Metros Cuadrados a Compensar',value=0,min_value=0)
           
 
            liq_aumento_edificabilidad,liq_compensar_estacionamiento,liq_compensacion_publico = [0]*3  
            
            # Liquidación para Aumento de Edificabilidad
            if valorcatastralsuelo>0 and area_adicional>0:
                liq_aumento_edificabilidad = -1.7917446413385605 + 0.9999963437314175*np.log(valorcatastralsuelo) + 1.0000024221145998*np.log(area_adicional)
                liq_aumento_edificabilidad = round_to_nearest(np.exp(liq_aumento_edificabilidad)) 
                    
            # Simulador de Liquidación del Valor a Compensar de Estacionamiento
            if valorcatastralsuelo>0 and area_adicional_estacionamientos>0:
                liq_compensar_estacionamiento = -2.995732273553994  + 1.0000000000000002*np.log(valorcatastralsuelo) + 1.0*np.log(area_adicional_estacionamientos)
                liq_compensar_estacionamiento = round_to_nearest(np.exp(liq_compensar_estacionamiento)) 
              
            # Liquidacion Pago Compensatorio de Cesiones Públicas para Parques y Equipamientos
            if valorcatastralsuelo>0 and areabrutaproyecto>0 and areautilproyecto>0 and mtcompensar>0:
                liq_compensacion_publico = 2.8346862204821655 + 0.8420028931572793*np.log(valorcatastralsuelo) + 0.8594449539498318*np.log(areabrutaproyecto) - 0.915169026757237*np.log(areautilproyecto) + 1.023125114022463*np.log(mtcompensar)
                liq_compensacion_publico = round_to_nearest(np.exp(liq_compensacion_publico)) 
                    
            data_carga_fija,data_carga_variable = cargas_fijas_variables(proyecto=tipo_proyecto,uso=uso_proyecto,vivienda=tipo_vivienda,composicion=composicion_proyecto,modalidad=modalidad_proyecto,estrato=estrato,area=area)

            results = [
                {'label':'Cargo Fijo:','value':data_carga_fija['total_cargo_fijo'].iloc[0],'output': f"${data_carga_fija['total_cargo_fijo'].iloc[0]:,.0f}" if not data_carga_fija.empty and 'total_cargo_fijo' in data_carga_fija and isinstance(data_carga_fija['total_cargo_fijo'].iloc[0],(float,int)) else '$0' },
                {'label':'Cargo Variable:','value':data_carga_variable['total_cargo_variable'].iloc[0],'output':f"${data_carga_variable['total_cargo_variable'].iloc[0]:,.0f}" if not data_carga_variable.empty and 'total_cargo_variable' in data_carga_variable and isinstance(data_carga_variable['total_cargo_variable'].iloc[0],(float,int)) else '$0' },
                {'label':'Liquidación para Aumento de Edificabilidad:','value':liq_aumento_edificabilidad,'output':f"${liq_aumento_edificabilidad:,.0f}" if isinstance(liq_aumento_edificabilidad,(float,int)) and liq_aumento_edificabilidad>0 else '$0'},
                {'label':'Liquidación del Valor a Compensar de Estacionamiento (Decreto 520 de 2022):','value':liq_compensar_estacionamiento,'output':f"${liq_compensar_estacionamiento:,.0f}" if isinstance(liq_compensar_estacionamiento,(float,int)) and liq_compensar_estacionamiento>0 else '$0'},
                {'label':'Pago Compensatorio de Cesiones Públicas para Parques y Equipamientos:','value':liq_compensacion_publico,'output':f"${liq_compensacion_publico:,.0f}" if isinstance(liq_compensacion_publico,(float,int)) and liq_compensacion_publico>0 else '$0'},
            ]
            inputs = [
                {'label':'Tipo de proyecto:','value':tipo_proyecto_r},
                {'label':'Uso del proyecto:','value':uso_proyecto_r},
                {'label':'Tipo de vivienda:','value':tipo_vivienda_r},
                {'label':'Composición del proyecto:','value':composicion_proyecto_r},
                {'label':'Modalidad:','value':modalidad_proyecto_r},
                {'label':'Estrato:','value':estrato},
                {'label':'Área:','value':area},
                {'label':'Valor catastral del metro cuadrado del suelo:','value':f"${valorcatastralsuelo:,.0f}" },
                {'label':'Área de Construcción Adicional Deseada por Encima del Índice Básico:','value':area_adicional},
                {'label':'Metros cuadrados de area adicional destinada a estacionamientos:','value':area_adicional_estacionamientos},
                {'label':'Área Bruta del Proyecto Urbano Objeto de Licencia:','value':areabrutaproyecto},
                {'label':'Área Útil del Proyecto Urbano Objeto de Licencia:','value':areautilproyecto},
                {'label':'Metros Cuadrados a Compensar:','value':mtcompensar},
                ]
            html,conteo = calculadorasHTML(inputs=inputs,results=results)
            st.components.v1.html(html,height=int(conteo*600/26),scrolling=True)

        
            #-----------------------------------------------------------------#
            # Tabla de normativa 
            #-----------------------------------------------------------------#
    



    # poner todos los demas edificios en 3D
    # poner en el resumen altura de las placas 
    # poner area de aislamiento (calcular le poligono restante) 
    # metricas o valores
    
    # Que edificios son similares a los que estan 
    # en cuanto se estan vendiendo 
    # quien los construyo (galeria inmobiliaria) 
    
    # Poner calculadoras VUC y Antejardin
    
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

def reduce_polygon(geometry, percentage):
    centroid     = geometry.centroid
    scale_factor = percentage / 100.0
    return scale(geometry, xfact=scale_factor, yfact=scale_factor, origin=centroid)

@st.cache_data(show_spinner=False)
def principal_table(resumen={},datapredios=pd.DataFrame(),datatipologias=pd.DataFrame(),datausosuelo=pd.DataFrame(),input_complemento={},input_transacciones={},data_antejardin=pd.DataFrame()):
   
    conteo = 0
    labelbarrio = ""
    try:
        if isinstance(input_complemento['barrio'], str): 
            labelbarrio = f"[{input_complemento['barrio'].title()}]"
    except: pass

    #---------------------------------------------------------------------#
    # Seccion Ubicaion
    tablaubicacion = ""
    html_paso = ""
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Dirección:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['direcciones']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Localidad:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['localidad']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Barrio:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['barrio']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Código UPL:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['codigoupl']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">UPL:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['upl']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Estrato:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{int(datapredios['estrato'].iloc[0])}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">LatLng:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['latlng']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    
    if html_paso!="":
        html_paso = f"""
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
        {html_paso}
        """
        conteo += 1
    if html_paso!="":
        
        labeltable     = "Ubicación"
        tablaubicacion = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaubicacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaubicacion}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion resumen general
    tablaresumen = ""
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
                conteo += 1
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
    # Terreno consildado
    tablaterreno = ""
    html_paso = ""
    
    try:    preaterre = f"{round(datapredios['preaterre'].iloc[0],2)}" 
    except: preaterre = None
    try:    preaconst = f"{round(datapredios['preaconst'].iloc[0],2)}" 
    except: preaconst = None
    try:    lotes = f"{int(datapredios['lotes'].iloc[0])}" 
    except: lotes = None
    try:    prediostotal = f"{int(datapredios['predios_total'].iloc[0])}" 
    except: prediostotal = None
    try:    pisos = f"{int(datapredios['pisos'].iloc[0])}" 
    except: pisos = None
    try:    sotanos = f"{int(datapredios['sotanos'].iloc[0])}" 
    except: sotanos = None
    try:    propietarios = f"{int(datapredios['propietarios'].iloc[0])}" 
    except: propietarios = None
    try:    avaluo = f"${int(datapredios['avaluo_catastral'].iloc[0]):,.0f}" 
    except: avaluo = None
    try:    predial = f"${int(datapredios['predial'].iloc[0]):,.0f}" 
    except: predial = None
    try:    esquinero = "Si" if datapredios['predial'].iloc[0]==1 else "No"
    except: esquinero = None
    try:    viaprincipal = "Si" if datapredios['tipovia'].iloc[0]==1 else "No"
    except: viaprincipal = None
    
    formato = {"Área de terreno":preaterre,"Área construida":preaconst,"Número de lotes":lotes,
               "Total de predios":prediostotal,"Pisos máximos":pisos,"Sotanos máximos":sotanos,
               "Esquinero":esquinero,"Vía principal":viaprincipal,
               "Propietarios":propietarios,"Avaúo catastral total":avaluo,"Predial total":predial,
               }
    
    for key,value in formato.items():
        if value is not None: 
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{value}</h6></td>
            </tr>"""
            conteo += 1
    if html_paso!="":
        labeltable     = "Terreno consolidado"
        tablaterreno = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaterreno = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaterreno}</tbody></table></div></div>"""

    #-------------------------------------------------------------------------#
    # Seccion Transacciones
    tablatransacciones = ""
    try:    transacciones_total = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(input_transacciones['transacciones_total'])}</h6></td></tr>"""  if (isinstance(input_transacciones['transacciones_total'],float) or isinstance(input_transacciones['transacciones_total'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: transacciones_total = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""  
    try:    valortrasnacciones = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${round(input_transacciones['valortrasnacciones'],2):,.0f} m²</h6></td></tr>""" if (isinstance(input_transacciones['valortrasnacciones'],float) or isinstance(input_transacciones['valortrasnacciones'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: valortrasnacciones = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    try:    transacciones_lastyear = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(input_transacciones['transacciones_lastyear'])}</h6></td></tr>"""  if (isinstance(input_transacciones['transacciones_lastyear'],float) or isinstance(input_transacciones['transacciones_lastyear'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: transacciones_lastyear = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    try:    valortrasnacciones_lastyear = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${round(input_transacciones['valortransacciones_lastyear'],2):,.0f} m²</h6></td></tr>""" if (isinstance(input_transacciones['valortransacciones_lastyear'],float) or isinstance(input_transacciones['valortransacciones_lastyear'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: valortrasnacciones_lastyear = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    
    titulo    = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Último año</h6></td></tr>"""
    html_paso = f"""
    {titulo}
    <tr><td style="border: none;"><h6></h6></td></tr>
    {valortrasnacciones_lastyear}
    {transacciones_lastyear}
    <tr><td style="border: none;"><h6></h6></td></tr>
    """
    
    titulo     = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Desde el 2019 a la fecha</h6></td></tr>"""
    html_paso += f"""
    {titulo}
    <tr><td style="border: none;"><h6></h6></td></tr>
    {valortrasnacciones}
    {transacciones_total}
    <tr><td style="border: none;"><h6></h6></td></tr>
    """   
    if html_paso!="":
        conteo += 6
        labeltable         = "Transacciones"
        tablatransacciones = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablatransacciones = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatransacciones}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion Tipologias
    datausosuelo.index = range(len(datausosuelo))
    tablatipologia     = ""
    if len(datausosuelo)>0:
        html_paso = ""
        areatotalconstruida = datausosuelo['preaconst_precuso'].sum()
        for i in range(len(datausosuelo)):
            try:    usosuelo = datausosuelo['usosuelo'].iloc[i]
            except: usosuelo = ''            
            try:    areaconstruida = round(datausosuelo['preaconst_precuso'].iloc[i],2)
            except: areaconstruida = ''       
            try:    areaterreno = round(datausosuelo['preaterre_precuso'].iloc[i],2)
            except: areaterreno = '' 
            try:    predios = int(datausosuelo['predios_precuso'].iloc[i])
            except: predios = ''                 
            try:    proporcion = f"{round(datausosuelo['preaconst_precuso'].iloc[i]/areatotalconstruida,2):,.1%}" 
            except: proporcion = ''
            conteo    += 1
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{usosuelo}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{predios}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaconstruida}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{proporcion}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaterreno}</h6></td>
            </tr>
            """
        html_paso = f"""
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Predios</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área construida</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Proporción</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área de terreno</h6></td>
        {html_paso}
        """
        if html_paso!="":
            labeltable     = "Tipologías actuales del lote"
            tablatipologia = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablatipologia = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablatipologia}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # POT
    tablapot  = ""
    html_paso = ""
    if 'POT' in input_complemento and input_complemento['POT']!=[]:
        
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
                
    if not data_antejardin.empty:
        html_paso += f"""
        <tr><td style="border: none;"><h6></h6></td></tr>
        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">Antejardín:</h6></td></tr>
        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Dimensión</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{data_antejardin['dimension'].iloc[0]}</h6></td></tr>
        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Nota</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{data_antejardin['nota'].iloc[0]}</h6></td></tr>
        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Observación</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{data_antejardin['observacio'].iloc[0]}</h6></td></tr>
        """

    if html_paso!="":
        labeltable     = "P.O.T"
        tablapot = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablapot = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablapot}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion Condiciones de mercado
    tablavalorizacion = ""
    if 'valorizacion' in input_complemento and isinstance(input_complemento['valorizacion'], list):
        html_paso     = ""
        df            = pd.DataFrame(input_complemento['valorizacion'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        variables     = [var for var in list(df) if var not in ['tipoinmueble']]
        tipoinmuebles = list(df['tipoinmueble'].unique())
        k             = len(tipoinmuebles)
        if 'valormt2'     in df: df['valormt2']     = df['valormt2'].apply(lambda x:     f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else '')
        if 'valorizacion' in df: df['valorizacion'] = df['valorizacion'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valorización:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{x:.2%}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else '')
        if 'tiponegocio'  in df: df['tiponegocio']  = df['tiponegocio'].apply(lambda x:  f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{x.title()}:</h6></td></tr>"""   if not pd.isnull(x) and isinstance(x, str)  else '')

        for i in tipoinmuebles:
            datapaso           = df[df['tipoinmueble']==i]
            datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
            titulo = ""
            if k>1: titulo = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: center;">{i.title()}:</h6></td></tr>"""
            conteo    += 1
            html_paso += f"""
            {titulo}
            <tr><td style="border: none;"><h6></h6></td></tr>
            {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
            <tr><td style="border: none;"><h6></h6></td></tr>
            """
    if html_paso!="":
        labeltable         = f"Precios de referencia {labelbarrio}"
        tablavalorizacion = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablavalorizacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavalorizacion}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion Demografica
    tablademografica = ""
    if 'dane' in input_complemento:
        html_paso = ""
        for key,value in input_complemento['dane'].items():
            try: 
                valor = "{:,}".format(int(value))
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{valor}</h6></td></tr>"""
                conteo    += 1
            except: pass
        if html_paso!="":
            labeltable     = f"Información Demográfica {labelbarrio}"
            tablademografica = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablademografica = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablademografica}</tbody></table></div></div>"""
        
    #---------------------------------------------------------------------#
    # Seccion Transporte
    tablatransporte = ""
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        labeltable     = "Transmilenio"
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
    tablasitp = ""
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        labeltable     = "SITP"
        tablasitp = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablasitp = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablasitp}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion Vias
    tablavias = ""
    if 'vias' in input_complemento and isinstance(input_complemento['vias'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['vias']}</h6></td></tr>"""
        labeltable     = "Vías"
        tablavias = f"""
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
      <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: 0px;">
        <div class="row">
          <div class="col-md-12 mb-md-0 mb-2">
            <div class="card h-100">
              <div class="card-body p-3">
                <div class="container-fluid py-4">
                  <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                    {tablaubicacion}
                    {tablaresumen}
                    {tablaterreno}
                    {tablatransacciones}
                    {tablatipologia}
                    {tablapot}
                    {tablavalorizacion}
                    {tablademografica}
                    {tablatransporte}
                    {tablasitp}
                    {tablavias}
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
    return html,conteo

def htmlrecaudo(resumen={},datapredios=pd.DataFrame(),datatipologias=pd.DataFrame(),dataestimado=pd.DataFrame()):
    
    conteo = 1
    #---------------------------------------------------------------------#
    # Seccion Tipologias
    tablacomposicion = "" 
    if not datatipologias.empty:
        html_paso   = ""
        for j in ['1','2+']:
            conteo     += 1
            dataP       = datatipologias[datatipologias['planta']==j]
            dataP.index = range(len(dataP))
            conteotabla = -1
            spaceline   = ""
            if '1' in j:
                titulo     = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Planta 1</h6></td></tr>"""
                titulov    = ['']*len(dataP)
                titulov[0] = titulo
                
            for i in range(len(dataP)):
                if '2+' in j:
                    titulo  = f'Planta {dataP["pisomin"].iloc[i]}-{dataP["pisomax"].iloc[i]}'
                    titulo  = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{titulo}</h6></td></tr>"""
                    titulov = [titulo]
                    conteotabla = -1
                    spaceline = """<tr><td style="border: none;"><h6></h6></td></tr>"""
                    
                conteotabla += 1
                htmlline     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['tipoinmueble'].iloc[i]}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['porcentaje'].iloc[i]*100:,.1f}%</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{dataP['areavendible'].iloc[i]:,.2f}</h6></td></tr>"""
                html_paso   += f"""
                {spaceline}
                {titulov[conteotabla]}
                {spaceline}
                {htmlline}
                {spaceline}
                """
        if html_paso!="":
            labeltable      = "Tipologías"
            tablacomposicion = f"""
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
            tablacomposicion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablacomposicion}</tbody></table></div></div>"""
    
    
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
            conteo      += 8
            labeltable   = "Recaudo potencial estimado:"
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
    # Seccion resumen general
    tablaresumen = ""
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
                conteo += 1
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
    # Terreno consildado
    tablaterreno = ""
    html_paso = ""

    try:    avaluo = f"${int(datapredios['avaluo_catastral'].iloc[0]):,.0f}" 
    except: avaluo = None
    try:    predial = f"${int(datapredios['predial'].iloc[0]):,.0f}" 
    except: predial = None

    formato = {"Avaúo catastral total":avaluo,"Predial total":predial}
    
    for key,value in formato.items():
        if value is not None: 
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{value}</h6></td>
            </tr>"""
            conteo += 1
    if html_paso!="":
        labeltable     = "Avaúo y predial"
        tablaterreno = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaterreno = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaterreno}</tbody></table></div></div>"""

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
                    {tablaresumen}
                    {tablacomposicion}
                    {tablavalores}
                    {tablaterreno}
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
    return html,conteo

@st.cache_data(show_spinner=False)
def calculadorasHTML(inputs={},results={}):
    
    #---------------------------------------------------------------------#
    # Seccion Inputs
    tablainputs = ""
    html_paso   = ""
    conteo      = 1
    for items in inputs:
        conteo    += 1
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{items['label']}</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{items['value']}</h6></td>
        </tr>"""
    if html_paso!="":
        
        labeltable     = "Variables"
        tablainputs = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablainputs = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablainputs}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion Resultados
    tablaresultados = ""
    html_paso       = ""
    
    total = 0 
    for items in results:
        value = 0
        if 'value' in items: 
            value = items['value'] if isinstance(items['value'],(float,int)) and items['value']>0 else 0  
        if value>0:
            total += value
    if total>0:
        results.append({'label':'<b>Total</b>','output':f"<b>${total:,.0f}</b>" if isinstance(total,(float,int)) and total>0 else None})
    for items in results:
        if 'label' in items and items['label'] is not None:
            #conteo    += 1
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{items['label']}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{items['output']}</h6></td>
            </tr>"""
    if html_paso!="":
        
        labeltable     = "Liquidación"
        tablaresultados = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaresultados = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaresultados}</tbody></table></div></div>"""
    
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
                    {tablainputs}
                    {tablaresultados}
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
    return html,conteo

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

def round_to_nearest(value):
    # Determinar el factor de redondeo según el tamaño del valor
    if value < 10_000_000:
        factor = 10_000
    elif value < 100_000_000:
        factor = 100_000
    else:
        factor = 1_000_000
    rounded_value = round(value / factor) * factor
    return rounded_value
