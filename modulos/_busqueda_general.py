import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from datetime import datetime

from display.stylefunctions  import style_function_geojson
from display.puntos_descripcion_usuarios import pasosApp,procesoCliente


from functions._principal_getdatalotes import main as getdatalotes
from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon

from data.tracking import savesearch,update_save_status
from data._params_to_direccion import chip2direccion,matricula2direccion,buildinglist
from data.barmanpreFromgrupo import grupoFrombarmanpre

from display.style_white import style 

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_default':None,
               'reporte_busqueda_default':False,
               'data_lotes_busqueda': pd.DataFrame(),
               'geojson_data_busqueda_default':None,
               'zoom_start_data_busqueda_default':12,
               'latitud_busqueda_default':4.652652, 
               'longitud_busqueda_default':-74.077899,
               'direccion':None,
               'barmanpre_ref':[],
               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'

    #-------------------------------------------------------------------------#
    # Clasificacion / uso del suelo
    datauso = usosuelo_class()

    #-------------------------------------------------------------------------#
    # Guardar la consulta 
    if isinstance(st.session_state.token,str) and st.session_state.token!='' and isinstance(st.session_state.id_consulta,int):
        colf1,colf2,colf3 = st.columns([0.66,0.24,0.1])
        with colf2:
            if st.session_state.favorito is False:
                on = st.toggle('Guardar en favoritos',False)
                if on:
                    with st.spinner('Guardando'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,1):
                            st.session_state.favorito = True
                            st.rerun()
            if st.session_state.favorito:
                on = st.toggle('Guardado',True)
                if on is False:
                    with st.spinner('Removiendo'):
                        if update_save_status(st.session_state.id_consulta,st.session_state.token,0):
                            st.session_state.favorito = False
                            st.rerun()
                            
    #-------------------------------------------------------------------------#
    # Proceso
    col1p,col2p,col3p = st.columns([1,2,1])
    with col2p:
        if st.session_state.geojson_data_busqueda_default is None and st.session_state.data_lotes_busqueda.empty:
            html = procesoCliente(1)
        elif st.session_state.geojson_data_busqueda_default is not None and st.session_state.data_lotes_busqueda.empty:
            html = procesoCliente(3)
        elif not st.session_state.data_lotes_busqueda.empty:
            html = procesoCliente(5)
        st.components.v1.html(html, height=100, scrolling=True)
    
    #-------------------------------------------------------------------------#
    # Busqueda por direccion 
    col1paso,col2paso = st.columns([9,3],vertical_alignment='center')
    col1text,col2text = st.columns([0.3,0.6],vertical_alignment='center')
    if screensize>1280:
        col1,col2,col3,col4,col5 = st.columns([0.3,0.15,0.3,0.15,0.1],vertical_alignment='center')
    else:
        col1, col2, col3 = st.columns([0.4,0.2,0.4],vertical_alignment='center')
        col4, col5 = st.columns([0.4,0.6],vertical_alignment='center')
    
    with col1:
        formato_options = {'En un poligono':1,'Por dirección':2,'Por chip':3,'Por matrícula inmobiliria':4,'Nombre de la copropiedad':5}
        consulta        = st.selectbox('Tipo de busqueda:',options=list(formato_options))
        option_selected = formato_options[consulta]

    if option_selected==1:
        if st.session_state.data_lotes_busqueda.empty:
            with col1paso:
                html = pasosApp(1, 'Seleccionar el tipo de búsqueda', 'Hay diferentes formas de ubicar un predio en el mapa, selecciona una de ellas. <br><i class="fa-solid fa-hexagon" style="color: #A16CFF;"></i> La opción <b>"En un poligono"</b> permite delimitar un poligono en el mapa y ubicar todos los lotes que están contenidos')
                st.markdown(html, unsafe_allow_html=True)
            
    elif option_selected>1:
        with col2:
            ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
            
        with col3:
            if option_selected==3:
                if st.session_state.data_lotes_busqueda.empty:
                    with col1paso:
                        html = pasosApp(1, 'Ubicar el lote', 'A partir del chip se busca la dirección, una vez encontrado se debe hacer <b>clic</b> en el botón que dice <b>"Ubicar en el mapa"</b> para verificar que el lote se encontró de manera exitosa')
                        st.markdown(html, unsafe_allow_html=True)
                chip = st.text_input('Chip:',value='',placeholder="Ej: AAA0158QWET")
                if isinstance(chip,str) and chip!='':
                    chip = chip.strip()
                    with col5:
                        if st.button('Buscar chip'):
                            st.session_state.direccion = chip2direccion(chip)
                            if not (isinstance(st.session_state.direccion,str) and st.session_state.direccion!=''):
                                with col1text:
                                    st.error('Chip no encontrado')
                            else:
                                with col1text:
                                    st.success('Chip encontrado con exito!')
                                
            if option_selected==4:
                if st.session_state.data_lotes_busqueda.empty:
                    with col1paso:
                        html = pasosApp(1, 'Ubicar el lote', 'A partir de la matrícula inmobiliaria se busca la dirección, una vez encontrado se debe hacer <b>clic</b> en el botón que dice <b>"Ubicar en el mapa"</b> para verificar que el lote se encontró de manera exitosa')
                        st.markdown(html, unsafe_allow_html=True)
                matricula = st.text_input('Matrícula inmobiliria:',value='',placeholder="Ej: 50N20612425")
                if isinstance(matricula,str) and matricula!='':
                    matricula = matricula.strip()
                    with col5:
                        if st.button('Buscar matrícula'):
                            st.session_state.direccion = matricula2direccion(matricula)
                            if not (isinstance(st.session_state.direccion,str) and st.session_state.direccion!=''):
                                with col1text:
                                    st.error('Matrícula no encontrado')
                            else:
                                with col1text:
                                    st.success('Matrícula encontrado con exito!')
                                    
            if option_selected==5:
                if st.session_state.data_lotes_busqueda.empty:
                    with col1paso:
                        html = pasosApp(1, 'Ubicar el lote', 'A partir del nombre de la copropiedad de la propiedad horizontal se busca la dirección, una vez encontrado se debe hacer <b>clic</b> en el botón que dice <b>"Ubicar en el mapa"</b> para verificar que el lote se encontró de manera exitosa')
                        st.markdown(html, unsafe_allow_html=True)
                dataoptions = buildinglist()
                if not dataoptions.empty:
                    lista       = list(sorted(dataoptions['nombre_conjunto'].unique()))
                    copropiedad = st.selectbox('Nombre de la copropiedad:',options=lista)    
                    if isinstance(copropiedad,str) and copropiedad!='':
                        direcciones = list(dataoptions[dataoptions['nombre_conjunto']==copropiedad]['direccion'].unique())
                        direcciones = [x.strip() for x in direcciones if isinstance(x,str)]
                        if isinstance(direcciones,list) and direcciones!=[]:
                            if len(direcciones)>1:
                                st.session_state.direccion = st.selectbox('Dirección:',options=direcciones)  
                            else:
                                st.session_state.direccion = direcciones[0]

            if option_selected==2:
                if st.session_state.data_lotes_busqueda.empty:
                    with col1paso:
                        html = pasosApp(1, 'Ubicar el lote', 'Se debe poner la dirección, luego se debe hacer <b>clic</b> en el botón que dice <b>"Ubicar en el mapa"</b>')
                        st.markdown(html, unsafe_allow_html=True)
                st.session_state.direccion = st.text_input('Dirección:',value='',placeholder="Ej: Calle 134 19A 25")   

        with col4:
            metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=0)   
        
        disabled = False if isinstance(st.session_state.direccion,str) and st.session_state.direccion!='' and metros<=500 else True
        with col5:
            if st.button('Ubicar en el mapa',disabled=disabled):
                st.session_state.latitud_busqueda_default,st.session_state.longitud_busqueda_default, st.session_state.barmanpre_ref = getlatlng(f'{st.session_state.direccion},{ciudad.lower()},colombia')
                st.session_state.polygon_busqueda_default         = circle_polygon(metros,st.session_state.latitud_busqueda_default,st.session_state.longitud_busqueda_default)
                st.session_state.geojson_data_busqueda_default    = mapping(st.session_state.polygon_busqueda_default)
                st.session_state.zoom_start_data_busqueda_default = 16
                st.rerun()

    if isinstance(st.session_state.barmanpre_ref,list) and len(st.session_state.barmanpre_ref)==1:
        with col5:
            barmanpre2grupo = grupoFrombarmanpre(barmanpre=st.session_state.barmanpre_ref)
            gruporef        = barmanpre2grupo['grupo'].iloc[0] if not barmanpre2grupo.empty and 'grupo' in barmanpre2grupo else None
            try: gruporef   = int(gruporef)
            except: pass
            if isinstance(gruporef,int) and gruporef>0:
                params       = {'type':'predio','grupo':gruporef,'barmanpre':st.session_state.barmanpre_ref[0],'token':st.session_state.token}
                params       = json.dumps(params)
                params       = base64.urlsafe_b64encode(params.encode()).decode()
                params       = urllib.parse.urlencode({'token': params})
                urlexport    = "http://www.urbex.com.co/Reporte"
                urllink      = f"{urlexport}?{params}"
                nombre       = 'Ir al reporte'
        
                style_button_dir = """
                <style>
                .custom-button {
                    display: inline-block;
                    padding: 5px 5px; /* Reducido el padding para menor altura */
                    background-color: #A16CFF;
                    color: #ffffff !important; /* Siempre blanco */
                    font-weight: bold;
                    font-size: 14px; /* Mantiene el tamaño de letra */
                    text-decoration: none;
                    border-radius: 8px; /* Borde más pequeño para menor tamaño */
                    width: 100%;
                    border: 2px solid #A16CFF;
                    cursor: pointer;
                    text-align: center;
                    letter-spacing: 1px;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); /* Menor sombra para compactar */
                    margin-bottom: 0px; /* Espaciado inferior reducido */
                }
                .custom-button:hover {
                    background-color: #7F4BFF;
                    color: #ffffff !important; /* Asegura que siga siendo blanco */
                    border: 2px solid #7F4BFF;
                }
                .custom-button:active {
                    background-color: #FFF;
                    color: #ffffff !important; /* Mantiene blanco incluso en clic */
                    border: 2px solid #A16CFF;
                    outline: none;
                }
                
                /* Asegurar que los enlaces <a> también tengan letra blanca */
                .custom-button a {
                    color: #ffffff !important;
                    text-decoration: none;
                }
                </style>
                """
                # Agregar estilos y botón en Markdown sin usar BeautifulSoup
                st.markdown(style_button_dir, unsafe_allow_html=True)
                st.markdown(f'<a href="{urllink}" class="custom-button" target="_blank" style="text-decoration: none;">{nombre}</a>', unsafe_allow_html=True)

    st.markdown('<div style="padding: 30px;"></div>', unsafe_allow_html=True)

    #-------------------------------------------------------------------------#
    # Formulario      
    col1paso,col2paso = st.columns([0.3,0.7])   
    if st.session_state.geojson_data_busqueda_default is not None and st.session_state.data_lotes_busqueda.empty:
        with col1paso:
            html = pasosApp(3, 'Filtros:', 'Estos filtros permiten segmentar los tipos de lotes que aparecen en el mapa.  <br> Al final de los filtros se pasa al punto <div class="circle_small">4</div> para realizar la búsqueda')
            st.markdown(html, unsafe_allow_html=True)
        
        with col2paso:
            html = pasosApp(2, 'Poligono:', 'Verifica que el poligono cubra el área donde está el predio')
            st.markdown(html, unsafe_allow_html=True)
    
    if not st.session_state.data_lotes_busqueda.empty:
        with col2paso:
            texto_adicional = '[El poligono de color verde hace referencia a la dirección o predio]' if (isinstance(st.session_state.barmanpre_ref,str) and st.session_state.barmanpre_ref!='') or (isinstance(st.session_state.barmanpre_ref,list) and st.session_state.barmanpre_ref!=[]) else ''
            html = pasosApp(5, 'Selección del lote o predio:', f'En el mapa aparecen todos los lotes que están contenidos en el poligono y que cumplen con los filtros. Para acceder a un predio se debe hacer: <br> (1) <b>Clic</b> en el lote {texto_adicional}<br> (2) Para entrar al lote se debe hacer <b>clic</b> en el texto que aparece con la descripción del lote')
            st.markdown(html, unsafe_allow_html=True)
            
    col1,col2 = st.columns([0.3,0.7])      
    with col1: 
        
        #lista        = ['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero']
        lista         = list(sorted(datauso['clasificacion'].unique()))
        lista         = ['Todos'] + lista
        
        seleccion     = st.multiselect('Tipo de inmueble(s)', key='seleccion',options=lista, default=['Todos'],placeholder='Selecciona uno o varios inmuebles')
        areamin       = st.number_input('Área construida mínima',value=0,min_value=0)
        areamax       = st.number_input('Área construida máxima',value=0,min_value=0)
        estratomin    = st.number_input('Estrato mínima',value=0,min_value=0)
        estratomax    = st.number_input('Estrato máximo',value=0,min_value=0)
        antiguedadmin = st.number_input('Año de construido desde (yyyy)',value=0,min_value=0)
        antiguedadmax = st.number_input('Año de construido hasta (yyyy)',value=datetime.now().year,min_value=0)

    #-------------------------------------------------------------------------#
    # Mapa
    with col2:
        m = folium.Map(location=[st.session_state.latitud_busqueda_default, st.session_state.longitud_busqueda_default], zoom_start=st.session_state.zoom_start_data_busqueda_default,tiles="cartodbpositron")
        
        if st.session_state.data_lotes_busqueda.empty and option_selected==1:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
        if st.session_state.geojson_data_busqueda_default is not None:
            folium.GeoJson(st.session_state.geojson_data_busqueda_default, style_function=style_function_color).add_to(m)

        if not st.session_state.data_lotes_busqueda.empty:
            
            geojson = data2geopandas(st.session_state.data_lotes_busqueda, st.session_state.barmanpre_ref)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
        if st.session_state.data_lotes_busqueda.empty:
            st_map = st_folium(m,width=int(mapwidth*0.6),height=700,key=st.session_state.mapkey)

            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                                       = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_busqueda_default         = Polygon(coordenadas[0])
                        st.session_state.geojson_data_busqueda_default    = mapping(st.session_state.polygon_busqueda_default)
                        polygon_shape                                     = shape(st.session_state.geojson_data_busqueda_default)
                        centroid                                          = polygon_shape.centroid
                        st.session_state.latitud_busqueda_default         = centroid.y
                        st.session_state.longitud_busqueda_default        = centroid.x
                        st.session_state.zoom_start_data_busqueda_default = 16
                        st.rerun()
        else:
            folium_static(m,width=int(mapwidth*0.6),height=700)
            
    col1paso,col2paso = st.columns([0.3,0.7])
    col1,col2,col3    = st.columns([0.15,0.15,0.7],vertical_alignment='center')  
    cols1,cols2       = st.columns([0.3,0.7])
    
    if st.session_state.geojson_data_busqueda_default is not None and st.session_state.data_lotes_busqueda.empty:
        with col1paso:
            html = pasosApp(4, 'Búsqueda:', 'Una vez selecciondo el poligono en el mapa te aparece el botón de búsqueda <br> Al hacer <b>clic</b> puedes buscar todos los predios que están definidos en el poligono <br> O puedes resetear la búsqueda para hacer una nueva')
            st.markdown(html, unsafe_allow_html=True)
        
    with col1:
        if st.button('Resetear'):
            
            variable_reset = formato.copy()
            del variable_reset['token']
            for key,value in variable_reset.items():
                del st.session_state[key]
            st.rerun()
                    
    if st.session_state.polygon_busqueda_default is not None:
        with col2:
            if st.button('Buscar'):
                inputvar = {
                    'tipoinmueble':seleccion,
                    'areamin':areamin,
                    'areamax':areamax,
                    'antiguedadmin':antiguedadmin,
                    'antiguedadmax':antiguedadmax,
                    'estratomin':estratomin,
                    'estratomax':estratomax,
                    'polygon':str(st.session_state.polygon_busqueda_default)
                    }
                with cols1:
                    with st.spinner('Buscando informacion'):
                        st.session_state.data_lotes_busqueda = getdatalotes(inputvar=inputvar)
                        st.session_state.reporte_busqueda_default = True
                
                # Guardar:
                _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_busqueda_general', inputvar)
                st.rerun()
                
    if st.session_state.reporte_busqueda_default and st.session_state.data_lotes_busqueda.empty:
        with col3:
            st.error('No se encontraron predios que cumplen con las características')

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }


