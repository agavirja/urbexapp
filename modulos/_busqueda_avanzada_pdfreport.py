import streamlit as st
import pandas as pd
import shapely.wkt as wkt
import plotly.express as px
import geojson as geojsonlib
import tempfile
import pdfcrowd
from shapely.geometry import mapping
from bs4 import BeautifulSoup
from sqlalchemy import create_engine 
from streamlit_js_eval import streamlit_js_eval

from modulos._busqueda_avanzada_descripcion_lote import principal_table as html_descripcion_lote, showlistings,gruoptransactions,graficasHtml as graficasHtml_descripcion_lote
from modulos._busqueda_avanzada_analisis_unidad import principal_table as html_unidad, linkPredial,buildname,buildphone,buildemail, graficasHtml as graficasHtml_unidad

from data.getlatlng import getlatlng
from data.getdatabuilding import main as getdatabuilding
from data.circle_polygon import circle_polygon
from data.data_listings import buildingMarketValues
from data.getdata_market_analysis import main as getdata_market_analysis
from data.reporte_analisis_mercado import reporteHtml as reporteHtml_estudio_mercado, data2geopandas,TransactionMarker
from data.getuso_destino import usosuelo_class

def main(chip=None,barmanpre=None):
    
    screensize = 1920
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass

    datadestinouso = usosuelo_class()
    datachips      = chipsfrombarmanpre(barmanpre=barmanpre)
    
    precdestin,precuso = [None]*2
    metros             = 500
    market,building,predio,logo = [None]*4
    
    col1,col2,col3 = st.columns([0.25,0.5,0.25])
    with col2:
        with st.container(border=True):
            st.subheader('¿Qué módulos quieres incluir en el reporte en PDF?')
            
            building = st.toggle("Descripción general",value=True)

            #-----------------------------------------------------------------#
            predio = st.toggle("Incluir análisis de unidad",value=False)
            if predio==True:
                if not datachips.empty:
                    predirecc = None
                    if isinstance(chip, str): 
                        try:    predirecc = datachips[datachips['chip']==chip]['predirecc'].iloc[0]
                        except: pass 
                    
                    options = list(sorted(datachips[datachips['predirecc'].notnull()]['predirecc'].unique())) 
                    index   = 0
                    if isinstance(predirecc, str):
                        index = options.index(predirecc)
                    predirecc = st.selectbox('Lista de direcciones',options=options,index=index)

                    try: chip = datachips[datachips['predirecc']==predirecc]['chip'].iloc[0]
                    except: pass
                    st.write('')
                    st.write('')
            #-----------------------------------------------------------------#
            market   = st.toggle("Estudio de mercado",value=False)
            if market==True:
                st.write('Filtrar la información del estudio de mercado por:')
                options    = ['Todos'] + list(sorted(datadestinouso[datadestinouso['clasificacion'].notnull()]['clasificacion'].unique()))
                destino    = st.selectbox('Tipo:',options=options)
                if 'todo' not in destino.lower() :
                    datadestinouso = datadestinouso[datadestinouso['clasificacion']==destino]

                options  = ['Todos'] + list(sorted(datadestinouso[datadestinouso['usosuelo'].notnull()]['usosuelo'].unique()))
                usosuelo = st.selectbox('Uso del suelo:',options=options)
                if 'todo' not in usosuelo.lower():
                    datadestinouso = datadestinouso[datadestinouso['usosuelo']==usosuelo]
                    
                precuso = list(datadestinouso['precuso'].unique())
                metros  = st.selectbox('Metros a la redonda',options=[100,200,300,400,500],index=4)
                st.write('')
                st.write('')
                
            #-----------------------------------------------------------------#
            listingsA  = st.toggle("Listings activos",value=True)
            listingsNA = st.toggle("Listings históricos (NO activos)",value=False)
            
            #-----------------------------------------------------------------#
            logo = st.toggle("Incluir el logo de la empresa",value=True)
              
            if st.button('Generar PDF'):
                with st.spinner('Generando reporte, por favor espera un momento'):
                    html = reportehtml(barmanpre=barmanpre,chip=chip,building=building,market=market,predio=predio,logo=logo,precuso=precuso,metros=metros,listingsA=listingsA,listingsNA=listingsNA,mapwidth=mapwidth,mapheight=200)
                    
                    #API_KEY      = 'e03f4c6097c664281d195cb71357a2a4'
                    #pdfcrowduser = 'urbexventas'
                    #wd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf")       
                    
                    if 'token' not in st.session_state: 
                        st.session_state.token = None
                        
                    #logo = getlogofromtoken(st.session_state.token)
                    #header_html = f"""
                    #<div style="text-align: right;">
                    #    <img src="{logo}" style="width: 100px; height: auto;">
                    #</div>
                    #"""
                    
                    #client = pdfcrowd.HtmlToPdfClient(pdfcrowduser,API_KEY)
                    #client.setHeaderHtml(header_html)
                    #client.setPageHeight('-1')
                    #client.convertStringToFile(html, pdf_temp_path)

                    #with open(pdf_temp_path, "rb") as pdf_file:
                    #    PDFbyte = pdf_file.read()

                    #with open(r"D:\...\reporte.html", "w", encoding="utf-8") as file:
                    #    file.write(html)
                        
                    #st.download_button(label="Descargar PDF",
                    #                    data=PDFbyte,
                    #                    file_name="reportePDF.pdf",
                    #                    mime='application/octet-stream')
                    
                    temp_html = 'temp_reporte.html'
                    with open(temp_html, 'w') as file:
                        file.write(html)

                    with open(temp_html, "r") as html_file:
                        HTMLbyte = html_file.read()
                    
                    if HTMLbyte:
                        st.download_button(label="Descargar Reporte",
                                           data=HTMLbyte,
                                           file_name="reporte-urbex.html",
                                           mime='text/html')
    
