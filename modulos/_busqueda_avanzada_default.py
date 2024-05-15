import streamlit as st
import copy
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from data.getdatalotes import main as getdatalotes
from data.getdataconsolidacionlotes import main as getdataconsolidacionlotes
from data.getdatalotesedificios import main as getdatalotesedificios

from data.coddir import coddir 

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
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busquedavanzada':None,
               'reporte_busquedavanzada':False,
               'datalotes_busquedavanzada': pd.DataFrame(),
               'geojson_data':None,
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               'options':        ['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'optionsoriginal':['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'default':[],
               'resetear':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    
    col1, col2 = st.columns(2)
    with col1:
        formato_options = {'En un poligono':1,'Por dirección':2,'Por chip':3,'Por matrícula inmobiliria':4,'Nombre de la copropiedad':5}
        consulta = st.selectbox('Tipo de busqueda:',options=list(formato_options))
        option_selected = formato_options[consulta]
        
    if option_selected==1:
        ifPolygon(formato,mapwidth,mapheight)
    else:
        direccion,chip,matricula,fcoddirlist = [None]*4
        if option_selected==2:
            with col1:
                direccion = st.text_input('Dirección del predio',value='')
        elif option_selected==3:
            with col1:
                chip = st.text_input('Chip del predio',value='',placeholder='AAA')
        elif option_selected==4:
            col1s,col2s,col3s = st.columns([0.25,0.5,0.25])
            with col1s:
                codigo = st.selectbox('Código:',options=['50S','50C','50N'])
            with col2s:
                matricula = st.text_input('Matrícula inmobiliaria',value='')
            if matricula is not None and matricula!='' and isinstance(matricula, str):
                matricula = f"{codigo}-{matricula}"
        elif option_selected==5:
            with st.spinner('Buscando los nombres de las copropiedades'):
                databuildingslist = buildinglist()
            with col1: 
                nombre_edificio = st.selectbox('Nombre de la copropiedad',options=sorted(databuildingslist['nombre_conjunto'].unique()))
                datapaso        = databuildingslist[databuildingslist['nombre_conjunto']==nombre_edificio]
                if not datapaso.empty and nombre_edificio!="":
                    fcoddirlist =  list(datapaso['coddir'].unique())
                    
        col1, col2 = st.columns([0.25,0.75])
        with col1:
            if st.button('Buscar Información'):
                ifPredio(direccion=direccion,chip=chip,matricula=matricula,fcoddir=fcoddirlist)

#-----------------------------------------------------------------------------#        
def ifPolygon(formato,mapwidth,mapheight):
    
    colm1,colm2,colm3    = st.columns([0.025,0.95,0.025])
    colf1,colf2          = st.columns(2)
    colb1,colb2          = st.columns(2)

    areamin              = 0
    areamax              = 0
    antiguedadmin        = 0
    antiguedadmax        = 0
    maxpiso              = 6
    alturaminpot         = 0
    maxpredios           = 0
    maxpropietario       = 0 
    maxavaluo            = 0 
    loteesquinero        = 'Todos'
    viaprincipal         = 'Todos'
    usodelsuelo          = 'Todos'
    tratamiento          = []
    areaactividad        = []
    actuacionestrategica = 'Todos'
    tipoedificio         = "Todos"
    
    #-------------------------------------------------------------------------#
    # Formulario            
    with colf1: seleccion  = st.multiselect('Tipo de inmueble(s)', key='seleccion',options=st.session_state.options, default=st.session_state.default,on_change=multyselectoptions,placeholder='Selecciona uno o varios inmuebles')
    with colf2: st.text_input('empty',disabled=True,label_visibility="hidden")
    
    if 'Lote' in seleccion:
        with colf1: areamin              = st.number_input('Área de terreno mínima',value=0,min_value=0)
        with colf2: areamax              = st.number_input('Área de terreno máxima',value=0,min_value=0)
        with colf1: maxpiso              = st.number_input('Número máximo de pisos construidos actualmente',value=6,min_value=0)
        with colf2: alturaminpot         = st.number_input('Altura mínima P.O.T',value=0,min_value=0)
        with colf1: tratamiento          = st.multiselect('Tratamiento P.O.T',['CONSOLIDACION', 'DESARROLLO', 'RENOVACION', 'CONSERVACION', 'MEJORAMIENTO INTEGRAL'])
        with colf2: actuacionestrategica = st.selectbox('Actuación estrategica', options=['Todos','Si','No'])
        with colf1: areaactividad        = st.multiselect('Área de actividad P.O.T',['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
        with colf2: maxpredios           = st.number_input('Número máximo de predios actuales en el lote',value=0,min_value=0)
        with colf1: loteesquinero        = st.selectbox('Lote esquinero', options=['Todos','Si','No'])
        with colf2: viaprincipal         = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])
        with colf1: frente               = st.number_input('Área de frente mínima',value=0,min_value=0)
        with colf2: maxpropietario       = st.number_input('Número máximo propietarios',value=0,min_value=0)
        with colf1: maxavaluo            = st.number_input('Valor máximo de avalúo catastral',value=0,min_value=0)
        #usodelsuelo   = st.selectbox('Uso del suelo', options=['Todos','Si','No'])
        
    elif 'Edificio' in seleccion:
        with colf1: tipoedificio   = st.selectbox('Tipo de Edificio', options=['Todos','Oficinas y Consultorios','Residencial'])
        with colf2: areamin        = st.number_input('Área construida mínima',value=0,min_value=0)
        with colf1: areamax        = st.number_input('Área construida máxima',value=0,min_value=0)
        with colf2: antiguedadmin  = st.number_input('Antigüedad mínima',value=0,min_value=0)
        with colf1: antiguedadmax  = st.number_input('Antigüedad máxima',value=0,min_value=0)
        with colf2: maxpropietario = st.number_input('Número máximo propietarios',value=0,min_value=0)
        #with colf1: maxpredios     = st.number_input('Número máximo de predios',value=0,min_value=0)
        with colf1: maxavaluo      = st.number_input('Valor máximo de avalúo catastral',value=0,min_value=0)
        with colf2: loteesquinero  = st.selectbox('Lote esquinero', options=['Todos','Si','No'])
        with colf1: viaprincipal   = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])
       
    else: 
        with colf1: areamin       = st.number_input('Área construida mínima',value=0,min_value=0)
        with colf2: areamax       = st.number_input('Área construida máxima',value=0,min_value=0)
        with colf1: antiguedadmin = st.number_input('Antigüedad mínima',value=0,min_value=0)
        with colf2: antiguedadmax = st.number_input('Antigüedad máxima',value=0,min_value=0)
        
        if 'Local' in seleccion:
            with colf1: loteesquinero = st.selectbox('Lote esquinero', options=['Todos','Si','No'])
            with colf2: viaprincipal  = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])
        
    #-------------------------------------------------------------------------#
    # Mapa
    m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":True},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)

    if st.session_state.geojson_data is not None:
        if st.session_state.datalotes_busquedavanzada.empty:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function).add_to(m)
        else:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function_color).add_to(m)

    if not st.session_state.datalotes_busquedavanzada.empty:
        geojson = data2geopandas(st.session_state.datalotes_busquedavanzada,seleccion)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    with colm2:
        st_map = st_folium(m,width=mapwidth,height=mapheight)

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
                
    if 'last_circle_polygon' in st_map and st_map['last_circle_polygon'] is not None:
        if st_map['last_circle_polygon']!=[]:
            coordenadas = st_map['last_circle_polygon']['coordinates'][0]
            st.session_state.polygon_busquedavanzada = Polygon(coordenadas)
            st.session_state.geojson_data            = mapping(st.session_state.polygon_busquedavanzada)
            polygon_shape                            = shape(st.session_state.geojson_data)
            centroid                                 = polygon_shape.centroid
            st.session_state.latitud                 = centroid.y
            st.session_state.longitud                = centroid.x
            st.session_state.zoom_start              = 16
            st.rerun()
            
    #-------------------------------------------------------------------------#
    # Reporte
    if seleccion==[]: seleccion = ['Todos']
    inputvar = {
        'tipoinmueble':seleccion,
        'areamin':areamin,
        'areamax':areamax,
        'antiguedadmin':antiguedadmin,
        'antiguedadmax':antiguedadmax,
        'maxpiso':maxpiso,
        'maxpredios':maxpredios,
        'maxpropietario':maxpropietario,
        'maxavaluo':maxavaluo,
        'loteesquinero':loteesquinero,
        'viaprincipal':viaprincipal,
        'usodelsuelo':usodelsuelo,
        'tipoedificio':tipoedificio,
        'pot':[{'tipo':'tratamientourbanistico','alturaminpot':alturaminpot,'tratamiento':tratamiento},
               {'tipo':'areaactividad','nombreare':areaactividad},
               {'tipo':'actuacionestrategica','isin':actuacionestrategica},
               ]
        }

    if st.session_state.polygon_busquedavanzada is not None:        
        inputvar['polygon'] = str(st.session_state.polygon_busquedavanzada)
        with colb2:
            if st.button('Buscar'):
                st.session_state.reporte_busquedavanzada = True
                st.rerun()

        with colb1:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
            
    if st.session_state.reporte_busquedavanzada:
        with colm2:
            with st.spinner('Buscando data'):
                if any([x for x in seleccion if 'lote' in x.lower()]):
                    _d,st.session_state.datalotes_busquedavanzada = getdataconsolidacionlotes(inputvar)
                    st.session_state.reporte_busquedavanzada   = False
                    st.rerun()
                elif any([x for x in seleccion if 'edificio' in x.lower()]):
                    _d,st.session_state.datalotes_busquedavanzada = getdatalotesedificios(inputvar)
                    st.session_state.reporte_busquedavanzada   = False
                    st.rerun()
                else:
                    st.session_state.datalotes_busquedavanzada = getdatalotes(inputvar)
                    st.session_state.reporte_busquedavanzada   = False
                    st.rerun()
        
