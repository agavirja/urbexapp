import streamlit as st
import re
import folium
import pandas as pd
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup

from display.stylefunctions  import style_function,style_function_geojson,style_function_color
from display.pasosApp import pasosApp

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
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass
 
    if st.session_state.access:
        landing(mapwidth,mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(mapwidth,mapheight):

    ifPolygon(mapwidth,mapheight)


#-----------------------------------------------------------------------------#        
def ifPolygon(mapwidth,mapheight):
    
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
        with st.container():
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
                    #_d,st.session_state.datalotes_busqueda_avanzada_default = getdatalotesedificios(inputvar)
                    st.session_state.datalotes_busqueda_avanzada_default = pd.DataFrame()
                    st.session_state.reporte_busqueda_avanzada_default   = False
                    st.rerun()
                else:
                    st.session_state.datalotes_busqueda_avanzada_default = pd.DataFrame()
                    st.session_state.reporte_busqueda_avanzada_default   = False
                    st.rerun()
        
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

if __name__ == "__main__":
    main()