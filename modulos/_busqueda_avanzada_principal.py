import streamlit as st
import re
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

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_avanzada_default':None,
               'reporte_busqueda_avanzada_default':False,
               'datalotes_busqueda_avanzada_default': pd.DataFrame(),
               'geojson_data_busqueda_avanzada_default':None,
               'zoom_start_data_busqueda_avanzada_default':12,
               'latitud_busqueda_avanzada_default':4.652652, 
               'longitud_busqueda_avanzada_default':-74.077899,
               'options_busqueda_avanzada_default':        ['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero'],
               'optionsoriginal_busqueda_avanzada_default':['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina', 'Parqueadero'],
               'default':[]
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    
    colt1,colt2,colt3    = st.columns([0.025,0.475,0.50])
    col1, col2 = st.columns(2)
    with colt2:
        formato_options = {'En un poligono':1,'Por dirección':2,'Por chip':3,'Por matrícula inmobiliria':4,'Nombre de la copropiedad':5}
        consulta = st.selectbox('Tipo de busqueda:',options=list(formato_options))
        option_selected = formato_options[consulta]
        
    if option_selected==1:
        ifPolygon(formato,mapwidth,500)
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
            if st.button('Buscar Información',key='boton1'):
                ifPredio(direccion=direccion,chip=chip,matricula=matricula,fcoddir=fcoddirlist)

#-----------------------------------------------------------------------------#        
def ifPolygon(formato,mapwidth,mapheight):
    
    colt1,colt2,colt3    = st.columns([0.025,0.475,0.50])
    colm1,colm2,colm3    = st.columns([0.025,0.95,0.025])
    colf1,colf2          = st.columns(2)

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
    with colf1: seleccion  = st.multiselect('Tipo de inmueble(s)', key='seleccion',options=st.session_state.options_busqueda_avanzada_default, default=st.session_state.default,on_change=multyselectoptions,placeholder='Selecciona uno o varios inmuebles')
    colf1,colf2 = st.columns(2)
    colb1,colb2 = st.columns(2)
    
    if 'Edificio' in seleccion:
        with colf1: tipoedificio   = st.selectbox('Tipo de Edificio', options=['Todos','Oficinas y Consultorios','Residencial'])
        with colf2: areamin        = st.number_input('Área construida mínima',value=0,min_value=0)
        with colf1: areamax        = st.number_input('Área construida máxima',value=0,min_value=0)
        with colf2: antiguedadmin  = st.number_input('Antigüedad mínima',value=0,min_value=0)
        with colf1: antiguedadmax  = st.number_input('Antigüedad máxima',value=0,min_value=0)
        with colf2: maxpropietario = st.number_input('Número máximo propietarios',value=0,min_value=0)
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
    with colm2:
        m    = folium.Map(location=[st.session_state.latitud_busqueda_avanzada_default, st.session_state.longitud_busqueda_avanzada_default], zoom_start=st.session_state.zoom_start_data_busqueda_avanzada_default,tiles="cartodbpositron")
        draw = Draw(
                    draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                    edit_options={"poly": {"allowIntersection": False}}
                    )
        draw.add_to(m)
    
        if st.session_state.geojson_data_busqueda_avanzada_default is not None:
            if st.session_state.datalotes_busqueda_avanzada_default.empty:
                folium.GeoJson(st.session_state.geojson_data_busqueda_avanzada_default, style_function=style_function).add_to(m)
            else:
                folium.GeoJson(st.session_state.geojson_data_busqueda_avanzada_default, style_function=style_function_color).add_to(m)
        else:
            with colt2:
                html = pasosApp("Dibuja el poligono para realziar la busqueda de lotes","1")
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)
                
        if not st.session_state.datalotes_busqueda_avanzada_default.empty:
            geojson = data2geopandas(st.session_state.datalotes_busqueda_avanzada_default,seleccion)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
        st_map = st_folium(m,width=int(mapwidth*0.95),height=500)

        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas                              = st_map['all_drawings'][0]['geometry']['coordinates']
                    st.session_state.polygon_busqueda_avanzada_default = Polygon(coordenadas[0])
                    st.session_state.geojson_data_busqueda_avanzada_default            = mapping(st.session_state.polygon_busqueda_avanzada_default)
                    polygon_shape                            = shape(st.session_state.geojson_data_busqueda_avanzada_default)
                    centroid                                 = polygon_shape.centroid
                    st.session_state.latitud_busqueda_avanzada_default                 = centroid.y
                    st.session_state.longitud_busqueda_avanzada_default                = centroid.x
                    st.session_state.zoom_start_data_busqueda_avanzada_default              = 16
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

    if st.session_state.polygon_busqueda_avanzada_default is not None:        
        inputvar['polygon'] = str(st.session_state.polygon_busqueda_avanzada_default)
        with colb1:
            if st.button('Buscar'):
                st.session_state.reporte_busqueda_avanzada_default = True
                st.rerun()

        with colb2:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
            
    if st.session_state.reporte_busqueda_avanzada_default:
        with colm2:
            with st.spinner('Buscando data'):
                if any([x for x in seleccion if 'edificio' in x.lower()]):
                    _d,st.session_state.datalotes_busqueda_avanzada_default = getdatalotesedificios(inputvar)
                    st.session_state.reporte_busqueda_avanzada_default   = False
                    st.rerun()
                else:
                    st.session_state.datalotes_busqueda_avanzada_default = getdatalotes(inputvar)
                    st.session_state.reporte_busqueda_avanzada_default   = False
                    st.rerun()
        