def ifPredio(direccion=None,chip=None,matricula=None,fcoddir=None):    

    col1, col2 = st.columns([0.75,0.25])
    style_button_dir = """
    <style>
    .custom-button {
        display: inline-block;
        padding: 10px 20px;
        background-color: #68c8ed; /* Cambia el color de fondo según tu preferencia */
        color: #ffffff; 
        font-weight: bold;
        text-decoration: none;
        border-radius: 10px;
        width: 100%;
        border: 2px solid #68c8ed; /* Añade el borde como en el estilo de Streamlit */
        cursor: pointer;
        text-align: center;
        letter-spacing: 1px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .custom-button:hover {
        background-color: #21D375; /* Cambia el color de fondo al pasar el ratón */
        color: black;
        border: 2px solid #21D375; /* Cambia el color del borde al pasar el ratón */
    }
    </style>
    """
    if direccion is not None and direccion!='' and isinstance(direccion, str):
        
        with st.spinner('Buscando dirección'):
            barmanpre = direccion2barmanpre(direccion)
        if barmanpre is not None:
            with col1:
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://localhost:8501/Busqueda_avanzada?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)        
        else:
            st.error('Dirección del predio no encontrada, por favor ingresar una dirección diferente')
            
    elif chip is not None and chip!='' and isinstance(chip, str) :
        with st.spinner('Buscando chip'):
            chip = confirmeChip(chip)
        if chip is not None:
            with col1:
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://localhost:8501/Busqueda_avanzada?type=predio&code={chip}&vartype=chip&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)        
        else:
            st.error('Chip del predio no encontrado, por favor ingresar un chip diferente')
        
    elif matricula is not None  and matricula!='' and isinstance(matricula, str):
        with st.spinner('Buscando matrícula inmobiliaria'):
            chip = matricula2chip(matricula)
        if chip is not None:
            with col1:
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://localhost:8501/Busqueda_avanzada?type=predio&code={chip}&vartype=chip&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)        
        else:
            st.error('Matrícula inmobiliaria del predio no encontrada, por favor ingresar una matrícula diferente')
        
    elif fcoddir is not None:
        with st.spinner('Buscando dirección'):
            barmanpre = coddir2barmanpre(fcoddir)
        if barmanpre is not None:
            with col1:
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://localhost:8501/Busqueda_avanzada?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)        
        else:
            st.error('Copropiedad no encontrada, por favor ingresar un nombreón diferente')
            
