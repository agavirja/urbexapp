import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import folium
from shapely.geometry import Polygon,mapping,shape
from shapely.ops import cascaded_union,unary_union
from sqlalchemy import create_engine 
from datetime import datetime
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup


from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.getuso_destino import getuso_destino
from data.combinacion_poligonos import combinapolygons,num_combinaciones_lote
from data.googleStreetView import mapstreetview,mapsatelite
from data.datacomplemento import main as datacomplemento

from display.stylefunctions  import style_function_geojson

def main(code=None):

    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = 1920
    mapwidth   = int(screensize*0.25)
    mapheight  = int(screensize*0.20)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize*0.25)
        mapheight  = int(screensize*0.20)
    except: pass

    st.markdown(estilos(), unsafe_allow_html=True)

    #-------------------------------------------------------------------------#
    # Buscar data
    #-------------------------------------------------------------------------#
    with st.spinner('Buscando lotes'):
        datapredios,datalotescatastro,datalong,datausosuelo = getdatacombinacionlotes(code)
    
    #-------------------------------------------------------------------------#
    # Seleccionar la combinacion de lotes
    #-------------------------------------------------------------------------#
    datapaso = pd.DataFrame()
    if not datapredios.empty:
        datapredios.index = range(1,len(datapredios)+1)
        if len(datapredios)>1:
            col1,col2   = st.columns(2)
            with col1:
                comb     = st.selectbox('Ver combinaciones de lotes:',options = datapredios.index.unique())
                datapaso = datapredios.iloc[[comb-1]].copy()
                st.write('')
                st.write('')
        else:
            datapaso = datapredios.copy()
        
    #-------------------------------------------------------------------------#
    # Mapa
    #-------------------------------------------------------------------------#
    col1,col2,col3,col4,col5   = st.columns([0.2,0.02,0.2,0.05,0.5])
    latitud,longitud = [None]*2
    if not datapaso.empty:
        
        try:
            polygon  = wkt.loads(datapaso['wkt'].iloc[0]) 
            latitud  = polygon.centroid.y
            longitud = polygon.centroid.x
        except: pass
    
        if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
           
            m  = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
            
            folium.GeoJson(polygon, style_function=style_function).add_to(m)
            
            df = pd.DataFrame()
            if not datalong.empty: df = datalong[datalong['id']==datapaso['id'].iloc[0]]
            if not df.empty:
                geojson = data2geopandas(df)
                popup   = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            with col5:
                st_map = st_folium(m,width=1000,height=400)

    #-------------------------------------------------------------------------#
    # Google maps streetview
    #-------------------------------------------------------------------------#
    with col3:
        if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
            html = mapstreetview(latitud,longitud)
            st.components.v1.html(html, width=int(mapwidth*0.8), height=mapheight)
    with col1:
        if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
            html = mapsatelite(latitud,longitud)
            st.components.v1.html(html, width=int(mapwidth*0.8), height=mapheight)
    
    #-------------------------------------------------------------------------#
    # Data complemento
    #-------------------------------------------------------------------------#
    precuso   = None
    barmanpre = None
    direccion = None
    if not datausosuelo.empty and 'precuso' in datausosuelo: 
        precuso = list(datausosuelo['precuso'].unique())
    
    if latitud is None and longitud is None and not datausosuelo.empty and 'latitud' in datausosuelo and 'longitud' in datausosuelo:
        latitud  = datausosuelo['latitud'].iloc[0]
        longitud = datausosuelo['longitud'].iloc[0]
    
    if not datalong.empty:
        if 'barmanpre' in datalong:
            barmanpre = list(datalong['barmanpre'].unique())
        if 'formato_direccion' in datalong:
            direccion = list(datalong['formato_direccion'].unique())

    polygonstr = None
    if not datapaso.empty and 'wkt' in datapaso:
        polygonstr = str(datapaso['wkt'].iloc[0])
    input_complemento = datacomplemento(barmanpre=code,latitud=latitud,longitud=longitud,direccion=direccion,polygon=polygonstr,precuso=precuso)
    
    #-------------------------------------------------------------------------#
    # Tabla descriptiva
    #-------------------------------------------------------------------------# 
    col1, col2 = st.columns(2)       
    datalotesparticulares = pd.DataFrame()
    if not datalong.empty: datalotesparticulares = datalong[datalong['id']==datapaso['id'].iloc[0]]
    html = principal_table(datalotegeneral=datapaso.copy(),datalotesparticulares=datalotesparticulares,input_complemento=input_complemento)
    #texto = BeautifulSoup(html, 'html.parser')
    #st.markdown(texto, unsafe_allow_html=True)
    st.components.v1.html(html,height=900,scrolling=True)

    #-------------------------------------------------------------------------#
    # Tabla Transacciones
    #-------------------------------------------------------------------------#
    if not datalotesparticulares.empty and len(datalotesparticulares)>1:       
        
        col1,col2,col3,col4 = st.columns([0.04,0.2,0.5,0.26])
        with col3:
            st.write('')
            titulo = 'Combinacion de lotes'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
        tableH    = 60*len(datalotesparticulares)
        html_paso = ""
        for _,items in datalotesparticulares.iterrows():
            try:    barrio = f"{items['prenbarrio']}"
            except: barrio = ''  
            try:    direccion = f"{items['formato_direccion']}"
            except: direccion = ''
            try:    areaconstruida = f"{round(items['preaconst'],2)}"
            except: areaconstruida = ''     
            try:    areaterreno = f"{round(items['preaterre'],2)}"
            except: areaterreno = ''
            try:    estrato = f"{int(items['estrato'])}"
            except: estrato = ""
            try:    predios = f"{int(items['predios'])}"
            except: predios = ""
            try:    pisos = f"{int(items['connpisos'])}"
            except: pisos = ""
            try:    sotanos = f"{int(items['connsotano'])}"
            except: sotanos = ""
            try:    construcciones = f"{int(items['construcciones'])}"
            except: construcciones = ""
            try:    antiguedadmin = f"{int(items['prevetustzmin'])}"
            except: antiguedadmin = ""
            try: 
                antiguedadmax = items['prevetustzmax'] if 'prevetustzmax' in items and 'prevetustzmin' in items and items['prevetustzmax']>items['prevetustzmin'] else ""
                antiguedadmax = f"{int(items['antiguedadmax'])}"
            except: antiguedadmax = ""
            
            try:    link = f"http://localhost:8501/Busqueda_avanzada?type=predio&code={items['barmanpre']}&vartype=barmanpre"
            except: link = ""
            html_paso += f"""
            <tr>
                <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                   <a href="{link}" target="_blank">
                   <img src="https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png" alt="link" width="20" height="20">
                   </a>                    
                </td>
                <td>{barrio}</td>
                <td>{direccion}</td>
                <td>{areaterreno}</td> 
                <td>{areaconstruida}</td>
                <td>{estrato}</td>
                <td>{predios}</td>
                <td>{pisos}</td>
                <td>{sotanos}</td>
                <td>{construcciones}</td>
                <td>{antiguedadmin}</td>
            </tr>
            """
        html_paso = f"""
        <thead>
            <tr>
                <th>Link</th>
                <th>Barrio</th>
                <th>Dirección</th>
                <th>Área de terreno</th>
                <th>Área construida</th>
                <th>Estrato</th>
                <th>Predios</th>
                <th>Pisos Máx</th>
                <th>Sotanos</th>
                <th>Construcciones</th>
                <th>Antiguedad</th>            
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
def getdatacombinacionlotes(code):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    datapredios       = pd.DataFrame()
    datalotescatastro = pd.DataFrame()
    datalong          = pd.DataFrame()
    try: 
        lista = str(code).split('|')
        query       = "','".join(lista)
        query       = f" id IN ('{query}')"   
        datapredios = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_consolidacion_lotes_2000 WHERE {query}" , engine)
    except: pass

    if not datapredios.empty:
        barmanprelist = datapredios['barmanpre'].str.split('|')
        barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
        barmanprelist = list(set(barmanprelist))
        
        query = "','".join(barmanprelist)
        query = f" lotcodigo IN ('{query}')"   
        datalotescatastro = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        datalotescatastro = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')
        datapredios       = combinapolygons(datapredios.copy(),datalotescatastro.copy())

        query = "','".join(barmanprelist)
        query = f" barmanpre IN ('{query}')"   
        datacompacta = pd.read_sql_query(f"SELECT barmanpre,prenbarrio,formato_direccion,preaconst,preaterre,prevetustzmin,prevetustzmax,estrato,predios,connpisos,connsotano,construcciones FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)
        dataprecuso  = pd.read_sql_query(f"SELECT precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst_total,preaterre_total,predios_total FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        
    if not datacompacta.empty and not datalotescatastro.empty:
        datamerge    = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')
        datacompacta = datacompacta.merge(datamerge[['barmanpre','wkt']],on='barmanpre',how='left',validate='m:1')
        
    if not datapredios.empty and  not datacompacta.empty:
        datamerge       = datacompacta.drop_duplicates(subset='barmanpre',keep='first')
        datalong              = datapredios.copy()
        datalong['barmanpre'] = datalong['barmanpre'].str.split('|')
        datalong              = datalong.explode('barmanpre')
        datalong              = datalong[['id','barmanpre']].merge(datamerge,on='barmanpre',how='left',validate='m:1')
       
    return datapredios,datalotescatastro,datalong,dataprecuso
    
@st.cache_data(show_spinner=False)
def data2geopandas(data):
    
    urlexport = "http://localhost:8501/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = ""
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            
            barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre"

            infopopup = ""
            try:    infopopup += f"""<b> Dirección:</b> {items['formato_direccion']}<br>"""
            except: pass
            try:    infopopup += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """
            except: pass
            try:    infopopup += f"""<b> Área construida total:</b> {round(items['preaconst'],2)}<br>"""
            except: pass
            try:    infopopup += f"""<b> Área de terreno:</b> {round(items['preaterre'],2)}<br> """
            except: pass
            try:    infopopup += f"""<b> Estrato:</b> {int(items['estrato'])}<br> """
            except: pass
            try:    infopopup += f"""<b> Pisos:</b> {int(items['connpisos'])}<br> """
            except: pass
            try:    infopopup += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>"""
            except: pass            
            try:    infopopup += f"""<b> Total de matriculas:</b> {int(items['predios'])}<br> """
            except: pass            
            try:    infopopup += f"""<b> Construcciones:</b> {int(items['construcciones'])}<br> """
            except: pass               

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {infopopup}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def principal_table(datalotegeneral=pd.DataFrame(),datalotesparticulares=pd.DataFrame(),input_complemento={}):
    
    #---------------------------------------------------------------------#
    # Seccion ubicacion
    tablaubicacion = ""
    try:    barrio = datalotesparticulares['prenbarrio'].iloc[0]
    except: barrio = None
    try:    direccion = datalotesparticulares['formato_direccion'].iloc[0]
    except: direccion = None
    try:    estrato = int(datalotesparticulares['estrato'].iloc[0])
    except: estrato = None
    try:    localidad = input_complemento['localidad'] if isinstance(input_complemento['localidad'], str) else None
    except: localidad = None
    try:    codigoupl = input_complemento['codigoupl'] if isinstance(input_complemento['codigoupl'], str) else None
    except: codigoupl = None       
    try:    upl = input_complemento['upl'] if isinstance(input_complemento['upl'], str) else None
    except: upl = None      
    
    formato   = {'Dirección:':direccion,'Localidad:':localidad,'Código UPL:':codigoupl,'UPL:':upl,'Barrio:':barrio,'Estrato:':estrato}
    html_paso = ""
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
    if html_paso!="":
        tablaubicacion = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Ubicación</td></tr>{html_paso}</tbody></table></div>"""
        tablaubicacion = f"""<div class="col-md-6">{tablaubicacion}</div>"""
           
    #---------------------------------------------------------------------#
    # Informacion del terreno
    tabladescripcion = ""
    html_paso        = ""
    try:    nlotes = f"{len(datalotesparticulares)}" 
    except: nlotes = None
    try:    areaterreno = f"{round(datalotegeneral['preaterre'].iloc[0],2)} m²"
    except: areaterreno = None    
    try:    areaconstruida = f"{round(datalotegeneral['preaconst'].iloc[0],2)} m²"
    except: areaconstruida = None  
    try:    predios = f"{int(datalotegeneral['predios'].iloc[0])}"
    except: predios = None  
    try:    maxpisos = f"{int(datalotegeneral['maxpisos'].iloc[0])}"
    except: maxpisos = None  
    try:    esquinero = 'Si' if datalotegeneral['esquinero'].iloc[0]==1 else 'No'
    except: esquinero = None  
    
    formato   = {'# de Lotes que conforman el terreno:':nlotes,'Predios:':predios,'Área de terreno:':areaterreno,'Área construida:':areaconstruida,'Pisos máximos construidos':maxpisos,'Esquinero':esquinero}
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
 
    if html_paso!="":
        tabladescripcion = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Información del Terreno</td></tr>{html_paso}</tbody></table></div>"""
        tabladescripcion = f"""<div class="col-md-6">{tabladescripcion}</div>"""

    #---------------------------------------------------------------------#
    # POT
    tablapot = ""
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
    tablademografica = ""
    labelbarrio = ""
    try:
        if isinstance(barrio, str): 
            labelbarrio = f'[{barrio.title()}]'
    except: pass
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
    tablatransporte = ""
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        tablatransporte = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Transmilenio</td></tr>{html_paso}</tbody></table></div>"""
        tablatransporte = f"""<div class="col-md-6">{tablatransporte}</div>"""

    #---------------------------------------------------------------------#
    # Seccion SITP
    tablasitp = ""
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        tablasitp = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">SITP</td></tr>{html_paso}</tbody></table></div>"""
        tablasitp = f"""<div class="col-md-6">{tablasitp}</div>"""

    #---------------------------------------------------------------------#
    # Seccion Vias
    tablavias = ""
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
        }
        .css-table td {
            text-align: left;
            padding: 0;
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
        }
        .css-table td[colspan="labelsectionborder"] {
          text-align: left;
          border: none;
          border-bottom: 2px solid blue;
          margin-top: 20px;
          display: block;
          padding: 0;
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
                    {tabladescripcion}
                    {tablapot}
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
    return html

def style_function(feature):
    return {
        'fillColor': '#fff',
        'color': 'blue',
        'weight': 2,
        'dashArray': '3, 3'
    }

@st.cache_data
def estilos():
    styles =  f"""
    <style>

    .stApp {{
        background-color: #FAFAFA;        
        opacity: 1;
        background-size: cover;
    }}
    
    div[data-testid="collapsedControl"] {{
        color: #fff;
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

    #MainMenu {{
    visibility: hidden; 
    height: 0%;
    }}
    header {{
        visibility: hidden; 
        height: 0%;
        }}
    footer {{
        visibility: hidden; 
        height: 0%;
        }}
    div[data-testid="stSpinner"] {{
        color: #000000;
        }}
    
    a[href="#responsive-table"] {{
        visibility: hidden; 
        height: 0%;
        }}
    
    a[href^="#"] {{
        /* Estilos para todos los elementos <a> con href que comienza con "#" */
        visibility: hidden; 
        height: 0%;
        overflow-y: hidden;
    }}

    div[class="table-scroll"] {{
        background-color: #a6c53b;
        visibility: hidden;
        overflow-x: hidden;
        }}
        
    </style>
    """
    return styles
    
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
    
if __name__ == "__main__":
    main()
