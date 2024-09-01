import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import shapely.wkt as wkt
import plotly.express as px
import tempfile
import pdfcrowd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_folium import st_folium
from shapely.geometry import Point
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from data.getdata_market_analysis import main as getdata_market_analysis
from data.getuso_destino import usosuelo_class
from data.circle_polygon import circle_polygon

from display.stylefunctions  import style_function_geojson

def main(polygon=None,precuso=None,barmanpreref=None,latitud=None,longitud=None,maxmetros=500,tipo=None):

    screensize = 1920
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass

    # Poner DANE
    # poner graficas cuandouuso del suelo hay varios
    # poner graficas de mercad oe habitaciones, banos, etc
    
    with st.spinner('Generando reporte'):
        
        if polygon is None and isinstance(tipo,str) and tipo=='radio' and (isinstance(latitud,float) or isinstance(latitud,int)) and (isinstance(longitud,float) or isinstance(longitud,int)):
            polygon = circle_polygon(maxmetros,latitud,longitud)
            
        #---------------------------------------------------------------------#
        # Datos
        datapredios,datacatastro,datavigencia,datatransacciones,datamarket = getdata_market_analysis(polygon=polygon,precuso=precuso)
        datausosuelo = usosuelo_class()

        # Remover tipo de inmuebles del analisis de mercado: Ej. parqueaderos, depositos, ...
        if isinstance(precuso,list) and precuso!=[]:
            listremove   = ['Depósitos','Parqueadero']
            listaprecuso = list(datausosuelo[datausosuelo['clasificacion'].isin(listremove)]['precuso'].unique())
            precuso      = [item for item in precuso if item not in listaprecuso]
            
        #---------------------------------------------------------------------#
        # Filtros del dashboard
        colpdf1,colpdf2 = st.columns([0.75,0.25])
        cols1,cols2,cols3,cols4 = st.columns(4)
        colsn1,colsn2 = st.columns(2)

        with cols1:
            areamin = st.number_input('Área mínima',value=0,min_value=0)
        with cols2:
            areamax = st.number_input('Área máxima',value=0,min_value=0)
        with cols3:
            antiguedadmin = st.number_input('Antigüedad desde (años)',value=0,min_value=0)
        with cols4:
            antiguedadmax = st.number_input('Antigüedad hasta (años)',value=100,min_value=0)
        
        precusoselect = []
        if isinstance(precuso,list) and precuso!=[]:
            with colsn1:
                idd = datausosuelo['precuso'].isin(precuso)
                if sum(idd)>0:
                    options       = list(datausosuelo[idd]['usosuelo'].unique())
                    precusoselect = st.multiselect('Uso del suelo',options=options)       
        else:
            with colsn1:
                options       = ['Todos'] + list(sorted(datausosuelo[datausosuelo['clasificacion'].notnull()]['clasificacion'].unique()))
                clasificacion = st.selectbox('Tipo:',options=options)
                if 'todo' not in clasificacion.lower() :
                    datausosuelo = datausosuelo[datausosuelo['clasificacion']==clasificacion]

            with colsn2:
                options     = ['Todos'] + list(sorted(datausosuelo[datausosuelo['usosuelo'].notnull()]['usosuelo'].unique()))
                usoselected = st.multiselect('Uso del suelo',options=options)
                if not any([x for x in usoselected if 'todo' in x.lower()]) and usoselected!=[]:
                    datausosuelo  = datausosuelo[datausosuelo['usosuelo'].isin(usoselected)]
                    precusoselect = list(datausosuelo['usosuelo'].unique())
                else: 
                    precusoselect = list(datausosuelo['usosuelo'].unique())
                     
        if isinstance(precusoselect,list) and precusoselect==[] and isinstance(precuso,list) and precuso!=[]:
            precusoselect = list(datausosuelo[datausosuelo['precuso'].isin(precuso)]['usosuelo'].unique())
        
        filtro = False
        if areamin>0:
            datacatastro = datacatastro[datacatastro['preaconst']>=areamin]
            datamarket   = datamarket[datamarket['areaconstruida']>=areamin]
            filtro       = True
        if areamax>0:
            datacatastro = datacatastro[datacatastro['preaconst']<=areamax]
            datamarket   = datamarket[datamarket['areaconstruida']<=areamax]
            filtro       = True
        if antiguedadmin>0:
            antiguedadmin = datetime.now().year-antiguedadmin
            datacatastro  = datacatastro[datacatastro['prevetustz']<=antiguedadmin]
            filtro        = True
        if antiguedadmax>0:
            antiguedadmax = datetime.now().year-antiguedadmax
            datacatastro  = datacatastro[datacatastro['prevetustz']>=antiguedadmax]
            filtro        = True
        if isinstance(precusoselect,list) and precusoselect!=[] and not any([x for x in precusoselect if 'todo' in x.lower()]):
            precusofiltro = list(datausosuelo[datausosuelo['usosuelo'].isin(precusoselect)]['precuso'].unique())
            datacatastro  = datacatastro[datacatastro['precuso'].isin(precusofiltro)]
            datapredios   = datapredios[datapredios['precuso'].isin(precusofiltro)]
            filtro        = True
            
        if filtro:
            if not datapredios.empty and not datacatastro.empty:
                datapredios = datapredios[datapredios['barmanpre'].isin(datacatastro['barmanpre'])]
            if not datavigencia.empty and not datacatastro.empty:
                datavigencia = datavigencia[datavigencia['chip'].isin(datacatastro['prechip'])]
            if not datatransacciones.empty and not datacatastro.empty:
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

        #---------------------------------------------------------------------#
        # Filtro de radio
        if not datapredios.empty and isinstance(tipo,str) and 'radio' in tipo:
            if isinstance(precuso,list) and precuso!=[]:
                with colsn2:
                    metros = st.slider("Metros a la redonda",100,maxmetros,value=maxmetros,step=100) 
            else:
                with colsn1:
                    metros = st.slider("Metros a la redonda",100,maxmetros,value=maxmetros,step=100) 
            
            if metros<maxmetros:
                polygon,datapredios,datacatastro,datavigencia,datatransacciones = filtro_radio(metros,polygon,datapredios,datacatastro,datavigencia,datatransacciones)

        #---------------------------------------------------------------------#
        # Mapa de referencia
        #---------------------------------------------------------------------#
        col1,col2 = st.columns([0.3,0.6])
        if not datapredios.empty:
            
            latitud,longitud = 4.688002,-74.054444
            if 'latitud' in datapredios and 'longitud' in datapredios:
                latitud  = datapredios['latitud'].mean()
                longitud = datapredios['longitud'].mean()
            
            m = folium.Map(location=[latitud, longitud], zoom_start=16,tiles="cartodbpositron")
            folium.GeoJson(wkt.loads(polygon), style_function=style_function_color).add_to(m)

            if not datapredios.empty:
                dataoutput = datapredios.sort_values(by='transacciones',ascending=False).drop_duplicates(subset='barmanpre',keep='first')
                geojson    = data2geopandas(dataoutput,barmanpreref=barmanpreref)
                popup      = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
            if not datapredios.empty and not datatransacciones.empty:
                geopoints = TransactionMarker(datapredios.copy(),datatransacciones.copy())
                marker    = folium.Circle(radius=1)
                folium.GeoJson(geopoints,style_function=style_function_geojson,marker=marker).add_to(m)
                
            with col1:
                st_map = st_folium(m,width=int(mapwidth*0.3),height=900)
        
        #---------------------------------------------------------------------#
        # Reporte
        #---------------------------------------------------------------------#
        with col2:
            html = reporteHtml(datapredios=datapredios,datacatastro=datacatastro,datatransacciones=datatransacciones,datavigencia=datavigencia,datamarket=datamarket,mapwidth=mapwidth/0.7,mapheight=200)
            st.components.v1.html(html, height=900)

        with colpdf2:
            if st.button('Generar PDF'):
                with st.spinner('Generando reporte, por favor espera un momento'):
    
                    API_KEY      = 'e03f4c6097c664281d195cb71357a2a4'
                    pdfcrowduser = 'urbexventas'
                    wd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf")       
                    
                    if 'token' not in st.session_state: 
                        st.session_state.token = None
                        
                    header_html = """
                    <div style="text-align: right;">
                        <img src="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png" style="width: 100px; height: auto;">
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

@st.cache_data(show_spinner=False)
def data2geopandas(data,barmanpreref=None):
    
    urlexport = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
        
    lista = []
    if barmanpreref is not None and isinstance(barmanpreref,str) and barmanpreref!="":
        lista = barmanpreref.split('|')
    elif isinstance(barmanpreref,list):
        lista = barmanpreref.copy()
        
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        idd              = data['barmanpre'].isin(lista)
        if sum(idd)>0:
            data.loc[idd,'color'] ='#003F2D'
            
        for idd,items in data.iterrows():

            urllink     = ""
            barmanpre   = items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"

            popupinfo = ""
            try:    popupinfo += f"""<b> Dirección:</b> {items['formato_direccion']}<br>"""
            except: pass
            try:    popupinfo += f"""<b> Copropiedad:</b> {items['nombre_conjunto']}<br> """ if isinstance(items['nombre_conjunto'],str) else ""
            except: pass     
            try:    popupinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """
            except: pass
            try:    popupinfo += f"""<b> Total de matriculas:</b> {int(items['predios_precuso'])}<br>"""
            except: pass
            try:    popupinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Pisos:</b> {int(items['connpisos'])}<br> """
            except: pass
            try:    popupinfo += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>"""
            except: pass            
            try:    popupinfo += f"""<b> Transacciones:</b> {int(items['transacciones'])}<br> """ if (isinstance(items['transacciones'],float) or isinstance(items['transacciones'],int)) else ""
            except: pass   
            try:    popupinfo += f"""<b> Transaccion promedio m²:</b> ${items['valormt2_transacciones']:,.0f}<br> """ if (isinstance(items['valormt2_transacciones'],float) or isinstance(items['valormt2_transacciones'],int)) else ""
            except: pass     
            try:    popupinfo += f"""<b> Propietarios:</b> {int(items['propietarios'])}<br> """ if (isinstance(items['propietarios'],float) or isinstance(items['propietarios'],int)) else ""
            except: pass 

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
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
def TransactionMarker(datapredios,datatransacciones):
    geojson = pd.DataFrame().to_json()    
    if not datapredios.empty and not datatransacciones.empty and 'barmanpre' in datatransacciones and 'barmanpre' in datapredios:
        datapaso = datapredios.copy()
        datapaso = datapaso[datapaso['barmanpre'].isin(datatransacciones['barmanpre'])]
        datapaso = datapaso[(datapaso['latitud'].notnull()) & (datapaso['longitud'].notnull())]
        if not datapaso.empty:
            datapaso['geometry'] = datapaso.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
            datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
            datapaso             = datapaso[['geometry']]
            datapaso['color']    = 'blue'
            geojson                 = datapaso.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def filtro_radio(metros,polygon,datapredios,datacatastro,datavigencia,datatransacciones):
    if not datapredios.empty and 'wkt' in datapredios:
        pol          = wkt.loads(polygon)
        latitud      = pol.centroid.y
        longitud     = pol.centroid.x
        polygonradio = circle_polygon(metros,latitud,longitud)
        
        datapaso             = datapredios.copy()
        datapaso             = datapaso[datapaso['wkt'].notnull()]
        datapaso['geometry'] = gpd.GeoSeries.from_wkt(datapaso['wkt'])
        datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
        idd                  = datapaso['geometry'].apply(lambda x: polygonradio.contains(x)) # polygonradio.touches(x)
        datapaso             = datapaso[idd]
        datapredios          = datapredios[datapredios['barmanpre'].isin(datapaso['barmanpre'])]
        datacatastro         = datacatastro[datacatastro['barmanpre'].isin(datapaso['barmanpre'])]
        datavigencia         = datavigencia[datavigencia['chip'].isin(datacatastro['prechip'])]
        datatransacciones    = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]
        polygonradio         = str(polygonradio)
        
    return polygonradio,datapredios,datacatastro,datavigencia,datatransacciones