def multyselectoptions():
    
    if st.session_state.seleccion==[]:
        st.session_state.options = copy.deepcopy(st.session_state.optionsoriginal)
        st.session_state.default = []
        
    if any([x for x in st.session_state.seleccion if 'todo' in x.lower()]):
        st.session_state.options = ['Todos']
        st.session_state.default = ['Todos']

    if any([x for x in st.session_state.seleccion if 'lote' in x.lower()]):
        st.session_state.options = ['Lote']
        st.session_state.default = ['Lote']

    if any([x for x in st.session_state.seleccion if 'edificio' in x.lower()]):
        st.session_state.options = ['Edificio']
        st.session_state.default = ['Edificio']   
    
    if st.session_state.seleccion!=[] and not any([x for x in st.session_state.seleccion if 'todo' in x.lower()]):
        if 'Todos' in st.session_state.options:
            st.session_state.options.remove('Todos')
        st.session_state.default = copy.deepcopy(st.session_state.seleccion)
        
    if st.session_state.seleccion!=[] and not any([x for x in st.session_state.seleccion if 'lote' in x.lower()]):
        if 'Lote' in st.session_state.options:
            st.session_state.options.remove('Lote')
        st.session_state.default = copy.deepcopy(st.session_state.seleccion)

    if st.session_state.seleccion!=[] and not any([x for x in st.session_state.seleccion if 'edificio' in x.lower()]):
        if 'Edificio' in st.session_state.options:
            st.session_state.options.remove('Edificio')
        st.session_state.default = copy.deepcopy(st.session_state.seleccion)
    
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  
    
