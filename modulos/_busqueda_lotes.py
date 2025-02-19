import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from shapely import wkt
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from datetime import datetime

from display.stylefunctions  import style_function_geojson
from display.puntos_descripcion_usuarios import pasosApp,procesoCliente

from functions.getuso_destino import usosuelo_class
from functions.getlatlng import getlatlng
from functions.circle_polygon import circle_polygon
from functions._principal_getdatalotes_combinacion import main as _principal_getlotes

from data._principal_normativa_urbana  import getoptionsnormativa
from data._principal_shapefile import localidad as datalocalidad
from data.tracking import savesearch
from data._params_to_direccion import chip2direccion,matricula2direccion,buildinglist

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_lotes_default':None,
               'data_lotes_combinacion':  pd.DataFrame(),
               'geojson_data_busqueda_lotes_default':None,
               'zoom_start_data_busqueda_lotes_default':12,
               'latitud_busqueda_lotes_default':4.652652, 
               'longitud_busqueda_lotes_default':-74.077899,
               'direccion':None,
               'barmanpre_ref':[],
               'search_button_clic_busqueda_lotes_default':False,
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
    # Data uso
    datauso          = usosuelo_class()
    dataoptions      = getoptionsnormativa()
    _,data_localidad = datalocalidad()
    
  
    #-------------------------------------------------------------------------#
    # Proceso
    col1p,col2p,col3p = st.columns([1,2,1])
    with col2p:
        if st.session_state.geojson_data_busqueda_lotes_default is None and st.session_state.data_lotes_combinacion.empty:
            html = procesoCliente(1)
        elif st.session_state.geojson_data_busqueda_lotes_default is not None and st.session_state.data_lotes_combinacion.empty:
            html = procesoCliente(3)
        elif not st.session_state.data_lotes_combinacion.empty:
            html = procesoCliente(5)
        st.components.v1.html(html, height=100, scrolling=True)
        
    #-------------------------------------------------------------------------#
    # Busqueda por direccion 
    #-------------------------------------------------------------------------#
    localidad         = ['Todas']
    col1paso,col2paso = st.columns([9,3],vertical_alignment='center')
    col1text,col2text = st.columns([0.3,0.6],vertical_alignment='center')
    if screensize>1280:
        col1,col2,col3,col4,col5 = st.columns([0.3,0.15,0.3,0.15,0.1],vertical_alignment='center')
    else:
        col1, col2, col3 = st.columns([0.4,0.2,0.4],vertical_alignment='center')
        col4, col5 = st.columns([0.4,0.6],vertical_alignment='center')
    
    with col1:
        formato_options = {'Localidad':0,'En un poligono':1,'Por dirección':2,'Por chip':3,'Por matrícula inmobiliria':4}
        consulta        = st.selectbox('Forma de seleccionar la zona:',options=list(formato_options))
        option_selected = formato_options[consulta]

    if option_selected==0:
        if st.session_state.data_lotes_combinacion.empty:
            with col1paso:
                html = pasosApp(1, 'Seleccionar la zona de búsqueda de lotes:', 'Existen varias formas de definir la zona de búsqueda de lotes. <br> La opción <b>"Localidad"</b> permite buscar exclusivamente dentro de la localidad seleccionada')
                st.markdown(html, unsafe_allow_html=True)
            
        with col2:
            ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
            
        with col3:
            options        = [""]+list(sorted(data_localidad['locnombre'].unique()))
            localidad      = st.selectbox('Localidad', options=options)
            localidadwkt,_ = datalocalidad(locnombre=localidad)
            
        st.session_state.direccion                              = None
        st.session_state.polygon_busqueda_lotes_default         = None
        st.session_state.geojson_data_busqueda_lotes_default    = wkt.loads(localidadwkt['wkt'].iloc[0]) if not localidadwkt.empty and 'wkt' in localidadwkt and isinstance(localidadwkt['wkt'].iloc[0],str) and localidadwkt['wkt'].iloc[0]!='' else None
        st.session_state.zoom_start_data_busqueda_lotes_default = 12
         
    elif option_selected==1:
        if st.session_state.data_lotes_combinacion.empty:
            with col1paso:
                html = pasosApp(1, 'Seleccionar la zona de búsqueda de lotes', 'Puede delimitar un polígono en el mapa para definir la zona específica donde se buscarán los lotes')
                st.markdown(html, unsafe_allow_html=True)
            
    elif option_selected>1:
        with col2:
            ciudad = st.selectbox('Ciudad:',options=['Bogotá D.C.'])
            
        with col3:
            if option_selected==3:
                if st.session_state.data_lotes_combinacion.empty:
                    with col1paso:
                        html = pasosApp(1, 'Seleccionar la zona de búsqueda de lotes', 'Para ubicar un lote en el mapa, ingrese el chip de referencia del lote. El sistema mostrará el lote en el mapa y generará un radio de búsqueda alrededor de ese punto. Luego, haga clic en el botón <b>"Ubicar en el mapa"</b> para visualizarlo.')
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
                if st.session_state.data_lotes_combinacion.empty:
                    with col1paso:
                        html = pasosApp(1, 'Seleccionar la zona de búsqueda de lotes', 'Para ubicar un lote en el mapa, ingrese la matrícula inmobiliaria de referencia del lote. El sistema mostrará el lote en el mapa y generará un radio de búsqueda alrededor de ese punto. Luego, haga clic en el botón <b>"Ubicar en el mapa"</b> para visualizarlo.')
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
                                    
            if option_selected==2:
                if st.session_state.data_lotes_combinacion.empty:
                    with col1paso:
                        html = pasosApp(1, 'Seleccionar la zona de búsqueda de lotes', 'Para ubicar un lote en el mapa, ingrese una dirección de referencia. El sistema mostrará el lote en el mapa y generará un radio de búsqueda alrededor de ese punto. Luego, haga clic en el botón <b>"Ubicar en el mapa"</b> para visualizarlo.')
                        st.markdown(html, unsafe_allow_html=True)
                st.session_state.direccion = st.text_input('Dirección:',value='',placeholder="Ej: Calle 134 19A 25")   

        with col4:
            metros = st.selectbox('Metros a la redonda:',options=[100,200,300,400,500],index=0)   
        
        disabled = False if isinstance(st.session_state.direccion,str) and st.session_state.direccion!='' and metros<=500 else True
        with col5:
            if st.button('Ubicar en el mapa',disabled=disabled):
                st.session_state.latitud_busqueda_lotes_default,st.session_state.longitud_busqueda_lotes_default, st.session_state.barmanpre_ref = getlatlng(f'{st.session_state.direccion},{ciudad.lower()},colombia')
                st.session_state.polygon_busqueda_lotes_default         = circle_polygon(metros,st.session_state.latitud_busqueda_lotes_default,st.session_state.longitud_busqueda_lotes_default)
                st.session_state.geojson_data_busqueda_lotes_default    = mapping(st.session_state.polygon_busqueda_lotes_default)
                st.session_state.zoom_start_data_busqueda_lotes_default = 16
                st.rerun()
    st.markdown('<div style="padding: 30px;"></div>', unsafe_allow_html=True)
    
    #-------------------------------------------------------------------------#
    # Formulario    
    col1paso,col2paso = st.columns([0.4,0.6])   
    if st.session_state.geojson_data_busqueda_lotes_default is not None and st.session_state.data_lotes_combinacion.empty:
        with col1paso:
            html = pasosApp(3, 'Filtros:', 'Utilice estos filtros para segmentar los lotes. <br> Una vez configurados, continúe al paso <div class="circle_small">4</div> para realizar la búsqueda')
            st.markdown(html, unsafe_allow_html=True)
        
        with col2paso:
            html = pasosApp(2, 'Poligono:', 'El polígono permite delimitar la zona en la que se buscarán los lotes')
            st.markdown(html, unsafe_allow_html=True)
    
    if not st.session_state.data_lotes_combinacion.empty:
        with col2paso:
            html = pasosApp(5, 'Selección de lotes para consolidar:', 'Los poligonos resultantes en color verde contienen los lotes que cumplen con los criterios de busqueda.  Al hacer clic en un polígono verde, se mostrará la cantidad de lotes disponibles para consolidación, así como el área total del terreno consolidable. Luego, al hacer clic en el texto, se abrirá una ventana donde podrá seleccionar y consolidar los lotes según su preferencia')
            st.markdown(html, unsafe_allow_html=True)
            
            
    col1,col3 = st.columns([0.4,0.6])      
    with col1:
        
        # Primera fila
        colc1, colc2 = st.columns(2)
        
        with colc1:
            areaminlote = st.number_input('Área mínima del lote', value=0, min_value=0)
        
        with colc2:
            areamaxlote = st.number_input('Área máxima del lote', value=0, min_value=0)
        
        # Segunda fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista = dataoptions[dataoptions['variable'] == 'pisos'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '<2': 'Menor a 2 pisos', '<3': 'Menor a 3 pisos', '<4': 'Menor a 4 pisos', '>=4': 'Mayor o igual a 4 pisos'
            })
            select = st.selectbox('Pisos construidos actualmente en los lotes', options=list(datalista['input'].unique()))
            pisos = datalista[datalista['input'] == select]['indice'].iloc[0]
        
        with colc2:
            datalista = dataoptions[dataoptions['variable'] == 'altura_min_pot'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '<=3': 'Menor a 4 pisos', '>4': 'Mayor a 4 pisos', '>6': 'Mayor a 6 pisos',
                '>10': 'Mayor a 10 pisos', '>15': 'Mayor a 15 pisos'
            })
            select = st.selectbox('Altura mínima del P.O.T', options=list(datalista['input'].unique()))
            altura_min_pot = datalista[datalista['input'] == select]['indice'].iloc[0]
        
        # Tercera fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista          = dataoptions[dataoptions['variable']=='tratamiento'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Tratamiento urbanístico',options=list(datalista['input'].unique()))
            tratamiento        = datalista[datalista['input']==select]['indice'].iloc[0]
        
        with colc2:
            datalista          = dataoptions[dataoptions['variable']=='actuacion_estrategica'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Actuación estrategíca',options=list(datalista['input'].unique()))
            actuacion_estrategica = datalista[datalista['input']==select]['indice'].iloc[0]
        
        
        # Cuarta fila
        colc1 = st.columns(1)[0]
        with colc1:
            datalista          = dataoptions[dataoptions['variable']=='area_de_actividad'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Área de actividad',options=list(datalista['input'].unique()))
            area_de_actividad  = datalista[datalista['input']==select]['indice'].iloc[0]
    
        # Quinta fila
        colc1, colc2 = st.columns(2)
        with colc1:
            datalista = dataoptions[dataoptions['variable'] == 'numero_propietarios'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({
                '0': 'Todos', '1': 'Un propietario', '<5': 'Menos de 5 propietarios', '<10': 'Menos de 10 propietarios',
                '<20': 'Menos de 20 propietarios', '>=20': 'Más de 20 propietarios'
            })
            select = st.selectbox('Número de propietarios', options=list(datalista['input'].unique()))
            numero_propietarios = datalista[datalista['input'] == select]['indice'].iloc[0]

        with colc2:
            datalista          = dataoptions[dataoptions['variable']=='via_principal'].sort_values(by='indice')
            datalista['input'] = datalista['input'].replace({'0':'Todos'})
            select             = st.selectbox('Vía principal',options=list(datalista['input'].unique()))
            via_principal      = datalista[datalista['input']==select]['indice'].iloc[0]
            
        # Sexta fila
        colc1, colc2 = st.columns(2)
        with colc1:
            estratomin = st.number_input('Estrato mínimo', value=0, min_value=0)
        
        with colc2:
            estratomax = st.number_input('Estrato máximo', value=0, min_value=0)
        

    #-------------------------------------------------------------------------#
    # Mapa
    with col3:
        m = folium.Map(location=[st.session_state.latitud_busqueda_lotes_default, st.session_state.longitud_busqueda_lotes_default], zoom_start=st.session_state.zoom_start_data_busqueda_lotes_default,tiles="cartodbpositron")
        
        if st.session_state.data_lotes_combinacion.empty and option_selected==1:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
        if st.session_state.geojson_data_busqueda_lotes_default is not None:
            folium.GeoJson(st.session_state.geojson_data_busqueda_lotes_default, style_function=style_function_color).add_to(m)

        if not st.session_state.data_lotes_combinacion.empty:
            geojson = data2geopandas(st.session_state.data_lotes_combinacion)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        if st.session_state.data_lotes_combinacion.empty:
            st_map = st_folium(m,width=int(mapwidth*0.6),height=700,key=st.session_state.mapkey)

            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                        coordenadas                                             = st_map['all_drawings'][0]['geometry']['coordinates']
                        st.session_state.polygon_busqueda_lotes_default         = Polygon(coordenadas[0])
                        st.session_state.geojson_data_busqueda_lotes_default    = mapping(st.session_state.polygon_busqueda_lotes_default)
                        polygon_shape                                           = shape(st.session_state.geojson_data_busqueda_lotes_default)
                        centroid                                                = polygon_shape.centroid
                        st.session_state.latitud_busqueda_lotes_default         = centroid.y
                        st.session_state.longitud_busqueda_lotes_default        = centroid.x
                        st.session_state.zoom_start_data_busqueda_lotes_default = 16
                        st.rerun()
        else:
            folium_static(m,width=int(mapwidth*0.6),height=700)


    inputvar = {
        'areaminlote':areaminlote,
        'areamaxlote':areamaxlote,
        'estratomin':estratomin,
        'estratomax':estratomax,
        'pisos':pisos,
        'altura_min_pot':altura_min_pot,
        'tratamiento':tratamiento,
        'actuacion_estrategica':actuacion_estrategica,
        'area_de_actividad':area_de_actividad,
        'via_principal':via_principal,
        'numero_propietarios':numero_propietarios,
        'localidad':localidad,
        'polygon':str(st.session_state.polygon_busqueda_lotes_default)
        }
    col1paso,col2paso = st.columns([0.4,0.6])
    col1,col2,col3    = st.columns([0.2,0.2,0.6])
    cols1,cols2       = st.columns([0.4,0.6])
    
    if st.session_state.geojson_data_busqueda_lotes_default is not None and st.session_state.data_lotes_combinacion.empty:
        with col1paso:
            html = pasosApp(4, 'Búsqueda:', 'Después de seleccionar el polígono en el mapa, aparecerá el botón de búsqueda. <br> Al hacer <b>clic</b>, podrás buscar todos los predios dentro del polígono definido. <br> También tienes la opción de restablecer la búsqueda para realizar una nueva')
            st.markdown(html, unsafe_allow_html=True)
            
    with col1:
        if st.button('Resetear búsqueda'):
            
            variable_reset = formato.copy()
            del variable_reset['token']
            
            for key,value in variable_reset.items():
                del st.session_state[key]
            st.session_state.clear()
            st.rerun()
                    
    with col2:
        if st.button('Buscar'):
            with cols1:
                with st.spinner('Buscando información'):
                    st.session_state.data_lotes_combinacion = _principal_getlotes(inputvar=inputvar)
                    st.session_state.search_button_clic_busqueda_lotes_default = True
                    
            # Guardar:
            _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_busqueda_lotes', inputvar)
            st.rerun()

    if st.session_state.search_button_clic_busqueda_lotes_default and st.session_state.data_lotes_combinacion.empty:
        st.error('No se encontraron lotes que cumplen con las características')

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

@st.cache_data(show_spinner=False)
def data2geopandas(data):

    urlexport = "http://www.urbex.com.co/Lotes"
    geojson   = pd.DataFrame().to_json()
    if 'geometry' in data: 
        data = data[data['geometry'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['geometry'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#003F2D' #'#003F2D' - #5A189A
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            if 'grupo' in items:
                params       = {'type':'combinacion_lote','grupo':items['grupo'],'barmanpre':items['barmanpre'] if 'barmanpre' in items else None,'token':st.session_state.token}
                params       = json.dumps(params)
                params       = base64.urlsafe_b64encode(params.encode()).decode()
                params       = urllib.parse.urlencode({'token': params})
                
                urllink  = f"{urlexport}?{params}"
                generalinfo = ""
                
                areapolygon = "{:.2f} m²".format(items['areamaxcombinacion']) if 'areamaxcombinacion' in items and isinstance(items['areamaxcombinacion'],(float,int)) else None
                generalinfo += f"""<b> Número máximo de lotes para consolidar:</b> {len(items['grupo'].split('|'))}<br>"""
                generalinfo += f"""<b> Área máxima consolidación de lotes:</b> {areapolygon}<br>"""  if areapolygon is not None else ''
                generalinfo += "<b> Ver lotes</b><br>"
            
                popup_content =  f'''
                <!DOCTYPE html>
                <html>
                    <body>
                        <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:300px;font-size: 12px;">
                            <a href="{urllink}" target="_blank" style="color: black;">
                                {generalinfo}
                            </a>
                        </div>
                    </body>
                </html>
                '''
                data.loc[idd,'popup'] = popup_content
            
        geojson = data.to_json()
    return geojson