def ifPredio(direccion=None,chip=None,matricula=None,fcoddir=None):    

    col1, col2 = st.columns([0.75,0.25])
    style_button_dir = """
    <style>
    .custom-button {
        display: inline-block;
        padding: 10px 20px;
        background-color: #A16CFF;
        color: #ffffff; 
        font-weight: bold;
        text-decoration: none;
        border-radius: 10px;
        width: 100%;
        border: 2px solid #A16CFF;
        cursor: pointer;
        text-align: center;
        letter-spacing: 1px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .custom-button:hover {
        background-color: #21D375;
        color: black;
        border: 2px solid #21D375;
    }
    </style>
    """
    if direccion is not None and direccion!='' and isinstance(direccion, str):
        
        with st.spinner('Buscando dirección'):
            barmanpre = direccion2barmanpre(direccion)
        if barmanpre is not None:
            with col1:
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
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
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={chip}&vartype=chip&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
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
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={chip}&vartype=chip&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
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
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)        
        else:
            st.error('Copropiedad no encontrada, por favor ingresar un nombreón diferente')
            
def multyselectoptions():
    
    if st.session_state.seleccion==[]:
        st.session_state.options_busqueda_avanzada_default = st.session_state.optionsoriginal_busqueda_avanzada_default.copy()
        st.session_state.default = []
        
    if any([x for x in st.session_state.seleccion if 'todo' in x.lower()]):
        st.session_state.options_busqueda_avanzada_default = ['Todos']
        st.session_state.default = ['Todos']

    if any([x for x in st.session_state.seleccion if 'edificio' in x.lower()]):
        st.session_state.options_busqueda_avanzada_default = ['Edificio']
        st.session_state.default = ['Edificio']   
    
    if st.session_state.seleccion!=[] and not any([x for x in st.session_state.seleccion if 'todo' in x.lower()]):
        if 'Todos' in st.session_state.options_busqueda_avanzada_default:
            st.session_state.options_busqueda_avanzada_default.remove('Todos')
        st.session_state.default = st.session_state.seleccion.copy()
        
    if st.session_state.seleccion!=[] and not any([x for x in st.session_state.seleccion if 'edificio' in x.lower()]):
        if 'Edificio' in st.session_state.options_busqueda_avanzada_default:
            st.session_state.options_busqueda_avanzada_default.remove('Edificio')
        st.session_state.default = st.session_state.seleccion.copy()
    
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  
    
@st.cache_data(show_spinner=False)
def data2geopandas(data,seleccion=[]):
    
    urlexport = "http://www.urbex.com.co/Busqueda_avanzada"
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
                        
            buildinfinfo     = ""
            infoprecuso      = ""
                
            urllink = ""
            if 'Edificio' in seleccion:
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
    
        matriculah1 = re.sub('[^0-9a-zA-Z]','',matricula)
        matriculah2 = re.sub('[^0-9a-zA-Z]','',matricula).lstrip('0')
        matriculah3 = re.sub('[^0-9a-zA-Z]','',matricula).lstrip('0')[3:]
        query = f" matriculainmobiliaria IN ('0{matricula.replace('-','')}','{matricula.replace('-','')}','{matricula}','{matricula.split('-')[-1]}','{matriculah1}','{matriculah2}','{matriculah3}')"
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

def pasosApp(texto,numero):
    style = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
    
        .step-container {
            background-color: #fff;
            border: 2px solid #ccc;
            border-radius: 10px;
            padding: 10px 20px; /* Reducir el padding */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            height: 30px;
        }
    
        .circle {
            background-color: #A16CFF;
            color: #fff;
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-right: 10px;
            font-size: 0.8em; /* Reducir el tamaño de la fuente */
        }
    
        .step {
            color: #B241FA;
            font-size: 0.8em; /* Reducir el tamaño de la fuente */
            margin: 0;
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
        {style}
    </head>
    <body>
        <div class="step-container" style="margin-bottom: 20px;">
            <div class="circle">{numero}</div>
            <p class="step">{texto}</p>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    main()