@st.cache_data(show_spinner=False)
def data2geopandas(data,seleccion=[]):
    
    urlexport = "http://localhost:8501/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        for idd,items in data.iterrows():
                        
            combinacionlotes = ""
            buildinfinfo     = ""
            infoprecuso      = ""
                
            urllink = ""
            if 'Lote' in seleccion:
                combinacion = items['combinacion'] if 'combinacion' in items and isinstance(items['combinacion'], str) else None
                if combinacion is not None:
                    urllink = urlexport+f"?type=lote&code={combinacion}&token={st.session_state.token}"
                if 'num_lotes_comb' in items:
                    combinacionlotes += """
                    <b> Ver lote<br>
                    """
            elif 'Edificio' in seleccion:
                barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
                if barmanpre is not None:
                    urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"
                
                try:    buildinfinfo += f"""<b> Dirección:</b> {items['formato_direccion']}<br>"""
                except: pass
                try:    buildinfinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """
                except: pass
                try:    buildinfinfo += f"""<b> Área construida total:</b> {round(items['areaconstruida_total'],2)}<br>"""
                except: pass
                try:    buildinfinfo += f"""<b> Área de terreno:</b> {round(items['areaterreno_total'],2)}<br> """
                except: pass
                try:    buildinfinfo += f"""<b> Antiguedad:</b> {int(items['antiguedadmin'])}<br>"""
                except: pass            
                try:    buildinfinfo += f"""<b> Total de matriculas:</b> {int(items['predios_total'])}<br> """
                except: pass                    
                try:    buildinfinfo += f"""<b> Número transacciones:</b> {int(items['numero_transacciones'])}<br> """
                except: pass    
                try:    buildinfinfo += f"""<b> Valor transacciones:</b> {int(items['valortransaccionesmt2'])}<br> """
                except: pass    
            else:
                barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
                if barmanpre is not None:
                    urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"

            
            if 'infoByprecuso' in items: 
                itemsu      = items['infoByprecuso'][0]
                infoprecuso = ""
                try:    infoprecuso += f"""<b> Dirección:</b> {itemsu['formato_direccion']}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Barrio:</b> {itemsu['prenbarrio']}<br>  """
                except: pass
                try:    infoprecuso += f"""<b> Área construida total:</b> {round(itemsu['preaconst_total'],2)}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Área de terreno:</b> {round(itemsu['preaterre_total'],2)}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Estrato:</b> {int(itemsu['estrato'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Pisos:</b> {int(itemsu['connpisos'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Antiguedad:</b> {int(itemsu['prevetustzmin'])}<br>"""
                except: pass            
                try:    infoprecuso += f"""<b> Total de matriculas:</b> {int(itemsu['predios_total'])}<br> """
                except: pass                    

                for witer in items['infoByprecuso']:
                    hmtl_paso = ""
                    if witer['usosuelo'] is not None and not pd.isnull(witer['usosuelo']):
                        hmtl_paso += f"<b> Uso del suelo:</b> {witer['usosuelo']}<br>"
                    if witer['predios_precuso'] is not None and not pd.isnull(witer['predios_precuso']):
                        hmtl_paso += f"<b> Predios:</b> {witer['predios_precuso']}<br> "
                    
                    if hmtl_paso!="":
                        infoprecuso += f"""
                        <b><br>
                        {hmtl_paso}
                        """
                    try:
                        infoprecuso += f"""
                        <b> Área: </b>{witer['preaconst_precuso']/witer['preaconst_total']:,.1%}<br>
                        """
                    except: pass
            
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {infoprecuso}
                            {combinacionlotes}
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
def direccion2barmanpre(direccion):
    barmanpre = None
    if direccion is not None and direccion!="" and isinstance(direccion,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"coddir='{coddir(direccion)}'"
        data     = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            barmanpre = data['barmanpre'].iloc[0]
        engine.dispose()
    return barmanpre

@st.cache_data(show_spinner=False)
def matricula2chip(matricula):
    chip = None
    if matricula is not None and matricula!="" and isinstance(matricula,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        
        query = f" matriculainmobiliaria IN ('0{matricula.replace('-','')}','{matricula.replace('-','')}','{matricula}','{matricula.split('-')[-1]}')"
        data     = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
        if not data.empty:
            chip = data['chip'].iloc[0]
        engine.dispose()
    return chip

@st.cache_data(show_spinner=False)
def confirmeChip(chip):
    result = None
    if chip is not None and chip!="" and isinstance(chip,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"prechip='{chip}'"
        data     = pd.read_sql_query(f"SELECT prechip FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            result = data['prechip'].iloc[0]
        engine.dispose()
    return result

@st.cache_data(show_spinner=False)
def coddir2barmanpre(fcoddir):
    barmanpre = None
    query     = ""
    if isinstance(fcoddir,str) and fcoddir!="":
        query = f"coddir='{fcoddir}'"
    if isinstance(fcoddir,list):
        query = "','".join(fcoddir)
        query = f" coddir IN ('{query}')" 

    if query!="":
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
        if not data.empty:
            barmanpre = data['barmanpre'].iloc[0]
        engine.dispose()
    return barmanpre

@st.cache_data(show_spinner=False)
def buildinglist():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query("SELECT nombre_conjunto,coddir FROM  bigdata.bogota_nombre_conjuntos " , engine)
    engine.dispose()
    data = data[~data['nombre_conjunto'].str.contains(r'^\d+$')]
    data = pd.concat([pd.DataFrame([{'nombre_conjunto':'','coddir':''}]),data])
    return data 

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