@st.cache_data(show_spinner=False)
def data2geopandas(data, barmanpre_ref=None):
    
    try: 
        variables = data.select_dtypes(include=['datetime64[ns]', 'timedelta64[ns]']).columns
        if isinstance(variables,list) and variables!=[]:
            data = data.drop(columns=variables)
        data = getitems(data)
    except: pass
        
        
    urlexport = "http://www.urbex.com.co/Reporte"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
        
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        
        if isinstance(barmanpre_ref,list) and barmanpre_ref!=[] and 'barmanpre' in data:
            idd = data['barmanpre'].isin(barmanpre_ref)
            if sum(idd)>0:
                data.loc[idd,'color'] = '#003F2D'
            
        for idd,items in data.iterrows():
        
            params       = {'type':'predio','grupo':items['grupo'],'barmanpre':items['barmanpre'],'token':st.session_state.token}
            params       = json.dumps(params)
            params       = base64.urlsafe_b64encode(params.encode()).decode()
            params       = urllib.parse.urlencode({'token': params})
            
            urllink      = f"{urlexport}?{params}"
            buildinfinfo = ""

            try:    buildinfinfo += f"""<b> Dirección:</b> {items['formato_direccion']}<br>""" if isinstance(items['formato_direccion'],str) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Nombre Edificio:</b> {items['nombre_conjunto']}<br>""" if isinstance(items['nombre_conjunto'],str) else ''
            except: pass     
            try:    buildinfinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """ if isinstance(items['prenbarrio'],str) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br>  """ if isinstance(items['estrato'],(float,int)) and items['estrato']>0 else ''
            except: pass
            try:    buildinfinfo += f"""<b> Área construida total:</b> {items['preaconst']:.2f}<br>""" if isinstance(items['preaconst'],(float,int)) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Área de terreno total:</b> {items['preaterre']:.2f}<br>""" if isinstance(items['preaterre'],(float,int)) else ''
            except: pass
            try:    buildinfinfo += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>""" if isinstance(items['prevetustzmin'],(float,int)) else ''
            except: pass            
            try:    buildinfinfo += f"""<b> Total de predios:</b> {int(items['predios'])}<br> """ if isinstance(items['predios'],(float,int)) else ''
            except: pass                    
            try:    buildinfinfo += f"""<b> Número transacciones:</b> {int(items['numero_transacciones'])}<br> """
            except: pass    
            # <a href="{urllink}" target="_blank" style="color: black; text-decoration: none;">
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {buildinfinfo}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def getitems(data):
    
    datamerge = data[['barmanpre']]
    formato   = [
        {'column':'general_catastro','variables':['barmanpre','formato_direccion', 'prenbarrio', 'preaconst', 'preaterre', 'prevetustzmin', 'estrato', 'predios']},
        {'column':'nombre_ph','variables':['barmanpre','nombre_conjunto']},
        {'column':'localizacion','variables':['barmanpre','locnombre']}
                 ]
    for i in formato:
        item       = i['column']
        variables  = i['variables']
        df         = data[['barmanpre',item]]
        df         = df[df[item].notnull()]
        df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df[df[item].notnull()]
        df         = df.explode(item)
        df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
        df         = pd.DataFrame(df)
        if not df.empty:
            df.columns = ['formato']
            df         = pd.json_normalize(df['formato'])
            if isinstance(variables,list) and variables!=[]:
                df     = df[variables]
                df     = df.sort_values(by=variables, na_position='last')
        if not df.empty:
            datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
            
    dataresultado = data[['grupo','barmanpre','wkt']]

    if not datamerge.empty:
        vargroup      = {'prenbarrio': 'first', 'preaconst': 'sum', 'preaterre': 'sum', 'prevetustzmin': 'min', 'estrato': 'max', 'predios': 'sum', 'locnombre': 'first'} 
        vargroup      = {k: v for k, v in vargroup.items() if k in datamerge.columns}
        datapaso      = datamerge.groupby('barmanpre').agg(vargroup).reset_index()
        dataresultado = dataresultado.merge(datapaso,on='barmanpre',how='left',validate='1:1')
        
        for j in ['formato_direccion','nombre_conjunto']:
            if j in datamerge:
                datapaso         = datamerge[datamerge[j].notnull()]
                datapaso         = datapaso.drop_duplicates(subset=['barmanpre',j],keep='first')
                datapaso         = datapaso[['barmanpre',j]]
                datapaso         = datapaso.groupby('barmanpre')[j].agg(lambda x: ' | '.join(x)).reset_index()
                datapaso.columns = ['barmanpre',j]
                dataresultado    = dataresultado.merge(datapaso,on='barmanpre',how='left',validate='1:1')
            
    return dataresultado
