import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from data.getdatalotes import main as getdatalotes
from data.data_pot_manzana import consolidacionlotesselected
from data.consolidacion_data_lotes import main as consolidacion_data_lotes
from data.getdatabuilding import main as getdatabuilding
from data.googleStreetView import mapstreetview,mapsatelite
from data.datacomplemento import main as datacomplemento

from modulos._busqueda_avanzada_descripcion_lote import analytics_transacciones,analytics_predial,gruoptransactions

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
               'polygon_showlotes':None,
               'datalotes_showlotes': pd.DataFrame(),
               'geojson_showlotes':None,
               'data_consolidacion':pd.DataFrame(),
               'estado':'search',
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    #-------------------------------------------------------------------------#
    # Mapa
    m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)

    if st.session_state.geojson_showlotes is not None and st.session_state.datalotes_showlotes.empty:
        if st.session_state.datalotes_showlotes.empty:
            folium.GeoJson(st.session_state.geojson_showlotes, style_function=style_function).add_to(m)
        else:
            folium.GeoJson(st.session_state.geojson_showlotes, style_function=style_function_color).add_to(m)

    if not st.session_state.datalotes_showlotes.empty:
        geojson = data2geopandas(st.session_state.datalotes_showlotes)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
    
    if not st.session_state.data_consolidacion.empty:
        geojson  = data2geopandas(st.session_state.data_consolidacion,color='blue')
        #popup   = folium.GeoJsonPopup(
        #    fields=["popup"],
        #    aliases=[""],
        #    localize=True,
        #    labels=True,
        #)
        #folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m1)
        folium.GeoJson(geojson,style_function=style_function_geojson).add_to(m)

    st_map = st_folium(m,width=mapwidth,height=mapheight)

    colb1,colb2,colb3  = st.columns(3)
    if 'search' in st.session_state.estado:
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas                              = st_map['all_drawings'][0]['geometry']['coordinates']
                    st.session_state.polygon_showlotes = Polygon(coordenadas[0])
                    st.session_state.geojson_showlotes = mapping(st.session_state.polygon_showlotes)
                    polygon_shape                      = shape(st.session_state.geojson_showlotes)
                    centroid                           = polygon_shape.centroid
                    st.session_state.latitud           = centroid.y
                    st.session_state.longitud          = centroid.x
                    st.session_state.zoom_start        = 14
                    st.session_state.estado            = 'consolidacion' 
                    st.rerun()
                    
    if 'consolidacion' in st.session_state.estado:
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas     = st_map['all_drawings'][0]['geometry']['coordinates']
                    polygonselected = Polygon(coordenadas[0])
                    col1,col2,col3  = st.columns([0.35,0.35,0.3])
                    if polygonselected is not None:
                        with colb3:
                            if st.button('Consolidar lotes'):
                                with st.spinner('Consolidando lotes'):
                                    st.session_state.data_consolidacion = consolidacionlotesselected(polygon=str(polygonselected))
                                    st.session_state.zoom_start         = 12
                                    st.rerun()  


    #-------------------------------------------------------------------------#
    # Reporte
    if st.session_state.polygon_showlotes is not None: 
        inputvar = {'polygon':str(st.session_state.polygon_showlotes)}
        with colb2:
            if st.button('Buscar'):
                with st.spinner('Buscando información'):
                    st.session_state.datalotes_showlotes = getdatalotes(inputvar)
                    st.rerun()

        with colb1:
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
                
    datageneral,datageneraluso,datacatastro,datausosuelo,datalote,datavigencia,datatransacciones = [pd.DataFrame()]*7
    if not st.session_state.data_consolidacion.empty:
        with st.spinner('Buscando información'):
            barmanprelist = st.session_state.data_consolidacion['barmanpre'].to_list()
            datageneral,datageneraluso = consolidacion_data_lotes(barmanprelist)
            datacatastro,datausosuelo,datalote,datavigencia,datatransacciones = getdatabuilding(barmanprelist)

    latitud,longitud = [None]*2
    if not datageneral.empty and 'wkt' in datageneral:
        st.write('')
        st.write('')
        st.write('')
        col1,col2,col3,col4,col5   = st.columns([0.2,0.02,0.2,0.05,0.5])
        polygon  = wkt.loads(datageneral['wkt'].iloc[0])
        latitud  = polygon.centroid.y
        longitud = polygon.centroid.x

        m  = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
        folium.GeoJson(polygon, style_function=style_function_color).add_to(m)
        with col5:
            st_map = st_folium(m,width=int(mapwidth*0.5),height=400)
            
        with col1:
            html = mapstreetview(latitud,longitud)
            st.components.v1.html(html, width=int(mapwidth*0.4), height=400)
        with col3:
            html = mapsatelite(latitud,longitud)
            st.components.v1.html(html, width=int(mapwidth*0.4), height=400)
    
    
    #-------------------------------------------------------------------------#
    # Tabla Principal 
    #-------------------------------------------------------------------------#
    barmanpre = None
    polygon   = None
    if not datageneral.empty: 
        #barmanpre = list(datageneral['barmanpre'].unique())
        polygon   = str(datageneral['wkt'].iloc[0])
    
    html = principal_table(barmanpre=barmanpre,latitud=latitud,longitud=longitud,polygon=polygon,datageneral=datageneral,datageneraluso=datageneraluso,datacatastro=datacatastro,datausosuelo=datausosuelo,datalote=datalote,datavigencia=datavigencia,datatransacciones=datatransacciones)
    #texto = BeautifulSoup(html, 'html.parser')
    #st.markdown(texto, unsafe_allow_html=True)
    st.components.v1.html(html,height=1900,scrolling=True)     

    #-------------------------------------------------------------------------#
    # Tabla Transacciones
    #-------------------------------------------------------------------------#
    if not datatransacciones.empty:       
        
        datatransacciones = gruoptransactions(datatransacciones)
        datapaso          = datatransacciones.copy()
        dataoptions       = datatransacciones.copy()
        dataoptions       = dataoptions.sort_values(by=['predirecc'],ascending=True)
        
        col1,col2,col3,col4 = st.columns([0.04,0.2,0.5,0.26])
        with col2:
            options = ['Todos'] + list(dataoptions['predirecc'].unique())
            filtro = st.selectbox('',key='filtro_direccion_tabla2',options=options,placeholder='Seleccionar un predio',label_visibility="hidden")
        
        with col3:
            st.write('')
            titulo = 'Transacciones'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
        tableH   = 450
        if 'todo' not in filtro.lower():
            datapaso = datatransacciones[datatransacciones['predirecc']==filtro]
            tableH   = 150
            
        html_paso = ""
        for _,items in datapaso.iterrows():
            
            try:    cuantia = f"${items['cuantia']:,.0f}"
            except: cuantia = ''
            try:    areaconstruida = f"{round(items['preaconst'],2)}"
            except: areaconstruida = ''     
            try:    areaterreno = f"{round(items['preaterre'],2)}"
            except: areaterreno = ''  
            html_paso += f"""
            <tr>
                <td>{items['group']}</td>    
                <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                   <a href="{items['link']}" target="_blank">
                   <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                   </a>                    
                </td>
                <td>{items['fecha_documento_publico']}</td>    
                <td>{items['predirecc']}</td>
                <td>{items['codigo']}</td>
                <td>{items['nombre']}</td>
                <td>{items['tarifa']}</td>
                <td>{cuantia}</td>
                <td>{areaconstruida}</td>
                <td>{areaterreno}</td>
                <td>{items['tipo_documento_publico']}</td>
                <td>{items['numero_documento_publico']}</td>
                <td>{items['entidad']}</td>                
            </tr>
            """
        html_paso = f"""
        <thead>
            <tr>
                <th>Grupo</th>
                <th>Link</th>
                <th>Fecha</th>
                <th>Dirección</th>
                <th>Código</th>
                <th>Tipo</th>
                <th>Tarifa</th>
                <th>Valor</th>
                <th>Área construida</th>
                <th>Área de terreno</th>
                <th>Tipo documento</th>
                <th>Número de documento</th>
                <th>Notaria</th>                
            </tr>
        </thead>
        <tbody>
        {html_paso}
        </tbody>
        """
        style = tablestyle()
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
        </head>
        <body>
            <div class="table-wrapper table-background">
                <div class="table-scroll">
                    <table class="fl-table">
                    {html_paso}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        st.components.v1.html(html,height=tableH)       
        
    #-------------------------------------------------------------------------#
    # Tabla Propiedades
    #-------------------------------------------------------------------------#
    if not datacatastro.empty:
        datacatastro['url']  = datacatastro['prechip'].apply(lambda x: f"http://localhost:8501/Busqueda_avanzada?type=predio&code={x}&vartype=chip")
        datacatastro         = datacatastro.sort_values(by='predirecc',ascending=True)
        
        col1,col2,col3,col4 = st.columns([0.04,0.2,0.5,0.26])
        with col2:
            options = ['Todos'] + list(datacatastro['predirecc'].unique())
            filtro = st.selectbox('',key='filtro_direccion_tabla1',options=options,placeholder='Seleccionar un predio',label_visibility="hidden")
        
        with col3:
            st.write('')
            titulo = 'Predios'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
        datapaso = datacatastro.copy()
        tableH   = 450
        if 'todo' not in filtro.lower():
            datapaso = datacatastro[datacatastro['predirecc']==filtro]
            tableH   = 150
            
        html_paso    = ""
        for _,items in datapaso.iterrows():
            html_paso += f"""
            <tr>
                <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                   <a href="{items['url']}" target="_blank">
                   <img src="https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png" alt="link" width="20" height="20">
                   </a>                    
                </td>
                <td>{items['predirecc']}</td>
                <td>{items['usosuelo']}</td>
                <td>{items['prechip']}</td>
                <td>{items['matriculainmobiliaria']}</td>
                <td>{items['precedcata']}</td>
                <td>{items['preaconst']}</td>
                <td>{items['preaterre']}</td>
            </tr>
            """
        html_paso = f"""
        <thead>
            <tr>
                <th>Link</th>
                <th>Dirección</th>
                <th>Uso del suelo</th>
                <th>Chip</th>
                <th>Matrícula Inmobiliaria</th>
                <th>Cédula catastral</th>
                <th>Área construida</th>
                <th>Área de terreno</th>
            </tr>
        </thead>
        <tbody>
        {html_paso}
        </tbody>
        """
        style = tablestyle()
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
        </head>
        <body>
            <div class="table-wrapper table-background">
                <div class="table-scroll">
                    <table class="fl-table">
                    {html_paso}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        st.components.v1.html(html,height=tableH)  
        