def style_function_geojson(feature):
    return {
        'fillColor': '#0000ff',
        'color': '#0000ff',
        'weight': 2,
        'opacity': 1,
        'fillOpacity': 0.6,
    }

@st.cache_data(show_spinner=False)
def reportehtml(barmanpre=None,chip=None,building=False,market=False,predio=False,logo=None,precuso=None,metros=500,listingsA=False,listingsNA=False,mapwidth=1920,mapheight=200):
    html = ""
    
    #-------------------------------------------------------------------------#
    # Reporte general:
    datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
    datausopredio = usosuelo_class()

    latitud   = datalote['latitud'].iloc[0]  if 'latitud'  in datalote and isinstance(datalote['latitud'].iloc[0], float)  else None
    longitud  = datalote['longitud'].iloc[0] if 'longitud' in datalote and isinstance(datalote['longitud'].iloc[0], float) else None
    polygon   = None
    if not datalote.empty and 'wkt' in datalote:
        polygon = wkt.loads(datalote['wkt'].iloc[0]) 

    if latitud is None and longitud is None and polygon:
        try:
            polygonl = wkt.loads(polygon) 
            latitud  = polygonl.centroid.y
            longitud = polygonl.centroid.x
        except: 
            try:
                latitud  = polygon.centroid.y
                longitud = polygon.centroid.x
            except: pass
        
    direccion = None
    if not datausosuelo.empty:
        try:    direccion = datausosuelo['formato_direccion'].iloc[0]
        except: pass
    if not latitud and not longitud: 
        ciudad           = 'bogota'
        latitud,longitud = getlatlng(f"{direccion},{ciudad},colombia")
        
    polygonstr = None
    if polygon is not None: polygonstr = str(polygon)
    if building:
        html_general,_ = html_descripcion_lote(code=barmanpre,datacatastro=datacatastro,datausosuelo=datausosuelo,datalote=datalote,datavigencia=datavigencia,datatransacciones=datatransacciones,polygon=polygonstr,latitud=latitud,longitud=longitud,direccion=direccion)
        try:
            soup = BeautifulSoup(html_general, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>','').replace('</body>','')
            titulo = 'Análisis General'
            html += f"""<div class="header-container" style="margin-bottom:50px"><h1 class="header-title">{titulo}</h1></div>"""
            html += soup
        except: pass

    datalistings = pd.DataFrame()
    if listingsA or listingsNA:
        if direccion is not None:
            datalistings = buildingMarketValues(direccion,precuso=None,mpioccdgo=None)

    if not datalistings.empty: 
        datalistings = datalistings.sort_values(by='tipo',ascending=True)
        datalistings = datalistings.drop_duplicates(subset=['tipoinmueble','tiponegocio','valor','areaconstruida','direccion'])
            
    if building:
        idd                = datausopredio['clasificacion'].isin(['Depósitos','Parqueadero','Otros'])
        datausopredio_paso = datausopredio[~idd]
        lista_precuso      = list(datausopredio_paso['precuso'].unique())

        datavigencia_gg      = mergeprecuso(datacatastro=datacatastro,datavigencia=datavigencia)
        datatransacciones_gg = datatransacciones[datatransacciones['precuso'].isin(lista_precuso)] if not datatransacciones.empty else pd.DataFrame()

        html_graficas,_ = graficasHtml_descripcion_lote(datatransacciones=datatransacciones_gg,datavigencia=datavigencia_gg,datalistings=datalistings,datacatastro=datacatastro,datausosuelo=datausosuelo,datausopredio=datausopredio,mapwidth=mapwidth,mapheight=220)
        try:
            soup = BeautifulSoup(html_graficas, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())  
            soup = soup.replace('"b":100', '"b":0').replace('"b":50', '"b":20')
            soup = soup.replace('<body>','').replace('</body>','')
            titulo = 'Estadísticas Generales'
            html += f"""<div class="header-container" style="margin-bottom:50px"><h1 class="header-title">{titulo}</h1></div>"""
            html += soup
        except: pass
    
    #-------------------------------------------------------------------------#
    # Tabla Transacciones
    #-------------------------------------------------------------------------#
    if not datatransacciones.empty:       
        
        datapaso  = gruoptransactions(datatransacciones.copy())
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
        titulo = 'Tabla de transacciones'
        html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
        html += f"""
        <div class="table-wrapper table-background">
            <div class="table-scroll">
                <table class="fl-table">
                    <thead>
                        <tr>
                            <th>Grupo</th>
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
                </table>
            </div>
        </div>
        """
            
    #-------------------------------------------------------------------------#
    # Reporte unidad:
    datacatastro_predio,datausosuelo_predio,datavigencia_predio,datatransacciones_predio = [pd.DataFrame()]*4 
    if predio:
        if isinstance(chip, str):
            if not datacatastro.empty:
                datacatastro_predio = datacatastro[datacatastro['prechip']==chip]
            if not datavigencia.empty:
                datavigencia_predio = datavigencia[datavigencia['chip']==chip]
                if not datavigencia_predio.empty: 
                    datavigencia_predio['link']  = datavigencia_predio.apply(lambda x: linkPredial(x['chip'],x['vigencia'],x['idSoporteTributario']),axis=1)
                    datavigencia_predio['name']  = datavigencia_predio.apply(lambda x: buildname(x['primerNombre'],x['segundoNombre'],x['primerApellido'],x['segundoApellido']),axis=1)
                    varphones             = [x for x in ['telefono1','telefono2','telefono3','telefono4','telefono5'] if x in datavigencia_predio]
                    datavigencia_predio['phone'] = datavigencia_predio[varphones].apply(buildphone, axis=1)
                    varemails             = [x for x in ['email1','email2'] if x in datavigencia_predio]
                    datavigencia_predio['email'] = datavigencia_predio[varemails].apply(buildemail, axis=1)
                    
            if not datatransacciones.empty:
                datatransacciones_predio = datatransacciones[datatransacciones['prechip']==chip]
            if not datacatastro_predio.empty and not datausosuelo.empty:
                datausosuelo_predio = datausosuelo[datausosuelo['precuso']==datacatastro_predio['precuso'].iloc[0]]
                
            html_descripcion_unidad,_ = html_unidad(datacatastro=datacatastro_predio,datausosuelo=datausosuelo_predio,datavigencia=datavigencia_predio)
            try:
                soup = BeautifulSoup(html_descripcion_unidad, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>','').replace('</body>','')
                titulo = 'Análisis detallado del predio'
                html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
                html += soup
            except: pass
        
    if not datatransacciones_predio.empty:       
        datapaso  = gruoptransactions(datatransacciones_predio.copy())
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
        titulo = 'Transacciones del predio'
        html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
        html += f"""
        <div class="table-wrapper table-background">
            <div class="table-scroll">
                <table class="fl-table">
                    <thead>
                        <tr>
                            <th>Grupo</th>
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
                </table>
            </div>
        </div>
        """
        
    if not datacatastro_predio.empty or not datavigencia_predio.empty:
        html_graficas,_ = graficasHtml_unidad(datatransacciones=datatransacciones_predio,datavigencia=datavigencia_predio,mapwidth=mapwidth,mapheight=200)
        try:
            soup = BeautifulSoup(html_graficas, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())  
            soup = soup.replace('"b":100', '"b":0')
            soup = soup.replace('<body>','').replace('</body>','')
            html += soup
        except: pass

    #-------------------------------------------------------------------------#
    # Estudio de mercado
    metros  = metros if isinstance(metros, int) else 500
    polygon = None
    if (isinstance(latitud, float) or isinstance(latitud, int)) or (isinstance(longitud, float) or isinstance(longitud, int)):
        polygon  = str(circle_polygon(metros,latitud,longitud))
            
    if market and isinstance(polygon,str):
        datapredios_estudio,datacatastro_estudio,datavigencia_estudio,datatransacciones_estudio,datamarket_estudio = getdata_market_analysis(polygon=polygon,precuso=precuso)

        dataoutput = datapredios_estudio.sort_values(by='transacciones',ascending=False).drop_duplicates(subset='barmanpre',keep='first')
        geojson    = data2geopandas(dataoutput,barmanpreref=None)
        geopoints  = TransactionMarker(datapredios_estudio.copy(),datatransacciones_estudio.copy())
        geocircle  = geojsonlib.Feature(geometry=mapping(wkt.loads(polygon)), properties={"color": "#828DEE"})
 
        
        titulo     = 'Estudio de mercado'
        html      += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""

        v = """
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 16
        }).addTo(map);
        """
        html += f"""
        <div id="map"></div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonCircle = {geocircle};
            var geojsonData = {geojson}
            var geojsonPoints = {geopoints};
            
            var map = L.map('map').setView([{latitud}, {longitud}], 16);
            {v}
            
            function style(feature) {{
                return {{
                    color: feature.properties.color,
                    weight: 1,
                }};
            }}
    
            function pointToLayer(feature, latlng) {{
                        return L.circleMarker(latlng, {{
                            radius: 2,
                            color: feature.properties.color,
                            weight: 1,
                        }});
                    }}

            L.geoJSON(geojsonData, {{
                style: style
            }}).addTo(map);
        
            L.geoJSON(geojsonPoints, {{
                pointToLayer: pointToLayer
            }}).addTo(map);
        
            L.geoJSON(geojsonCircle, {{
                style: style
            }}).addTo(map);
        </script>
        """
        html_reporte_estudio = reporteHtml_estudio_mercado(datapredios=datapredios_estudio,datacatastro=datacatastro_estudio,datatransacciones=datatransacciones_estudio,datavigencia=datavigencia_estudio,datamarket=datamarket_estudio,mapwidth=mapwidth/(0.4),mapheight=200)
        try:
            soup = BeautifulSoup(html_reporte_estudio, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>','').replace('</body>','')
            titulo = ""
            html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
            html += soup
        except: pass

    #-------------------------------------------------------------------------#
    # Data Listings
    #-------------------------------------------------------------------------#        
    if not datalistings.empty and listingsA:
        datapaso = datalistings[datalistings['tipo']=='activos']
        if not datapaso.empty:
            datapaso = datapaso.sort_values(by='tiponegocio',ascending=True)
            html_listings_paso = showlistings(datapaso)
            try:
                soup = BeautifulSoup(html_listings_paso, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>', '').replace('</body>','')
                titulo = 'Listings activos'
                html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
                html += soup
            except: pass

    if not datalistings.empty and listingsNA:
        datapaso = datalistings[datalistings['tipo']=='historico']
        if not datapaso.empty:
            datapaso = datapaso.sort_values(by='tiponegocio',ascending=True)
            html_listings_paso = showlistings(datapaso)
            try:
                soup = BeautifulSoup(html_listings_paso, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>', '').replace('</body>','')
                titulo = 'Listings no activos'
                html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
                html += soup
            except: pass

    # GOOGLE #
    YOUR_API_KEY = st.secrets['API_KEY'] # "AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw"
    # static map
    #static_map = f'https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=15&size=600x450&maptype=roadmap&key={YOUR_API_KEY}'
    # streetview google: 
    streetview = f'https://maps.googleapis.com/maps/api/streetview?size=600x450&location={latitud},{longitud}&heading=0&pitch=0&key={YOUR_API_KEY}'
    # satelital google: 
    satelital = f'https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=20&size=600x450&maptype=satellite&key={YOUR_API_KEY}'

    # MAPBOX #
    access_token   = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'
    # static map
    #static_map = f'https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/pin-s+3b83bd({longitud},{latitud})/{longitud},{latitud},14,0,0/420x250?access_token={access_token}'
    static_map = f'https://api.mapbox.com/styles/v1/mapbox/light-v10/static/pin-s+3b83bd({longitud},{latitud})/{longitud},{latitud},17,0,0/420x250?access_token={access_token}'
    # streetview mapbox: 
    #streetview = f'https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/pin-s+3b83bd({longitud},{latitud})/{longitud},{latitud},14,0,0/600x450?access_token={access_token}'
    # satelital mapbox: 
    #satelital = f'https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/pin-s+3b83bd({longitud},{latitud})/{longitud},{latitud},14,0/600x450?access_token={access_token}'
    
    if html!='':
        logo = 'https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png'
        header_html = f"""
        <div class="header">
            <img src="{logo}" alt="Logo">
        </div>
        """
        style = f"""
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            .header {{
                display: flex;
                justify-content: flex-end;
                align-items: center;
                padding: 10px;
            }}
            .header img {{
                width: 200px;
                height: auto;
            }}
                    
            .card {{
                --bs-card-spacer-y: 1rem;
                --bs-card-spacer-x: 1rem;
                --bs-card-title-spacer-y: 0.5rem;
                --bs-card-title-color: #000;
                --bs-card-subtitle-color: #6c757d;
                --bs-card-border-width: 1px;
                --bs-card-border-color: rgba(0, 0, 0, 0.125);
                --bs-card-border-radius: 0.25rem;
                --bs-card-box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                --bs-card-inner-border-radius: calc(0.25rem - 1px);
                --bs-card-cap-padding-y: 0.5rem;
                --bs-card-cap-padding-x: 1rem;
                --bs-card-cap-bg: rgba(0, 123, 255, 0.03);
                --bs-card-cap-color: #007bff;
                --bs-card-height: auto;
                --bs-card-color: #000;
                --bs-card-bg: #fff;
                --bs-card-img-overlay-padding: 1rem;
                --bs-card-group-margin: 0.75rem;
                position: relative;
                display: flex;
                flex-direction: column;
                min-width: 0;
                height: var(--bs-card-height);
                color: var(--bs-card-color);
                word-wrap: break-word;
                background-color: var(--bs-card-bg);
                background-clip: border-box;
                border: var(--bs-card-border-width) solid var(--bs-card-border-color);
                border-radius: var(--bs-card-border-radius);
                box-shadow: var(--bs-card-box-shadow);
            }}
            
            .card-stats .icon-big {{
                font-size: 3rem;
                line-height: 1;
                color: #fff;
            }}
            
            .card-stats .icon-primary {{
                background-color: #007bff;
            }}
            
            .bubble-shadow-small {{
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                border-radius: 50%;
                padding: 1rem;
            }}
            
            .card-stats .numbers {{
                font-size: 2rem;
                font-weight: bold;
                text-align: center;
            }}
            
            .card-stats .card-category {{
                color: #6c757d;
                font-size: 0.8rem;
                margin: 0;
                text-align: center;
            }}
            
            .card-stats .card-title {{
                margin: 0;
                font-size: 1.2rem;
                font-weight: bold;
                text-align: center;
            }}
            
            .small-text {{
                font-size: 0.3rem; 
                color: #6c757d; 
            }}
            
            .graph-container {{
                width: 100%;
                height: 100%;
                margin-bottom: 0;
            }}
            
            .card-custom {{
                height: 215px;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
            }}
            
            .card-body-custom {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                text-align: center;
            }}
            
            .css-table {{
                overflow-x: auto;
                overflow-y: auto;
                width: 100%;
                height: 100%;
            }}
            
            .css-table table {{
                width: 100%;
                padding: 0;
                table-layout: fixed; 
                border-collapse: collapse;
            }}
            
            .css-table td {{
                text-align: left;
                padding: 0;
                overflow: hidden; 
                text-overflow: ellipsis; 
            }}
            
            .css-table h6 {{
                line-height: 1; 
                font-size: 50px;
                padding: 0;
            }}
            
            .css-table td[colspan="labelsection"] {{
                text-align: left;
                font-size: 15px;
                color: #A16CFF;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #A16CFF;
                margin-top: 20px;
                display: block;
                font-family: 'Inter';
                width: 100%;
            }}
            
            .css-table td[colspan="labelsectionborder"] {{
                text-align: left;
                border: none;
                border-bottom: 2px solid blue;
                margin-top: 20px;
                display: block;
                padding: 0;
                width: 100%;
            }}
            
            #top {{
                position: absolute;
                top: 0;
            }}
            
            #top:target::before {{
                content: '';
                display: block;
                height: 100px; 
                margin-top: -100px; 
            }}
            
            .map-container-wrapper, .graph-container-wrapper {{
                display: flex;
                justify-content: space-between;
                gap: 10px; 
            }}  
            
            .map-container-wrapper > div, .map-container-wrapper > img, .graph-container-wrapper > div {{
                flex: 1;
                height: 400px;
                width: 48%;
            }}
            
            #map-container {{
                background-image: url('{{{{streetview}}}}');
                background-size: cover;
            }}
            
            #map-container-sat {{
                background-image: url('{{{{satelital}}}}');
                background-size: cover;
            }}
            
            #map {{
                width: 100%;
                height: 600px;
            }}
            
            .property-map {{
                width: 100%;
                height: 100%;
            }}
            
            .property-image {{
                width: 100%;
                height: 250px;
                overflow: hidden; 
                margin-bottom: 10px;
            }}
            
            .price-info {{
                font-family: 'Roboto', sans-serif;
                font-size: 20px;
                margin-bottom: 2px;
                text-align: center;
            }}
            
            .caracteristicas-info {{
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                margin-bottom: 2px;
                text-align: center;
            }}
            
            img {{
                max-width: 100%;
                width: 100%;
                height: 100%;
                object-fit: cover;
                margin-bottom: 10px; 
            }}
            
            .header-container {{
                width: 100%;
                background-color: #f2f2f2;
                padding: 20px 0;
            }}
            
            .header-title {{
                color: #A16CFF;
                text-align: center;
                font-size: 24px;
                margin: 0;
            }}
            
            body {{
                font-family: Arial, sans-serif;
                font-size: 10px;
            }}
            
            .table-wrapper {{
                width: 100%;
                margin: 0 auto;
            }}
            
            .fl-table {{
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 10px;
                width: 100%;
                border: 1px solid #ddd;
                text-align: left;
            }}
            
            .fl-table th, .fl-table td {{
                padding: 8px 10px;
            }}
            
            .fl-table th {{
                background-color: #f2f2f2;
            }}
            
            .fl-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            .mb-20 {{
                margin-bottom: 10px;
            }}
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
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
          {style}
        </head>
        <body>
          {header_html}
          <div class="map-container-wrapper">
            <img src="{streetview}" id="map-container" >
            <img src="{satelital}" id="map-container-sat">
            <img src="{static_map}" class="property-map">
          </div>
          {html}
        </body>
        </html>
        """
        html = BeautifulSoup(html, 'html.parser')
        html = html.prettify()
    return html

@st.cache_data(show_spinner=False)
def chipsfrombarmanpre(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.DataFrame()
    if isinstance(barmanpre, str) and not any([x for x in ['','*'] if x in barmanpre]):
        data = pd.read_sql_query(f"SELECT distinct(predirecc) as predirecc, prechip as chip FROM  bigdata.data_bogota_catastro WHERE barmanpre='{barmanpre}' AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
    engine.dispose()
    return data
    
@st.cache_data(show_spinner=False)
def getlogofromtoken(token):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = 'urbex' 
    logo     = 'https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png'
    if isinstance(token, str) and token!='':
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        datalogo = pd.read_sql_query(f"SELECT logo FROM {schema}.users WHERE token='{token}'" , engine)
        if not datalogo.empty:
            logot = datalogo['logo'].iloc[0]
            if isinstance(logot, str) and ('http' in logot.lower() or 'www' in logot.lower()):
                logo = logot
    engine.dispose()
    return logo

@st.cache_data(show_spinner=False)
def mergeprecuso(datacatastro=pd.DataFrame(),datavigencia=pd.DataFrame()):
    if not datacatastro.empty and not datavigencia.empty:
        datamerge    = datacatastro.drop_duplicates(subset=['prechip'],keep='first')
        datamerge.rename(columns={'prechip':'chip'},inplace=True)
        variables = [x for x in ['precuso','preaconst'] if x not in datavigencia]
        if isinstance(variables,list) and variables!=[]:
            variables = [x for x in variables if x in datamerge]
        if isinstance(variables,list) and variables!=[]:
            variables.append('chip') 
            datavigencia = datavigencia.merge(datamerge[variables],on='chip',how='left',validate='m:1')
    
    if not datavigencia.empty and all([x for x in ['precuso','preaconst'] if x in datavigencia]):
        datavigencia['avaluomt2'] = datavigencia['valorAutoavaluo']/datavigencia['preaconst']
        
    for i in ['precuso','preaconst','avaluomt2']:
        if i not in datavigencia: 
            datavigencia[i] = None

    return datavigencia
