import streamlit as st
import pandas as pd
import shapely.wkt as wkt
import plotly.express as px
import tempfile
import pdfcrowd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine 

from modulos._busqueda_avanzada_descripcion_lote import principal_table as html_descripcion_lote, shwolistings,gruoptransactions
from modulos._busqueda_avanzada_analisis_unidad import principal_table as html_unidad, linkPredial,buildname,buildphone,buildemail

from data.data_estudio_mercado_general import builddata as builddata_radio, data2geopandas, TransactionMarker
from data.getlatlng import getlatlng
from data.getuso_destino import usobydestino
from data.getdatabuilding import main as getdatabuilding
from data.getdatalotes import main as getdatalotes_radio
from data.circle_polygon import circle_polygon
from data.datadane import main as censodane
from data.data_listings import listingsBypolygon
from data.data_listings import buildingMarketValues

def main(chip=None,barmanpre=None):
    
    datadestinouso = usobydestino()
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
                options    = ['Todos'] + list(sorted(datadestinouso[datadestinouso['destino'].notnull()]['destino'].unique()))
                destino    = st.selectbox('Destino:',options=options)
                if 'todo' not in destino.lower() :
                    datadestinouso = datadestinouso[datadestinouso['destino']==destino]
                    precdestin     = list(datadestinouso['precdestin'].unique())
                
                
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
                    html = reportehtml(barmanpre=barmanpre,chip=chip,building=building,market=market,predio=predio,logo=logo,tipodestino=precdestin,tipouso=precuso,metros=metros,listingsA=listingsA,listingsNA=listingsNA)
                    
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

                    #with open(r"D:\...\reporte.html", "w", encoding="utf-8") as file:
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
def reportehtml(barmanpre=None,chip=None,building=False,market=False,predio=False,logo=None,tipodestino=None,tipouso=None,metros=500,listingsA=False,listingsNA=False):
    
    html = ""
    
    #-------------------------------------------------------------------------#
    # Reporte general:
    datacatastro,datausosuelo,datalote,datavigencia,datatransacciones = getdatabuilding(barmanpre)
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
    datacatastro_predio,datausosuelo_predio,datavigencia_predio = [pd.DataFrame()]*3 
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
                titulo = 'Análisis detallado'
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
        
    html_fig_predio = []
    if not datavigencia_predio.empty:
        format_bar = {"Avalúo Catastral":"valorAutoavaluo","Impuesto Predial":"valorImpuesto"}
        for key,value in format_bar.items():
            df = datavigencia_predio.groupby('vigencia')[value].max().reset_index()
            df = df.sort_values(by='vigencia',ascending=False)
            df.index = range(len(df))
            df = df.iloc[0:4,:]
            if not df.empty:
                df.columns  = ['year','value']
                df['year']   = pd.to_numeric(df['year'],errors='coerce')
                df           = df[(df['value']>0) & (df['year']>0)]
                df           = df.sort_values(by='year',ascending=True)
                df.index     = range(len(df))
                df['year']   = df['year'].astype(int).astype(str)
                fig          = px.bar(df, x="year", y="value", text="value", title=key)
                fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_xaxes(tickmode='linear', dtick=1)
                fig.update_layout(title_x=0.5,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                    'legend':dict(bgcolor='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                html_fig_paso = fig.to_html(config={'displayModeBar': False})
                try:
                    soup = BeautifulSoup(html_fig_paso, 'html.parser')
                    soup = soup.find('body')
                    soup = str(soup.prettify())
                    soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                    html_fig_predio.append(soup)
                except: pass
    
    if isinstance(html_fig_predio, list):
        for graficas in html_fig_predio:
            html += f""" 
            <div class="graph-container">
                {graficas}
            </div>
            """

    #-------------------------------------------------------------------------#
    # Estudio de mercado
    html_fig_market = []
    if market:
        metros = metros if isinstance(metros, int) else 500
        if (isinstance(latitud, float) or isinstance(latitud, int)) or (isinstance(longitud, float) or isinstance(longitud, int)):
            polygon  = str(circle_polygon(metros,latitud,longitud))
            inputvar =  {
                'polygon':polygon,
                'latitud':latitud,
                'longitud':longitud,
                }
            datalotes_radio                            = getdatalotes_radio(inputvar)
            datacatastro_radio,datatransacciones_radio = builddata_radio(polygon=polygon)
            datalistingsactivos_radio,datalistingshistoricos_radio = listingsBypolygon(str(polygon),precuso=None)
            datacensodane_radio = censodane(str(polygon))
            
            geojson   = data2geopandas(datalotes_radio)
            geopoints = TransactionMarker(datatransacciones_radio.copy(),datacatastro_radio.copy(),datalotes_radio.copy())
            titulo = 'Estudio de mercado'
            html += f"""<div class="header-container"><h1 class="header-title">{titulo}</h1></div>"""

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
            
            </script>
            """
            if isinstance(tipodestino, list):
                datacatastro_radio      = datacatastro_radio[datacatastro_radio['precdestin'].isin(tipodestino)]
                datalotes_radio         = datalotes_radio[datalotes_radio['barmanpre'].isin(datacatastro_radio['barmanpre'])]
                datatransacciones_radio = datatransacciones_radio[datatransacciones_radio['prechip'].isin(datatransacciones_radio['prechip'])]

            if isinstance(tipouso, list):
                datacatastro_radio      = datacatastro_radio[datacatastro_radio['precuso'].isin(tipouso)]
                datalotes_radio         = datalotes_radio[datalotes_radio['barmanpre'].isin(datacatastro_radio['barmanpre'])]
                datatransacciones_radio = datatransacciones_radio[datatransacciones_radio['prechip'].isin(datacatastro_radio['prechip'])]
                
            tiposelected = 'destino'
            titulo       = 'Destino'
            
                #---------------------------------------------------------------------#
                # Transacciones
            if not datatransacciones_radio.empty:
                df = datatransacciones_radio.groupby('fecha_documento_publico').agg({'valormt2_transacciones':['count','median']}).reset_index()
                df.columns = ['fecha','count','value']
                df.index = range(len(df))
                if not df.empty:
                    fig = px.bar(df, x="fecha", y="count", text="count", title='Número de transacciones')
                    fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                    fig.update_xaxes(tickmode='linear', dtick=1)
                    fig.update_layout(title_x=0.5,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                        'legend':dict(bgcolor='black'),
                    })    
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass
                
                    fig = px.bar(df, x="fecha", y="value", text="value", title='Valor promedio de las transacciones por m²')
                    fig.update_traces(texttemplate='$%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                    fig.update_layout(title_x=0.5,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                    })
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass
                        
                #---------------------------------------------------------------------#
                # Destino<>uso del suelo + Transacciones
            if not datacatastro_radio.empty:
                df = datacatastro_radio.groupby(tiposelected)['prechip'].count().reset_index()
                df.columns = ['variable','value']
                df.index = range(len(df))
                if not df.empty and len(df)>1:
                    graphtit = f'Número de matrículas por {titulo}'
                    # color_discrete_sequence=px.colors.sequential.RdBu[::-1]
                    fig      = px.pie(df,  values="value", names="variable", title=graphtit,color_discrete_sequence=px.colors.sequential.Purples[::-1],height=500)
                    fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                    })
                    fig.update_traces(textinfo='percent+label', textfont_color='white',textposition='inside',)
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_layout(legend=dict(font=dict(color='black')))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass
                        
            if not datatransacciones_radio.empty:
                df         = datatransacciones_radio.groupby(tiposelected).agg({'valormt2_transacciones':['median']}).reset_index()
                df.columns = ['variable','value']
                df         = df[(df['value']>0) & (df['value']<100000000)]
                df         = df.sort_values(by='value',ascending=True)
                df.index   = range(len(df))
                if not df.empty and len(df)>1:
                    graphtit = f'Transacciones por {titulo}'
                    fig = px.bar(df, x="value", y="variable", text="value", title=graphtit,orientation='h')
                    fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                    fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                    })
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass
                
                #---------------------------------------------------------------------#
                # Avaluo catastral y predial
            if not datacatastro_radio.empty:
                df = datacatastro_radio.groupby(tiposelected).agg({'avaluomt2':['median']}).reset_index()
                df.columns = ['variable','value']
                df         = df[(df['value']>0) & (df['value']<100000000)]
                df         = df.sort_values(by='value',ascending=True)
                df.index   = range(len(df))
                if not df.empty:
                    df  = df[df['value'].notnull()]
                    fig = px.bar(df, x="value", y="variable", text="value", title='Avalúo catastral promedio por m²',orientation='h')
                    fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                    fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                    })    
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass
                
                df         = datacatastro_radio.groupby(tiposelected).agg({'predialmt2':['median']}).reset_index()
                df.columns = ['variable','value']
                df         = df[(df['value']>0) & (df['value']<500000)]
                df         = df.sort_values(by='value',ascending=True)
                df.index   = range(len(df))
                if not df.empty:
                    df  = df[df['value'].notnull()]
                    fig = px.bar(df, x="value", y="variable", text="value", title='Predial promedio por m²',orientation='h')
                    fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                    fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                        'title_font':dict(color='black'),
                    })    
                    fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                        html_fig_market.append(soup)
                    except: pass

                #---------------------------------------------------------------------#
                # Tipologia de los inmuebles
            df  = pd.DataFrame()
            if not datacatastro_radio.empty:
                formato = [{'variable':'preaconst','titulo':'Diferenciación por Área Privada'},
                           {'variable':'prevetustz','titulo':'Diferenciación por Antigüedad'},]
                for iiter in formato:
                    variable = iiter['variable']
                    titulo   = iiter['titulo']
                    df         = datacatastro_radio.copy()
                    df         = df[df[variable]>0]
                    
                    if not df.empty:
                        q1         = df.groupby(tiposelected)[variable].quantile(0.25).reset_index()
                        q1.columns = [tiposelected,'q1']
                        q3         = df.groupby(tiposelected)[variable].quantile(0.75).reset_index()
                        q3.columns = [tiposelected,'q3']
                        
                        # Remover outliers
                        w         = q1.merge(q3,on=tiposelected,how='outer')
                        w['iqr']  = w['q3']-w['q1']
                        w['linf'] = w['q1'] - 1.5*w['iqr']
                        w['lsup'] = w['q3'] + 1.5*w['iqr']
                        df        = df.merge(w[[tiposelected,'linf','lsup']],on=tiposelected,how='left',validate='m:1')
                        df        = df[(df[variable]>=df['linf']) & (df[variable]<=df['lsup'])]
                        
                        w         = df.groupby(tiposelected)['prechip'].count().reset_index() 
                        w.columns = [tiposelected,'count']
                        df        = df.merge(w,on=tiposelected,how='left',validate='m:1')
                        df        = df[df['count']>2]
                
                    if not df.empty:
                        fig = px.box(df,x=tiposelected,y=variable,title=titulo,color_discrete_sequence=['#68c8ed'])
                        fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                        fig.update_layout({
                            'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                            'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                            'title_font':dict(color='black'),
                        })    
                        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                        fig.update_traces(boxpoints=False)
                        html_fig_paso = fig.to_html(config={'displayModeBar': False})
                        try:
                            soup = BeautifulSoup(html_fig_paso, 'html.parser')
                            soup = soup.find('body')
                            soup = str(soup.prettify())
                            soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                            html_fig_market.append(soup)
                        except: pass
                    
                #---------------------------------------------------------------------#
                # Listings
            if not datalistingsactivos_radio.empty:
                df = datalistingsactivos_radio.groupby(['tiponegocio','tipoinmueble']).agg({'valormt2':['count','median']}).reset_index()
                df.columns = ['tiponegocio','tipoinmueble','count','value']
                df.index = range(len(df))
                for tiponegocio in ['Venta','Arriendo']:
                    dfiter = df[df['tiponegocio']==tiponegocio]
                    dfiter = dfiter.sort_values(by='value',ascending=True)
                    if not dfiter.empty:
                        fig = px.bar(dfiter, x="value", y="tipoinmueble", text="value", title=f'Valor de {tiponegocio.lower()} por m² (listings activos)',orientation='h')
                        fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                        fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                        fig.update_layout({
                            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                            'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                            'title_font':dict(color='black'),
                        })    
                        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                        html_fig_paso = fig.to_html(config={'displayModeBar': False})
                        try:
                            soup = BeautifulSoup(html_fig_paso, 'html.parser')
                            soup = soup.find('body')
                            soup = str(soup.prettify())
                            soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                            html_fig_market.append(soup)
                        except: pass

                #---------------------------------------------------------------------#
                # Analisis demografico
            if not datacensodane_radio.empty:
                variables = [x for x in ['Total personas','Total viviendas','Hogares','Hombres','Mujeres'] if x in datacensodane_radio]
                df = datacensodane_radio[variables].copy()
                df = df.T.reset_index()
                df.columns = ['name','value']
                df.index = range(len(df))
                fig      = px.bar(df, x="name", y="value", text="value", title="Análisis Demográfico (censo del DANE)")
                fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_xaxes(tickmode='linear', dtick=1)
                fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False)
                html_fig_paso = fig.to_html(config={'displayModeBar': False})
                try:
                    soup = BeautifulSoup(html_fig_paso, 'html.parser')
                    soup = soup.find('body')
                    soup = str(soup.prettify())
                    soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                    html_fig_market.append(soup)
                except: pass
            
                variables = [x for x in ['0 a 9 años', '10 a 19 años', '20 a 29 años', '30 a 39 años', '40 a 49 años', '50 a 59 años', '60 a 69 años', '70 a 79 años', '80 años o más'] if x in datacensodane_radio]
                df = datacensodane_radio[variables].copy()
                df = df.T.reset_index()
                df.columns = ['name','value']
                df.index = range(len(df))
                fig      = px.bar(df, x="name", y="value", text="value", title="Edades (censo del DANE)")
                fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_xaxes(tickmode='linear', dtick=1)
                fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                html_fig_paso = fig.to_html(config={'displayModeBar': False})
                try:
                    soup = BeautifulSoup(html_fig_paso, 'html.parser')
                    soup = soup.find('body')
                    soup = str(soup.prettify())
                    soup = soup.replace('<body>', '<div style="margin-bottom: 20px;">').replace('</body>', '</div>')
                    html_fig_market.append(soup)
                except: pass

    if isinstance(html_fig_market, list):
        for graficas in html_fig_market:
            html += f""" 
            <div class="graph-container">
                {graficas}
            </div>
            """
            
    datalistings = pd.DataFrame()
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
    
    if html!='':
        style = f"""
        <style>
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