@st.cache_data(show_spinner=False)
def reporteHtml(datapredios=pd.DataFrame(),datacatastro=pd.DataFrame(),datatransacciones=pd.DataFrame(),datavigencia=pd.DataFrame(),datamarket=pd.DataFrame(),mapwidth=600,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Header
    html_header = ""
    if not datapredios.empty:
        formato = [{'texto':'Edificios','value':int(len(datapredios['barmanpre'].unique()))},
                   {'texto':'Matrículas','value':int(datapredios['predios_precuso'].sum()) if 'predios_precuso' in datapredios else None}]
        html_paso = ""
        for i in formato:
            if i['value'] is not None:
                value      = '{:,.0f}'.format(i['value'])
                html_paso += f"""
                <div class="col-6 col-md-6 mb-3">
                    <div class="card card-stats card-round">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="numbers">
                                        <h4 class="card-title">{value}</h4>
                                        <p class="card-category">{i['texto']}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """
        if html_paso!="":
            html_header = f"""
            <div class="row">
                {html_paso}
            </div>
            """
    #-------------------------------------------------------------------------#
    # Transacciones
    html_transacciones = ""
    if not datatransacciones.empty:
        html_grafica = ""
        df = datatransacciones.copy()
        if not df.empty and 'codigo' in df:
            df = df[df['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]

        df['year'] = pd.to_datetime(df['fecha_documento_publico'])
        df['year'] = df['year'].dt.year
        df         = df[df['year']>=(datetime.now().year-4)]
        df         = df.groupby('year').agg({'cuantiamt2':['count','median']}).reset_index()
        df.columns = ['fecha','count','value']
        df.index   = range(len(df))
        if not df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df['fecha'],y=df['count'],name='Transacciones',marker_color='#7189FF',offsetgroup=0,width=0.4,showlegend=True,text=df['count'],texttemplate='%{text}',textposition='inside',textangle=0,textfont=dict(color='white')),secondary_y=False)
            fig.add_trace(go.Bar(x=df['fecha'],y=df['value'],name='Valor transacciones',marker_color='#624CAB',offsetgroup=1,width=0.4,showlegend=True,text=df['value'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=10)),secondary_y=True)
            
            fig.update_layout(
                title='Transacciones',
                xaxis_title=None,
                yaxis_title=None,
                yaxis2_title=None,
                barmode='group',
                #height=200, width=600,
                height=int(mapheight), width=int(mapwidth*0.6*0.35),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                margin=dict(l=0, r=0, t=20, b=5),
                legend=dict(orientation='h', yanchor='top',y=-0.2,xanchor='center',x=0.5,bgcolor='white',font=dict(color='black')),
                title_font=dict(size=11,color='black'),
            )
            fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(color='black'),showgrid=False, zeroline=False,)
            fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'), title_font=dict(color='black'))
            fig.update_yaxes(title=None, secondary_y=True, showgrid=False, zeroline=False, tickfont=dict(color='black'))
            html_fig_paso = fig.to_html(config={'displayModeBar': False})
            try:
                soup = BeautifulSoup(html_fig_paso, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
                html_grafica = f""" 
                <div class="col-8">
                    <div class="card card-stats card-round card-custom">
                        <div class="card-body card-body-custom">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="graph-container" style="width: 100%; height: auto;">
                                        {soup}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """
            except: pass
        
        html_inputs = ""
        datapaso    = datatransacciones.copy()
        datapaso['fecha_documento_publico'] = pd.to_datetime(datapaso['fecha_documento_publico'])
        if not datapaso.empty and 'codigo' in datapaso:
            datapaso = datapaso[datapaso['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
        if not datapaso.empty:
            filtrodate    = datetime.now()-timedelta(days=365)
            datapaso      = datapaso[datapaso['fecha_documento_publico']>=filtrodate]
        if not datapaso.empty:
            input1   = '{:,.0f}'.format(len(datapaso))
            valormt2 = int(datapaso['cuantiamt2'].median() // 1000 * 1000)
            input2   = f"${valormt2:,.0f}"
            html_inputs = f"""
            <div class="col-4">
                <div class="row mb-3">
                    <div class="col-12 mb-3">
                        <div class="card card-stats card-round">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col col-stats ms-3 ms-sm-0">
                                        <div class="numbers">
                                            <h4 class="card-title" style="margin-bottom: 10px;">{input1}</h4>
                                            <p class="card-category">Transacciones</p>
                                            <p class="card-category" style="font-size: 0.6rem;">(ultimos 12 meses)</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="card card-stats card-round">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col col-stats ms-3 ms-sm-0">
                                        <div class="numbers">
                                            <h4 class="card-title" style="margin-bottom: 10px;">{input2}</h4>
                                            <p class="card-category">Valor transacciones m²</p>
                                            <p class="card-category" style="font-size: 0.6rem;">(ultimos 12 meses)</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        html_transacciones = f"""
        <div class="row">
            {html_inputs}
            {html_grafica}
        </div>
        """
        
    #-------------------------------------------------------------------------#
    # Avaluos y prediales
    html_vigencia = ""
    if not datavigencia.empty:
        html_grafica = ""
        df         = datavigencia.copy()
        df         = df[df['vigencia']>=(df['vigencia'].max()-4)]
        df         = df.groupby(['vigencia','chip']).agg({'avaluomt2':'max','predialmt2':'max'}).reset_index()
        df.columns = ['vigencia','chip','avaluomt2','predialmt2']
        df         = df.groupby('vigencia').agg({'avaluomt2':'median','predialmt2':'median'}).reset_index()
        df.columns = ['fecha','avaluomt2','predialmt2']
        df.index   = range(len(df))
        if not df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df['fecha'],y=df['predialmt2'],name='Predial',marker_color='#7189FF',offsetgroup=1,width=0.4,showlegend=True,text=df['predialmt2'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=10)),secondary_y=False)
            fig.add_trace(go.Bar(x=df['fecha'],y=df['avaluomt2'],name='Avalúo Catastral',marker_color='#624CAB',offsetgroup=0,width=0.4,showlegend=True,text=df['avaluomt2'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=10)),secondary_y=True)

            fig.update_layout(
                title='Avalúo catastral y predial',
                xaxis_title=None,
                yaxis_title=None,
                yaxis2_title=None,
                barmode='group',
                #height=200, width=600,
                height=int(mapheight), width=int(mapwidth*0.6*0.35),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                margin=dict(l=0, r=0, t=20, b=5),
                legend=dict(orientation='h', yanchor='top',y=-0.2,xanchor='center',x=0.5,bgcolor='white',font=dict(color='black')),
                title_font=dict(size=11,color='black'),
            )
            fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(color='black'),showgrid=False, zeroline=False,)
            fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'), title_font=dict(color='black'))
            fig.update_yaxes(title=None, secondary_y=True, showgrid=False, zeroline=False, tickfont=dict(color='black'))
            html_fig_paso = fig.to_html(config={'displayModeBar': False})
            try:
                soup = BeautifulSoup(html_fig_paso, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
                html_grafica = f""" 
                <div class="col-8">
                    <div class="card card-stats card-round card-custom">
                        <div class="card-body card-body-custom">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="graph-container">
                                        {soup}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """
            except: pass
        df         = datavigencia.groupby(['vigencia','chip']).agg({'avaluomt2':'max','predialmt2':'max'}).reset_index()
        df.columns = ['vigencia','chip','avaluomt2','predialmt2']
        w          = df.groupby('chip')['vigencia'].max().reset_index()
        w.columns  = ['chip','maxvigencia']
        df         = df.merge(w,on='chip',how='left',validate='m:1')
        df         = df[df['vigencia']==df['maxvigencia']]
        maxyear    = int(df['vigencia'].max())
        input1     = f"${int(df['avaluomt2'].median() // 1000 * 1000):,.0f}" if 'avaluomt2' in datavigencia else ''
        input2     = f"${df['predialmt2'].median():,.0f}" if 'predialmt2' in datavigencia else ''
        html_vigencia = f"""
        <div class="row">
            <div class="col-4">
                <div class="row mb-3">
                    <div class="col-12 mb-3">
                        <div class="card card-stats card-round">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col col-stats ms-3 ms-sm-0">
                                        <div class="numbers">
                                            <h4 class="card-title" style="margin-bottom: 10px;">{input1}</h4>
                                            <p class="card-category">Avalúo catastral m²</p>
                                            <p class="card-category" style="font-size: 0.6rem;">({maxyear})</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="card card-stats card-round">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col col-stats ms-3 ms-sm-0">
                                        <div class="numbers">
                                            <h4 class="card-title" style="margin-bottom: 10px;">{input2}</h4>
                                            <p class="card-category">Predial por m²</p>
                                            <p class="card-category" style="font-size: 0.6rem;">({maxyear})</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {html_grafica}
        </div>
        """

    #-------------------------------------------------------------------------#
    # Tiplogias
    html_tipologias = ""
    html_grafica    = ""
    if not datacatastro.empty:
        formato = [{'variable':'preaconst' ,'titulo':'Distribución por Área Privada'},
                  {'variable':'prevetustz','titulo':'Distribución por Antigüedad'}]
        for iiter in formato:
            variable = iiter['variable']
            titulo   = iiter['titulo']
            df         = datacatastro.copy()
            df         = df[df[variable]>0]
            
            if not df.empty:
                df['isin'] = 1
                q1         = df.groupby('isin')[variable].quantile(0.25).reset_index()
                q1.columns = ['isin','q1']
                q3         = df.groupby('isin')[variable].quantile(0.75).reset_index()
                q3.columns = ['isin','q3']
                
                # Remover outliers
                w         = q1.merge(q3,on='isin',how='outer')
                w['iqr']  = w['q3']-w['q1']
                w['linf'] = w['q1'] - 1.5*w['iqr']
                w['lsup'] = w['q3'] + 1.5*w['iqr']
                df        = df.merge(w[['isin','linf','lsup']],on='isin',how='left',validate='m:1')
                df        = df[(df[variable]>=df['linf']) & (df[variable]<=df['lsup'])]
                
                w         = df.groupby('isin')['prechip'].count().reset_index() 
                w.columns = ['isin','count']
                df        = df.merge(w,on='isin',how='left',validate='m:1')
                df        = df[df['count']>2]
        
            if not df.empty:
                fig = px.box(df,x='isin',y=variable,title=titulo,color_discrete_sequence=['#624CAB'])
                fig.update_layout(
                    title_x=0.55,
                    height=int(mapheight),
                    #width=600,
                    width=int(mapwidth*0.6*0.35),
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(l=80, r=0, t=20, b=0),
                    plot_bgcolor='rgba(0, 0, 0, 0)',
                    paper_bgcolor='rgba(0, 0, 0, 0)',
                    title_font=dict(size=11, color='black')
                )
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                html_fig_paso = fig.to_html(config={'displayModeBar': False})
                try:
                    soup = BeautifulSoup(html_fig_paso, 'html.parser')
                    soup = soup.find('body')
                    soup = str(soup.prettify())
                    soup = soup.replace('<body>', '<div style="width: 100%; height: 100%;margin-bottom: 0px;">').replace('</body>', '</div>')
                    html_grafica += f""" 
                    <div class="col-6">
                        <div class="card card-stats card-round card-custom">
                            <div class="card-body card-body-custom">
                                <div class="row align-items-center">
                                    <div class="col col-stats ms-3 ms-sm-0">
                                        <div class="graph-container">
                                            {soup}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                except: pass
        html_tipologias = f"""
        <div class="row">
            {html_grafica}
        </div>
        """

    #-------------------------------------------------------------------------#
    # Market
    html_market = ""
    if not datamarket.empty:
        askventa = datamarket[datamarket['tiponegocio']=='Venta']['valormt2'].median()
        askventa = int(askventa // 1000 * 1000) if askventa>0 else None
        obsventa = len(datamarket[datamarket['tiponegocio']=='Venta'])
        obsventa = obsventa if obsventa>0 else None

        askrenta = datamarket[datamarket['tiponegocio']=='Arriendo']['valormt2'].median()
        askrenta = askrenta if askrenta>0 else None
        obsrenta = len(datamarket[datamarket['tiponegocio']=='Arriendo'])
        obsrenta = obsrenta if obsrenta>0 else None
        
        formato = [{'texto':'Precio de lista en VENTA','value1':askventa,'value2':obsventa},
                   {'texto':'Precio de lista en RENTA','value1':askrenta,'value2':obsrenta},]
        
        html_paso = ""
        for i in formato:
            if i['value1'] is not None:
                html_paso += f"""
                <div class="col-6 col-md-6 mb-3">
                    <div class="card card-stats card-round">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="numbers">
                                        <h4 class="card-title">${i['value1']:,.0f} m²</h4>
                                        <p class="card-category">Registros: {i['value2']}</p>
                                        <p class="card-category">{i['texto']}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """
        if html_paso!="":
            html_market = f"""
            <div class="row">
                {html_paso}
            </div>
            """
            
    style = """
    <style>
        body, html {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        .card {
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
        }

        .card-stats .icon-big {
            font-size: 3rem;
            line-height: 1;
            color: #fff;
        }

        .card-stats .icon-primary {
            background-color: #007bff;
        }

        .bubble-shadow-small {
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            border-radius: 50%;
            padding: 1rem;
        }

        .card-stats .numbers {
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
        }

        .card-stats .card-category {
            color: #6c757d;
            font-size: 0.8rem;
            margin: 0;
            text-align: center;
        }

        .card-stats .card-title {
            margin: 0;
            font-size: 1.2rem;
            font-weight: bold;
            text-align: center;
        }
        
        .small-text {
            font-size: 0.3rem; 
            color: #6c757d; 
        }
        .graph-container {
            width: 100%;
            height: 100%;
            margin-bottom: 0;
        }
        
        .card-custom {
            height: 215px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .card-body-custom {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Visitors Card</title>
        <!-- Incluyendo Bootstrap CSS para el diseño de las tarjetas -->
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/5.0.0-alpha1/css/bootstrap.min.css">
        <!-- Font Awesome para los íconos -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        {style}
    </head>
    <body>
        <div class="container-fluid">
            {html_header}
            {html_transacciones}
            {html_vigencia}
            {html_market}
            {html_tipologias}
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