@st.cache_data(show_spinner=False)
def principal_table(barmanpre=None,latitud=None,longitud=None,polygon=None,datageneral=pd.DataFrame(),datageneraluso=pd.DataFrame(),datacatastro=pd.DataFrame(),datausosuelo=pd.DataFrame(),datalote=pd.DataFrame(),datavigencia=pd.DataFrame(),datatransacciones=pd.DataFrame()):
    
    #-------------------------------------------------------------------------#
    # Data complemento
    input_complemento = datacomplemento(barmanpre=barmanpre,latitud=latitud,longitud=longitud,direccion=None,polygon=polygon,precuso=None)

    #-------------------------------------------------------------------------#
    # Data analisis predial
    input_predial = analytics_predial(datavigencia,datacatastro)

    #-------------------------------------------------------------------------#
    # Data analisis transacciones
    input_transacciones = analytics_transacciones(datatransacciones,datavigencia)

    labelbarrio = ""
    try:
        if isinstance(input_complemento['barrio'], str): 
            labelbarrio = f"[{input_complemento['barrio'].title()}]"
    except: pass

    tablaubicacion       = ""
    tablacaracteristicas = ""
    tablatipologia       = ""
    tablatransacciones   = ""
    tablapredial         = ""
    tablamarketventa     = ""
    tablamarketarriendo  = ""
    tablavalorizacion    = ""
    tablapot             = ""
    tablademografica     = ""
    tablatransporte      = ""
    tablasitp            = ""
    tablavias            = ""
    
    if not datausosuelo.empty:
        #---------------------------------------------------------------------#
        # Seccion ubicacion
        try:    barrio = datausosuelo['prenbarrio'].iloc[0]
        except: barrio = None
        try:    localidad = input_complemento['localidad'] if isinstance(input_complemento['localidad'], str) else None
        except: localidad = None
        try:    codigoupl = input_complemento['codigoupl'] if isinstance(input_complemento['codigoupl'], str) else None
        except: codigoupl = None       
        try:    upl = input_complemento['upl'] if isinstance(input_complemento['upl'], str) else None
        except: upl = None      
        try:    latlng = f"{round(latitud,2)}|{round(longitud,2)}"
        except: latlng = None
        
        formato   = {'Localidad:':localidad,'Código UPL:':codigoupl,'UPL:':upl,'Barrio:':barrio,'lat-lng':latlng}
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            tablaubicacion = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Ubicación</td></tr>{html_paso}</tbody></table></div>"""
            tablaubicacion = f"""<div class="col-md-6">{tablaubicacion}</div>"""
               
            
    if not datageneral.empty:
        #---------------------------------------------------------------------#
        # Seccion caracteristicas
        numlotes  = int(datageneral['num_lotes'].iloc[0])  if 'num_lotes' in datageneral else None
        preaterre = f"{datageneral['preaterre'].iloc[0]:,}"  if 'preaterre' in datageneral and isinstance(datageneral['preaterre'].iloc[0], float) else None
        preacons  = f"{datageneral['preaconst'].iloc[0]:,}"  if 'preaconst' in datageneral and isinstance(datageneral['preaconst'].iloc[0], float) else None
        predios   = int(datageneral['predios'].iloc[0])  if 'predios' in datageneral else None
        pisos     = int(datageneral['pisos'].iloc[0]) if 'pisos' in datageneral and isinstance(datageneral['pisos'].iloc[0], float) else None
        sotanos   = int(datageneral['sotanos'].iloc[0])  if 'sotanos' in datageneral and isinstance(datageneral['sotanos'].iloc[0], float) else None
        estrato   = int(datageneral['estrato'].iloc[0])  if 'estrato' in datageneral and isinstance(datageneral['estrato'].iloc[0], float) else None
        construcciones = int(datageneral['construcciones'].iloc[0])   if 'construcciones' in datageneral and isinstance(datageneral['construcciones'].iloc[0], float) else None
        vetustezmin = int(datageneral['vetustezmin'].iloc[0])  if 'vetustezmin' in datageneral else None
        vetustezmax = int(datageneral['vetustezmax'].iloc[0])  if 'vetustezmax' in datageneral else None
        try:    esquinero = input_complemento['esquinero'] if 'esquinero' in input_complemento and  isinstance(input_complemento['esquinero'], str) else None
        except: esquinero = None      
        try:    viaprincipal = input_complemento['viaprincipal'] if 'viaprincipal' in input_complemento and isinstance(input_complemento['viaprincipal'], str) else None
        except: viaprincipal = None  

        formato   = {'Número de lotes:':numlotes,'Área de terreno:':preaterre,'Área construida:':preacons,'Predios: ':predios,'Máximo número de pisos:':pisos,'Máximo número de sotanos:':sotanos,'Máximo número de construcciones:':construcciones,'Estrato:':estrato,'Antigüedad mínima:':vetustezmin,'Antigüedad máximo:':vetustezmax,'Esquinero:':esquinero,'Vía principal:':viaprincipal}
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            tablacaracteristicas = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Caracteristicas</td></tr>{html_paso}</tbody></table></div>"""
            tablacaracteristicas = f"""<div class="col-md-6">{tablacaracteristicas}</div>"""

    if not datageneraluso.empty:
        #---------------------------------------------------------------------#
        # Seccion Tipologias
        datageneraluso       = datageneraluso.sort_values(by='preaconst_precuso',ascending=False)
        datageneraluso.index = range(len(datageneraluso))
        if len(datageneraluso)>1:
            html_paso = ""
            for i in range(len(datageneraluso)):
                try:    usosuelo = datageneraluso['usosuelo'].iloc[i]
                except: usosuelo = ''            
                try:    areaconstruida = f"{round(datageneraluso['preaconst_precuso'].iloc[i],2):,}"
                except: areaconstruida = ''       
                try:    areaterreno = f"{round(datageneraluso['preaterre_precuso'].iloc[i],2):,}"
                except: areaterreno = '' 
                try:    predios = f"{int(datageneraluso['predios_precuso'].iloc[i]):,}"
                except: predios = ''                 
                
                html_paso += f"""
                <tr>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{usosuelo}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{predios}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaconstruida}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaterreno}</h6></td>
                </tr>
                """
                
            html_paso = f"""
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Predios</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área construida</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área de terreno</h6></td>
            {html_paso}
            """
            if html_paso!="":
                tablatipologia = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Tipologías de activos</td></tr>{html_paso}</tbody></table></div>"""
                tablatipologia = f"""<div class="col-md-12">{tablatipologia}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Transacciones
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
        tablatransacciones = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Transacciones</td></tr>{html_paso}</tbody></table></div>"""
        tablatransacciones = f"""<div class="col-md-6">{tablatransacciones}</div>"""
      
    #---------------------------------------------------------------------#
    # Seccion Predial
    try:    avaluomt2 = f"${round(input_predial['avaluocatastral'],0):,.0f} m²" if (isinstance(input_predial['avaluocatastral'],float) or isinstance(input_predial['avaluocatastral'],int)) else None
    except: avaluomt2 = None
    try:    predialmt2 = f"${round(input_predial['predial'],0):,.0f} m²" if (isinstance(input_predial['predial'],float) or isinstance(input_predial['predial'],int)) else None
    except: predialmt2 = None
    try:    propietarios = int(input_predial['propietarios'])
    except: propietarios = None
    formato   = {'Avalúo catastral:':avaluomt2,'Predial:':predialmt2, '# Propietarios (*):': propietarios}
    html_paso = ""
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
    if html_paso!="":
        tablapredial = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Información Catastral</td></tr>{html_paso}</tbody></table></div>"""
        tablapredial = f"""<div class="col-md-6">{tablapredial}</div>"""

    #---------------------------------------------------------------------#
    # Seccion precios de referencia
    if 'market_venta' in input_complemento:
        html_paso     = ""
        df            = pd.DataFrame(input_complemento['market_venta'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        df            = df.set_index('index').T.reset_index()
        if 'valor' in df: df['valor'] = df['valor'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        if 'obs'   in df: df['obs']   = df['obs'].apply(lambda x:   f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(x)}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        namedict = {'activos':'Listings Activos','historico':'Listings no Activos'}
        for i in ['activos','historico']:
            datapaso = df[df['index']==i]
            if not datapaso.empty:
                variables          = [x for x in ['valor', 'obs'] if x in datapaso]
                datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            else:
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td></tr>
                """

        if html_paso!="":
            tablamarketventa = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Precios de Referencia en Venta</td></tr>{html_paso}</tbody></table></div>"""
            tablamarketventa = f"""<div class="col-md-6">{tablamarketventa}</div>"""

    if 'market_arriendo' in input_complemento:
        html_paso     = ""
        df            = pd.DataFrame(input_complemento['market_arriendo'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        df            = df.set_index('index').T.reset_index()
        if 'valor' in df: df['valor'] = df['valor'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        if 'obs'   in df: df['obs']   = df['obs'].apply(lambda x:   f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(x)}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        namedict = {'activos':'Listings Activos','historico':'Listings no Activos'}
        for i in ['activos','historico']:
            datapaso = df[df['index']==i]
            if not datapaso.empty:
                variables          = [x for x in ['valor', 'obs'] if x in datapaso]
                datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            else:
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td></tr>
                """

        if html_paso!="":
            tablamarketarriendo = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Precios de Referencia en Arriendo</td></tr>{html_paso}</tbody></table></div>"""
            tablamarketarriendo = f"""<div class="col-md-6">{tablamarketarriendo}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Condiciones de mercado
    html_paso = ""
    if 'valorizacion' in input_complemento and isinstance(input_complemento['valorizacion'], list):
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
            html_paso += f"""
            {titulo}
            <tr><td style="border: none;"><h6></h6></td></tr>
            {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
            <tr><td style="border: none;"><h6></h6></td></tr>
            """
    if html_paso!="":
        tablavalorizacion = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Precios de referencia {labelbarrio}</td></tr>{html_paso}</tbody></table></div>"""
        tablavalorizacion = f"""<div class="col-md-6">{tablavalorizacion}</div>"""

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
            
        if html_paso!="":
            tablapot = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">P.O.T</td></tr>{html_paso}</tbody></table></div>"""
            tablapot = f"""<div class="col-md-12">{tablapot}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Demografica
    if 'dane' in input_complemento:
        html_paso = ""
        for key,value in input_complemento['dane'].items():
            try:    
                valor = "{:,}".format(int(value))
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{valor}</h6></td></tr>"""
            except: pass
        if html_paso!="":
            tablademografica = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Información Demográfica {labelbarrio}</td></tr>{html_paso}</tbody></table></div>"""
            tablademografica = f"""<div class="col-md-6">{tablademografica}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Transporte
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        tablatransporte = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Transmilenio</td></tr>{html_paso}</tbody></table></div>"""
        tablatransporte = f"""<div class="col-md-6">{tablatransporte}</div>"""

    #---------------------------------------------------------------------#
    # Seccion SITP
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        tablasitp = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">SITP</td></tr>{html_paso}</tbody></table></div>"""
        tablasitp = f"""<div class="col-md-6">{tablasitp}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Vias
    if 'vias' in input_complemento and isinstance(input_complemento['vias'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['vias']}</h6></td></tr>"""
        tablavias = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Vías</td></tr>{html_paso}</tbody></table></div>"""
        tablavias = f"""<div class="col-md-6">{tablavias}</div>"""
        
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
            table-layout: fixed; /* Ensures all columns have the same width */
            border-collapse: collapse; /* Ensures borders are collapsed */
        }
        .css-table td {
            text-align: left;
            padding: 0;
            white-space: nowrap;
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
          color: #6EA4EE;
          font-weight: bold;
          border: none;
          border-bottom: 2px solid #6EA4EE;
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
                    {tablacaracteristicas}
                    {tablatipologia}
                    {tablatransacciones}
                    {tablapredial}
                    {tablamarketventa }
                    {tablamarketarriendo}
                    {tablavalorizacion}
                    {tablapot}
                    {tablademografica}
                    {tablatransporte}
                    {tablasitp}
                    {tablavias}
                    <p style="margin-top:50px;font-size: 0.6em;color: #908F8F;">(*) cálculos aproximados<a href="#nota1">nota al pie</a>.</p>
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
def data2geopandas(data,color=None):
    urlexport = "http://localhost:8501/Busqueda_avanzada"
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        if isinstance(color, str): data['color'] = color #'#5A189A' #'#003F2D'
        else: data['color'] ='#5A189A'
    return data.to_json()

@st.cache_data
def tablestyle():
    return """
        <style>
            * {
                box-sizing: border-box;
                -webkit-box-sizing: border-box;
                -moz-box-sizing: border-box;
            }
        
            body {
                font-family: Helvetica;
                -webkit-font-smoothing: antialiased;
            }
        
            .table-background {
                background: rgba(71, 147, 227, 1);
            }
        
            h2 {
                text-align: center;
                font-size: 18px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: white;
                padding: 30px 0;
            }
        
            /* Table Styles */
        
            .table-wrapper {
                margin: 10px 70px 70px;
                box-shadow: 0px 35px 50px rgba(0, 0, 0, 0.2);
            }
        
            .fl-table {
                border-radius: 5px;
                font-size: 12px;
                font-weight: normal;
                border: none;
                border-collapse: collapse;
                width: 100%;
                max-width: 100%;
                white-space: nowrap;
                background-color: white;
            }
        
            .fl-table td,
            .fl-table th {
                text-align: center;
                padding: 8px;
            }
        
            .fl-table td {
                border-right: 1px solid #f8f8f8;
                font-size: 12px;
            }
        
            .fl-table thead th {
                color: #ffffff;
                background: #6EA4EE; /* Manteniendo el color verde claro para el encabezado */
                position: sticky; /* Haciendo el encabezado fijo */
                top: 0; /* Fijando el encabezado en la parte superior */
            }
        
            .fl-table tr:nth-child(even) {
                background: #f8f8f8;
            }
            .table-scroll {
                overflow-x: auto;
                overflow-y: auto;
                max-height: 400px; /* Altura máxima ajustable según tus necesidades */
            }
        
            @media (max-width: 767px) {
                .fl-table {
                    display: block;
                    width: 100%;
                }
                .table-wrapper:before {
                    content: "Scroll horizontally >";
                    display: block;
                    text-align: right;
                    font-size: 11px;
                    color: white;
                    padding: 0 0 10px;
                }
                .fl-table thead,
                .fl-table tbody,
                .fl-table thead th {
                    display: block;
                }
                .fl-table thead th:last-child {
                    border-bottom: none;
                }
                .fl-table thead {
                    float: left;
                }
                .fl-table tbody {
                    width: auto;
                    position: relative;
                    overflow-x: auto;
                }
                .fl-table td,
                .fl-table th {
                    padding: 20px .625em .625em .625em;
                    height: 60px;
                    vertical-align: middle;
                    box-sizing: border-box;
                    overflow-x: hidden;
                    overflow-y: auto;
                    width: 120px;
                    font-size: 13px;
                    text-overflow: ellipsis;
                }
                .fl-table thead th {
                    text-align: left;
                    border-bottom: 1px solid #f7f7f9;
                }
                .fl-table tbody tr {
                    display: table-cell;
                }
                .fl-table tbody tr:nth-child(odd) {
                    background: none;
                }
                .fl-table tr:nth-child(even) {
                    background: transparent;
                }
                .fl-table tr td:nth-child(odd) {
                    background: #f8f8f8;
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tr td:nth-child(even) {
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tbody td {
                    display: block;
                    text-align: center;
                }
            }
        </style>
        """
        
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }  