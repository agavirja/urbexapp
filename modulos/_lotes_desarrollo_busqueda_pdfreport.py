import streamlit as st
import pandas as pd
import tempfile
import pdfcrowd
import geojson as geojsonlib
import shapely.wkt as wkt
from shapely.geometry import mapping
from bs4 import BeautifulSoup
from sqlalchemy import create_engine 
from streamlit_js_eval import streamlit_js_eval

from modulos._busqueda_avanzada_descripcion_lote import gruoptransactions,analytics_transacciones,shwolistings
from modulos._lotes_descripcion_combinacionlote import data2geopandas as data2geopandascombinacion,principal_table as html_descripcion_general
from modulos._propietarios import gethtml as gethtmlpropietarios

from data.getdatabuilding import main as getdatabuilding
from data.circle_polygon import circle_polygon
from data.data_listings import buildingMarketValues
from data.datacomplemento import main as datacomplemento
from data.getdatalotescombinacion import getdatacombinacionlotes,mergedatabybarmanpre
from data.getdata_market_analysis import main as getdata_market_analysis
from data.reporte_analisis_mercado import reporteHtml as reporteHtml_estudio_mercado, data2geopandas,TransactionMarker
from data.getuso_destino import usosuelo_class

def main(code=None,latitud=None,longitud=None,precuso=None):
    
    screensize = 1920
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass

    datadestinouso     = usosuelo_class()
    precdestin,precuso = [None]*2
    metros             = 500
    market,building,predio,logo = [None]*4
    
    col1,col2,col3 = st.columns([0.25,0.5,0.25])
    with col2:
        with st.container(border=True):
            st.subheader('¿Qué módulos quieres incluir en el reporte en PDF?')
            
            #-----------------------------------------------------------------#
            building = st.toggle("Combinación de lotes",value=True)

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
                    precuso        = list(datadestinouso['precuso'].unique())

                metros = st.selectbox('Metros a la redonda',options=[100,200,300,400,500],index=4)
                st.write('')
                st.write('')
                
            #-----------------------------------------------------------------#
            listingsA  = st.toggle("Listings activos",value=True)
            listingsNA = st.toggle("Listings históricos (NO activos)",value=False)
            
            #-----------------------------------------------------------------#
            logo = st.toggle("Incluir el logo de la empresa",value=True)
  
            if st.button('Generar PDF'):
                with st.spinner('Generando reporte, por favor espera un momento'):
                    html = reportehtml(code=code,building=building,market=market,logo=logo,tipodestino=precdestin,tipouso=precuso,metros=metros,listingsA=listingsA,listingsNA=listingsNA,latitud=latitud,longitud=longitud,mapwidth=mapwidth,mapheight=200)
                               
                    API_KEY      = '1a7a2a64fcce84bcb9e1dbb0a7363b75'
                    pdfcrowduser = 'agavirja3'
                    wd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf")       
                    
                    if 'token' not in st.session_state: 
                        st.session_state.token = None
                        
                    logo = getlogofromtoken(st.session_state.token)
                    header_html = f"""
                    <div style="text-align: right;">
                        <img src="{logo}" style="width: 100px; height: auto;">
                    </div>
                    """
                    
                    client = pdfcrowd.HtmlToPdfClient(pdfcrowduser,API_KEY)
                    client.setHeaderHtml(header_html)
                    client.setPageHeight('-1')
                    client.convertStringToFile(html, pdf_temp_path)

                    with open(pdf_temp_path, "rb") as pdf_file:
                        PDFbyte = pdf_file.read()

                    #with open(r"D:\...\reportelote.html", "w", encoding="utf-8") as file:
                    #    file.write(html)
                        
                    st.download_button(label="Descargar PDF",
                                        data=PDFbyte,
                                        file_name="reportePDF.pdf",
                                        mime='application/octet-stream')

def style_function_geojson(feature):
    return {
        'fillColor': '#0000ff',
        'color': '#0000ff',
        'weight': 2,
        'opacity': 1,
        'fillOpacity': 0.6,
    }

@st.cache_data(show_spinner=False)
def reportehtml(code=None,building=False,market=False,logo=None,tipodestino=None,tipouso=None,metros=500,listingsA=False,listingsNA=False,latitud=None,longitud=None,mapwidth=600,mapheight=200):
    
    #datapredios,datalotescatastro,datalong,datausosuelo = getdatacombinacionlotes(code)
    datapredios,datalotescatastro,datausosuelo  = getdatacombinacionlotes(code)
    
    html = ""
    lote = ""
    if not datalotescatastro.empty:
        geojson   = data2geopandascombinacion(datalotescatastro)

        v = """
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);
        """
        lote = f"""
        <div id="map_1" style="height: 420px;" class="property-map"></div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonData = {geojson};
            var map = L.map('map_1').setView([{latitud}, {longitud}], 19);
            {v}
    
            function style(feature) {{
                return {{
                    color: feature.properties.color,
                    weight: 3,
                    dashArray: '6, 6'
                }};
            }}
            L.geoJSON(geojsonData, {{
                style: style
            }}).addTo(map);

        </script>
        """
            
    barmanpre  = None
    precuso    = None
    direccion  = None
    polygonstr = None
    
    datavigencia,datatransacciones,datadirecciones,datactl,_du,_dl = [pd.DataFrame()]*6
    input_transacciones = {}
    if isinstance(code, str) and code!='':
        barmanpre = code.split('|')
        datadirecciones,_du,_dl,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
        datalotescatastro = mergedatabybarmanpre(datalotescatastro.copy(),_du.copy(),['prenbarrio','formato_direccion','construcciones','prevetustzmin'])
        
    if not datatransacciones.empty and not datavigencia.empty:
        input_transacciones = analytics_transacciones(datatransacciones,datavigencia)

    if not _du.empty and 'formato_direccion' in _du:
        direccion = list(_du['formato_direccion'].unique())

    if not datapredios.empty:
        polygonstr = datapredios['wkt'].iloc[0]
  
    if not datausosuelo.empty and 'precuso' in datausosuelo: 
        precuso = list(datausosuelo['precuso'].unique())
        
    input_complemento = datacomplemento(barmanpre=code,latitud=latitud,longitud=longitud,direccion=direccion,polygon=polygonstr,precuso=precuso)
    try:    input_complemento['direcciones'] = ' | '.join(direccion)
    except: input_complemento['direcciones'] = ''

    if building:
        
        html_paso,conteo = html_descripcion_general(datapredios=datapredios,datausosuelo=datausosuelo,input_complemento=input_complemento,input_transacciones=input_transacciones)
        html += html_paso
        
        if not datalotescatastro.empty and len(datalotescatastro)>1:       
            
            html_paso = ""
            for _,items in datalotescatastro.iterrows():
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
                try:    pisos = f"{int(items['pisos'])}"
                except: pisos = ""
                try:    sotanos = f"{int(items['sotanos'])}"
                except: sotanos = ""
                try:    construcciones = f"{int(items['construcciones'])}"
                except: construcciones = ""
                try:    antiguedadmin = f"{int(items['prevetustzmin'])}"
                except: antiguedadmin = ""                
                try:    link = f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}"
                except: link = ""
                html_paso += f"""
                <tr>
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{link}" target="_blank">
                       <img src="https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png" alt="link" style="width: 16px; height: 16px;">
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
            if html_paso!="":
                titulo = 'Lista de lotes'
                html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
                html += f"""
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
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
                        </table>
                    </div>
                </div>
                """

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
    # Propietarios
    #-------------------------------------------------------------------------#
    if barmanpre is not None:
        
        _,datavigencia_predio = gethtmlpropietarios(chip=None,barmanpre=barmanpre,vartype=None,infilter=False,descargar=False)
        if not datavigencia_predio.empty:
            html_paso    = ""
            for _,items in datavigencia_predio.iterrows():
                try:    
                    link = items['link'] if 'link' in items and isinstance(items['link'], str) else ""
                    link = f"""
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{link}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    """
                except: link = "<td></td>"
                try:    vigencia = f"<td>{items['vigencia']}</td>" if 'vigencia' in items and (isinstance(items['vigencia'], int) or isinstance(items['vigencia'], float)) else "<td></td>"
                except: vigencia = "<td></td>"
                try:    direccion = f"<td>{items['predirecc']}</td>" if 'predirecc' in items and isinstance(items['predirecc'], str) else "<td></td>"
                except: direccion = "<td></td>"                
                try:    avaluo = f"<td>${items['valorAutoavaluo']:,.0f}</td>" if 'valorAutoavaluo' in items and (isinstance(items['valorAutoavaluo'], int) or isinstance(items['valorAutoavaluo'], float)) else "<td></td>"
                except: avaluo = "<td></td>"
                try:    predial = f"<td>${items['valorImpuesto']:,.0f}</td>" if 'valorImpuesto' in items and (isinstance(items['valorImpuesto'], int) or isinstance(items['valorImpuesto'], float)) else "<td></td>"
                except: predial = "<td></td>"
                try:    areaconstruida = f"<td>{items['preaconst']}</td>" if 'preaconst' in items and (isinstance(items['preaconst'], int) or isinstance(items['preaconst'], float)) else "<td></td>"
                except: areaconstruida = "<td></td>"
                try:    copropiedad = f"<td>{int(items['copropiedad'])}</td>" if 'copropiedad' in items and (isinstance(items['copropiedad'], int) or isinstance(items['copropiedad'], float)) else "<td></td>"
                except: copropiedad = "<td></td>"
                try:    tipopropietario = f"<td>{items['tipoPropietario']}</td>" if 'tipoPropietario' in items and isinstance(items['tipoPropietario'], str) else "<td></td>"
                except: tipopropietario = "<td></td>"
                try:    tipodocumento = f"<td>{items['tipoDocumento']}</td>" if 'tipoDocumento' in items and isinstance(items['tipoDocumento'], str) else "<td></td>"
                except: tipodocumento = "<td></td>"
                try:    name = f"<td>{items['name']}</td>" if 'name' in items and isinstance(items['name'], str) else "<td></td>"
                except: name = "<td></td>"
                try:    phone = f"<td>{items['phone']}</td>" if 'phone' in items and isinstance(items['phone'], str) else "<td></td>"
                except: phone = "<td></td>"
                try:    email = f"<td>{items['email']}</td>" if 'email' in items and isinstance(items['email'], str) else "<td></td>"
                except: email = "<td></td>"
                
                html_paso += f"""
                <tr>
                    {vigencia}
                    {direccion}
                    {avaluo}
                    {predial}
                    {copropiedad}
                    {areaconstruida}
                    {tipopropietario}
                    {tipodocumento}
                    {name}
                    {phone}
                    {email}
                </tr>
                """
            titulo = 'Propietarios'
            html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""
            html += f"""
            <div class="table-wrapper table-background">
                <div class="table-scroll">
                    <table class="fl-table">
                        <thead>
                            <tr>
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
    datalistings = pd.DataFrame()
    direccion    = None
    if not _du.empty and 'formato_direccion' in _du:
        direccion = list(_du['formato_direccion'].unique())
    if listingsA or listingsNA:
        if direccion is not None:
            datalistings = buildingMarketValues(direccion,precuso=None,mpioccdgo=None)
        
    if not datalistings.empty and listingsA:
        datapaso = datalistings[datalistings['tipo']=='activos']
        if not datapaso.empty:
            datapaso = datapaso.sort_values(by='tiponegocio',ascending=True)
            html_listings_paso = shwolistings(datapaso)
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
            html_listings_paso = shwolistings(datapaso)
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
    YOUR_API_KEY = "AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw"
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
    
    #if html!='':
    style = f"""
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
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
            }}
        
            .css-table td {{
                text-align: left;
                padding: 0;
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
            }}
        
            .css-table td[colspan="labelsectionborder"] {{
                text-align: left;
                border: none;
                border-bottom: 2px solid blue;
                margin-top: 20px;
                display: block;
                padding: 0;
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
                gap: 10px; /* Separación pequeña entre elementos */
            }}  
        
            .map-container-wrapper > div, .map-container-wrapper > img, .graph-container-wrapper > div {{
                flex: 1;
                height: 400px;
                width: 48%;
            }}
        
            #map-container {{
                background-image: url('{{streetview}}');
                background-size: cover;
            }}
        
            #map-container-sat {{
                background-image: url('{{satelital}}');
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
                background-color: #f2f2f2; /* Gris muy claro */
                padding: 20px 0; /* Espaciado arriba y abajo */
            }}
        
            .header-title {{
                color: #A16CFF; /* Azul claro */
                text-align: center;
                font-size: 24px; /* Tamaño de fuente del título */
                margin: 0;
            }}
        
            body {{
                font-family: Arial, sans-serif;
                font-size: 10px; /* Reducir el tamaño de la fuente */
            }}
        
            .table-wrapper {{
                width: 100%;
                margin: 0 auto;
            }}
        
            .fl-table {{
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 10px; /* Reducir el tamaño de la fuente */
                width: 100%;
                border: 1px solid #ddd;
                text-align: left;
            }}
        
            .fl-table th, .fl-table td {{
                padding: 8px 10px; /* Reducir el padding */
            }}
        
            .fl-table th {{
                background-color: #f2f2f2;
            }}
        
            .fl-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            .map-container-wrapper, .graph-container-wrapper {{
                display: flex;
                justify-content: space-between;
                gap: 10px; /* Separación pequeña entre elementos */
            }}  
            .map-container-wrapper > div, .map-container-wrapper > img, .graph-container-wrapper > div {{
                flex: 1;
                height: 400px;
                width: 48%;
            }}
            #map-container {{
                background-image: url('{streetview}');
                background-size: cover;
            }}
            #map-container-sat {{
                background-image: url('{satelital}');
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
            .graph-container {{
                margin-bottom: 20px;
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
      <div class="map-container-wrapper">
          <div id="map-container"></div>
          <div id="map-container-sat"></div>
          {lote}
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
