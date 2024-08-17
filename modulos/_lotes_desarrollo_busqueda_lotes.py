import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import base64
import json
import shapely.wkt as wkt
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup
from shapely.ops import unary_union

from data.getdataconsolidacionlotes import main as getdataconsolidacionlotes

from display.stylefunctions import style_function,style_function_geojson

def main(code=None):
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
        landing(code=code,mapwidth=mapwidth,mapheight=mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(code=None,mapwidth=1288,mapheight=600):
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_busqueda_lotes':None,
               'reporte_busqueda_lotes':False,
               'datalotes_busqueda_lotes': pd.DataFrame(),
               'datapredios':pd.DataFrame(),
               'dataconsolidacion':pd.DataFrame(),
               'estado':'search',
               'showterreno':False,
               'geojson_data':None,
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               'options':        ['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'optionsoriginal':['Todos','Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Lote', 'Oficina', 'Parqueadero'],
               'resetear':False,
               'polygon_consolidacion':None,
               'areamin':0,
               'areamax':0,
               'find_data':True
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    #-------------------------------------------------------------------------#
    # Cuando viene la busqueda directa de la url: analisis_normativa_urbana
    #-------------------------------------------------------------------------#
    if 'search' in st.session_state.estado:
        if isinstance(code,str) and code!='':
            try:
                codejson = base64.b64decode(code)
                codejson = codejson.decode('utf-8')
                codejson = json.loads(codejson)
            except: codejson = None
            if codejson is not None:
                st.session_state.latitud    = codejson['latitud'] if 'latitud' in codejson and isinstance(codejson['zoom'],(float,int)) else st.session_state.latitud
                st.session_state.longitud   = codejson['longitud'] if 'longitud' in codejson and isinstance(codejson['zoom'],(float,int)) else st.session_state.longitud
                st.session_state.zoom_start = codejson['zoom'] if 'zoom' in codejson and isinstance(codejson['zoom'],(float,int)) else st.session_state.zoom_start
                st.session_state.estado     = codejson['estado'] if 'estado' in codejson and isinstance(codejson['estado'],str) else st.session_state.estado
                polygon                     = codejson['polygon'] if 'polygon' in codejson and isinstance(codejson['polygon'],str) else None
                
                if isinstance(polygon,str) and polygon!="":
                    st.session_state.polygon_busqueda_lotes = wkt.loads(polygon)
                    st.session_state.geojson_data           = mapping(st.session_state.polygon_busqueda_lotes)
                    
                inputvar = {'areamin': 0, 'areamax': 0, 'antiguedadmin': 0, 'antiguedadmax': 0, 'maxpiso': 0, 'maxpredios': 0, 'maxpropietario': 0, 'maxavaluo': 0, 'loteesquinero': 'Todos', 'viaprincipal': 'Todos', 'usodelsuelo': 'Todos', 'pot': [{'tipo': 'tratamientourbanistico', 'alturaminpot': 0, 'tratamiento': []}, {'tipo': 'areaactividad', 'nombreare': []}, {'tipo': 'actuacionestrategica', 'isin': 'Todos'}]}
                if st.session_state.polygon_busqueda_lotes is not None:  
                    inputvar['polygon'] = str(st.session_state.polygon_busqueda_lotes)
                    with st.spinner('Buscando información'):
                        st.session_state.datapredios,st.session_state.datalotes_busqueda_lotes = getdataconsolidacionlotes(inputvar)
                        if not st.session_state.datalotes_busqueda_lotes.empty:
                            st.session_state.estado    = 'consolidacion'
                            st.session_state.find_data = True
                        else: 
                            st.session_state.find_data = False
                        st.rerun()
    #-------------------------------------------------------------------------#

    colt1,colt2,colt3    = st.columns([0.025,0.475,0.50])
    colm1,colm2,colm3    = st.columns([0.025,0.95,0.025])
    colmsn1,colmsn2      = st.columns([0.95,0.05])
    colmap1,colmap2      = st.columns([0.6,0.4])
    colf1,colf2          = st.columns(2)
    colb1,colb2          = st.columns(2)

    if 'search' in st.session_state.estado:
        areamin              = 0
        areamax              = 0
        antiguedadmin        = 0
        antiguedadmax        = 0
        maxpiso              = 6
        alturaminpot         = 0
        maxpredios           = 0
        maxpropietario       = 0 
        maxavaluo            = 0 
        frente               = 0
        loteesquinero        = 'Todos'
        viaprincipal         = 'Todos'
        usodelsuelo          = 'Todos'
        tratamiento          = []
        areaactividad        = []
        actuacionestrategica = 'Todos'
    
        with colf1: areamin              = st.number_input('Área de terreno mínima',value=0,min_value=0)
        with colf2: areamax              = st.number_input('Área de terreno máxima',value=0,min_value=0)
        with colf1: maxpiso              = st.number_input('Número máximo de pisos construidos actualmente',value=2,min_value=0)
        with colf2: alturaminpot         = st.number_input('Altura mínima P.O.T',value=0,min_value=0)
        with colf1: tratamiento          = st.multiselect('Tratamiento P.O.T',['CONSOLIDACION', 'DESARROLLO', 'RENOVACION', 'CONSERVACION', 'MEJORAMIENTO INTEGRAL'])
        with colf2: actuacionestrategica = st.selectbox('Actuación estrategica', options=['Todos','Si','No'])
        with colf1: areaactividad        = st.multiselect('Área de actividad P.O.T',['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
        with colf2: maxpropietario       = st.number_input('Número máximo de propietarios por lote',value=0,min_value=0)
        with colf1: maxavaluo            = st.number_input('Valor máximo de avalúo catastral',value=0,min_value=0)
        with colf2: maxpredios           = st.number_input('Número máximo de predios actuales en el lote',value=0,min_value=0)
        #usodelsuelo                      = st.selectbox('Uso del suelo', options=['Todos','Si','No'])
        #with colf1: loteesquinero        = st.selectbox('Lote esquinero', options=['Todos','Si','No'])
        #with colf2: viaprincipal         = st.selectbox('Sobre vía principal', options=['Todos','Si','No'])
        #with colf1: frente               = st.number_input('Área de frente mínima',value=0,min_value=0)
        st.session_state.areamin = areamin
        st.session_state.areamax = areamax
        
    #-------------------------------------------------------------------------#
    # Mapa
    m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)
    
    if st.session_state.geojson_data is not None:
        if st.session_state.datalotes_busqueda_lotes.empty:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function).add_to(m)
        else:
            folium.GeoJson(st.session_state.geojson_data, style_function=style_function_color).add_to(m)
    else:
        with colt2:
            html = pasosApp("Dibuja el poligono para realziar la busqueda de lotes","1")
            html = BeautifulSoup(html, 'html.parser')
            st.markdown(html, unsafe_allow_html=True) 
            
    if st.session_state.polygon_consolidacion is not None:
        folium.GeoJson(st.session_state.polygon_consolidacion, style_function=style_function_consolidacion).add_to(m)
    else:
        if not st.session_state.datalotes_busqueda_lotes.empty:
            with colt2:
                html = pasosApp("Dibuja el poligono para consolidar los lotes que deseas","2")
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)  
            
    if not st.session_state.datalotes_busqueda_lotes.empty:
        geojson = data2geopandas(st.session_state.datalotes_busqueda_lotes)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    if st.session_state.showterreno:
        with colmap1:
            st_map = st_folium(m,width=int(mapwidth*0.7),height=600)
    else:
        with colm2:
            st_map = st_folium(m,width=int(mapwidth*0.9),height=600)

    if 'search' in st.session_state.estado:
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas                             = st_map['all_drawings'][0]['geometry']['coordinates']
                    st.session_state.polygon_busqueda_lotes = Polygon(coordenadas[0])
                    st.session_state.geojson_data           = mapping(st.session_state.polygon_busqueda_lotes)
                    polygon_shape                           = shape(st.session_state.geojson_data)
                    centroid                                = polygon_shape.centroid
                    st.session_state.latitud                = centroid.y
                    st.session_state.longitud               = centroid.x
                    st.session_state.zoom_start             = 16
                    st.rerun()
               
    if 'consolidacion' in st.session_state.estado:
        colc1,colc2 = st.columns(2)
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas     = st_map['all_drawings'][0]['geometry']['coordinates']
                    polygonselected = Polygon(coordenadas[0])
                    if polygonselected is not None:
                        with colc2:
                            if st.button('Consolidar lotes'):
                                with st.spinner('Consolidando lotes'):
                                    datapaso             = st.session_state.datalotes_busqueda_lotes.copy()
                                    datapaso['geometry'] = gpd.GeoSeries.from_wkt(datapaso['wkt'])
                                    datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
                                    idd                  = datapaso['geometry'].apply(lambda x: polygonselected.contains(x))
                                    datapaso             = datapaso[idd]
                                    if not datapaso.empty:
                                        st.session_state.polygon_consolidacion = unary_union(datapaso['geometry'].to_list())
                                        centroid                               = st.session_state.polygon_consolidacion.centroid
                                        st.session_state.latitud               = centroid.y
                                        st.session_state.longitud              = centroid.x
                                        st.session_state.zoom_start            = 18
                                        st.session_state.showterreno           = True
                                        
                                        idd = st.session_state.datapredios['barmanpre'].isin(datapaso['barmanpre'])
                                        st.session_state.dataconsolidacion = st.session_state.datapredios[idd]
                                    st.rerun()
                                    
        if st.session_state.showterreno and not st.session_state.dataconsolidacion.empty:          
            with colmap2:
                if not st.session_state.dataconsolidacion.empty:
                    datapaso             = st.session_state.dataconsolidacion.copy()
                    numlotes             = len(datapaso)
                    barmanprelist        = '|'.join(datapaso['barmanpre'].unique())
                    datapaso['numlotes'] = numlotes
                    datapaso             = datapaso.groupby('numlotes').agg({'preaconst':'sum','preaterre':'sum','estrato':'max','predios':'sum','prevetustzmin':'min','prevetustzmax':'max','connpisos':'max','connsotano':'max','construcciones':'sum','areapolygon':'sum','esquinero':'max','tipovia':'min','propietarios':'sum','avaluocatastral':'sum'}).reset_index()
                    datapaso.columns     = ['numlotes','preaconst','preaterre','estrato','predios','prevetustzmin','prevetustzmax','pisos','connsotano','construcciones','areapolygon','esquinero','tipovia','propietarios','avaluocatastral']

                    #st.dataframe(datapaso)
                    #st.dataframe(st.session_state.dataconsolidacion)
                    
                    html = principal_table(datageneral=datapaso.copy(),numerolotes=numlotes,areamin=st.session_state.areamin,areamax=st.session_state.areamax)
                    st.components.v1.html(html,height=300,scrolling=True)  
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
                    nombre = 'Reporte del lote consolidado'
                    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=lote&code={barmanprelist}&token={st.session_state.token}" class="custom-button" target="_blank">{nombre}</a></body></html>"""
                    html = BeautifulSoup(html, 'html.parser')
                    st.markdown(html, unsafe_allow_html=True)  
                        
        with colc1:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
                            
    #-------------------------------------------------------------------------#
    # Buscar data    
    if 'search' in st.session_state.estado:
        inputvar = {
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
            'pot':[{'tipo':'tratamientourbanistico','alturaminpot':alturaminpot,'tratamiento':tratamiento},
                   {'tipo':'areaactividad','nombreare':areaactividad},
                   {'tipo':'actuacionestrategica','isin':actuacionestrategica},
                   ]
            }

        if st.session_state.polygon_busqueda_lotes is not None:  
            inputvar['polygon'] = str(st.session_state.polygon_busqueda_lotes)
            with colb1:
                if st.button('Buscar'):
                    with st.spinner('Buscando información'):
                        st.session_state.datapredios,st.session_state.datalotes_busqueda_lotes = getdataconsolidacionlotes(inputvar)
                        if not st.session_state.datalotes_busqueda_lotes.empty:
                            st.session_state.estado    = 'consolidacion'
                            st.session_state.find_data = True
                        else: 
                            st.session_state.find_data = False
                        st.rerun()
            with colb2:
                if st.button('Resetear búsqueda'):
                    for key,value in formato.items():
                        del st.session_state[key]
                    st.rerun()

    if st.session_state.find_data is False:
        with colmsn1:
            st.error('No se encontraron lotes que cumplan con las condiciones en ese poligono')
                

@st.cache_data(show_spinner=False)
def data2geopandas(data):
    
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
                        
            popupinfo = ""
            urllink   = ""
            barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"

            try:    popupinfo += f"""<b> Área de terreno:</b> {round(items['preaterre'],2)}<br> """
            except: pass
            try:    popupinfo += f"""<b> Área construida:</b> {round(items['preaconst'],2)}<br>"""
            except: pass
            try:    popupinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Pisos:</b> {int(items['connpisos'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Sotanos:</b> {int(items['connsotano'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Avalúo catastral:</b> ${items['avaluocatastral']:,.0f} <br>"""
            except: pass            
            try:    popupinfo += f"""<b> Propietarios:</b> {int(items['propietarios'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>"""
            except: pass
        
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {popupinfo}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def principal_table(datageneral=pd.DataFrame(),numerolotes=0,areamin=0,areamax=0):
    
    tablaresumen = ""
    if not datageneral.empty:
        #---------------------------------------------------------------------#
        # Seccion ubicacion
        try:    numlotes = f"{int(round(datageneral['numlotes'].iloc[0],0)):,}" 
        except: numlotes = None
        try:    areaterreno = f"{round(datageneral['preaterre'].iloc[0],2):,}" 
        except: areaterreno = None
        try:    areaconstruida = f"{round(datageneral['preaconst'].iloc[0],2):,}" 
        except: areaconstruida = None
        try:    estrato = f"{int(round(datageneral['estrato'].iloc[0],0)):,}" 
        except: estrato = None
        try:    predios = f"{int(round(datageneral['predios'].iloc[0],0)):,}" 
        except: predios = None
        try:    pisos = f"{int(round(datageneral['pisos'].iloc[0],0)):,}" 
        except: pisos = None
        try:    sotanos = f"{int(round(datageneral['connsotano'].iloc[0],0)):,}" 
        except: sotanos = None
        try:    antiguedadmin = f"{round(datageneral['prevetustzmin'].iloc[0],0)}" 
        except: antiguedadmin = None   
        try:    antiguedadmax = f"{round(datageneral['prevetustzmax'].iloc[0],0)}" 
        except: antiguedadmax = None   
        try:    propietarios = f"{max(1,int(round(datageneral['propietarios'].iloc[0],0))):,}" 
        except: propietarios = None
        try:    avaluocatastral = f"${datageneral['avaluocatastral'].iloc[0]:,.0f}" 
        except: avaluocatastral = None     
        try:    predial = f"${datageneral['predial'].iloc[0]:,.0f}" 
        except: predial = None   
        areaterrenovalue = datageneral['preaterre'].iloc[0] if 'preaterre' in datageneral and datageneral['preaterre'].iloc[0]>0 else 0
        
        formato   = {'Número de lotes:':numlotes,'Área de terreno:':areaterreno,'Área construida:':areaconstruida,'Estrato:':estrato,
                     'Predios:':predios,'Pisos máximos:':pisos,'Sotanos:':sotanos,'Antigüedad mínima:':antiguedadmin,'Antigüedad máxima:':antiguedadmax,
                     'Propietarios:':propietarios,'Avalúo catastral:':avaluocatastral,'Predial:':predial}

        html_paso = ""
        for key,value in formato.items():
            if 'Área de terreno:' not in key:
                if value is not None:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
            else:
                if areaterrenovalue>areamax and areaterrenovalue>0 and areamax>0:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #FA8383;">{value}</h6></td></tr>"""
                elif areaterrenovalue<areamin and areaterrenovalue>0 and areamin>0:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #FA8383;">{value}</h6></td></tr>"""
                else:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                    
        if html_paso!="":
            labeltable = "Datos del terreno"
            if numerolotes>1:
                labeltable = "Datos del terreno consolidado"
            tablaresumen = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablaresumen = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaresumen}</tbody></table></div></div>"""
        
        
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
    
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  

def style_function_consolidacion(feature):
    return {
        'fillColor': '#006400',
        'color': 'blue',
        'weight': 3,
        'dashArray': '6, 6'
    }

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
