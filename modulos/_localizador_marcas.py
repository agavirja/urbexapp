import folium
import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import plotly.express as px
from streamlit_folium import folium_static
from bs4 import BeautifulSoup
from streamlit_js_eval import streamlit_js_eval
from shapely.geometry import Point
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, AgGridTheme
from st_aggrid.shared import JsCode
from datetime import datetime

from data.getdataBrands import getoptions,getallcountrybrands

from display.stylefunctions  import style_function_geojson

from folium.features import CustomIcon

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
               'data_localizador_marcas':pd.DataFrame(),
               'search_localizador_marcas':False,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
    latitud   = 4.652652 
    longitud  = -74.077899
    idxlabel  = []
    
    with st.spinner('Busqueda de información'):
        dataoptions = getoptions()

        col1,col2,col3 = st.columns([0.4,0.3,0.3])
        
        with col1:
            segmento = st.multiselect('Busqueda por:',options=sorted(list(dataoptions['label'].unique())))
            if isinstance(segmento,list) and segmento!=[]:
                idxlabel = list(set(list(dataoptions[dataoptions['label'].isin(segmento)]['idxlabel'].unique())))
        
    if isinstance(idxlabel,list) and idxlabel!=[]:
        with col2:
            st.write('')
            st.write('')
            if st.button('Buscar'):
                with st.spinner('Buscando data'):
                    st.session_state.data_localizador_marcas   = getallcountrybrands(idxlabel=idxlabel)
                    st.session_state.search_localizador_marcas = True
                    st.rerun()
                    
        with col3:
            st.write('')
            st.write('')
            if st.button('Resetear búsqueda'):
                for key,value in formato.items():
                    del st.session_state[key]
                st.rerun()
            
    #st.dataframe(st.session_state.data_localizador_marcas)
    if st.session_state.search_localizador_marcas and not st.session_state.data_localizador_marcas.empty:
        dashboard(st.session_state.data_localizador_marcas,mapwidth=mapwidth)
    elif st.session_state.search_localizador_marcas and st.session_state.data_localizador_marcas.empty:
        st.error('No se encontró información de predios')
 


def dashboard(data,mapwidth=1280):
    
    #---------------------------------------------------------------------#
    # filtros
    #---------------------------------------------------------------------#
    cols1,cols2 = st.columns(2,gap="small")
    with cols1:
        empresa = st.multiselect('Empresa',options=data['empresa'].unique())
        if isinstance(empresa,list) and empresa!=[]:
            data = data[data['empresa'].isin(empresa)]
            
    if not data.empty and 'prenbarrio' in data:
        options = list(sorted(data[data['prenbarrio'].notnull()]['prenbarrio'].unique()))
        with cols2:
            barrio = st.multiselect('Barrio',options=options)
            if barrio!=[]:
                data = data[data['prenbarrio'].isin(barrio)]

    col1,col2 = st.columns([0.3,0.6])
    #-------------------------------------------------------------------------#
    # Tabla de datos
    #-------------------------------------------------------------------------#
    dftable      = data.copy()
    data.index   = range(len(data))
    chipselected = None
    if not dftable.empty:
        dftable   = dftable[(dftable['latitud'].notnull()) & (dftable['longitud'].notnull())]
        variables = ['empresa','nombre','prenbarrio','predirecc','usosuelo','barmanpre']
        variables = [x for x in variables if x in dftable]
        dftable   = dftable[variables]
        dftable.rename(columns={'empresa':'Empresa','nombre':'Nombre','prenbarrio':'Barrio','predirecc':'Dirección','usosuelo':'Uso del suelo'},inplace=True)
        
    if not dftable.empty:
        dftable['link'] = dftable['barmanpre'].apply(lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={x}&vartype=barmanpre&token={st.session_state.token}")
        dftable.drop(columns=['barmanpre'],inplace=True)
        
        gb = GridOptionsBuilder.from_dataframe(dftable,editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        cell_renderer =  JsCode("""function(params) {return `<a href=${params.value} target="_blank">${params.value}</a>`}""")
        
        gb.configure_column(
            "link",
            headerName="link",
            cellRenderer=JsCode("""
                class UrlCellRenderer {
                  init(params) {
                    this.eGui = document.createElement('a');
                    this.eGui.innerText = 'Reporte completo';
                    this.eGui.setAttribute('href', params.value);
                    this.eGui.setAttribute('style', "text-decoration:none");
                    this.eGui.setAttribute('target', "_blank");
                  }
                  getGui() {
                    return this.eGui;
                  }
                }
            """)
        )
    
        if   len(dftable)>=13: tableH = 400
        elif len(dftable)>=5:  tableH = int(len(dftable)*60)
        elif len(dftable)>1:   tableH = int(len(dftable)*80)
        elif len(dftable)==1:  tableH = 100
        else: tableH = 100
        with col2:
            response = AgGrid(dftable,
                        gridOptions=gb.build(),
                        columns_auto_size_mode="FIT_CONTENTS",
                        theme=AgGridTheme.STREAMLIT,
                        updateMode=GridUpdateMode.VALUE_CHANGED,
                        allow_unsafe_jscode=True,
                        width=int(mapwidth*0.7),
                        #height=400,
                        height=int(min(400, tableH)),
                        )
        
            df = pd.DataFrame(response['selected_rows'])
            if not df.empty:
                df.rename(columns={'Empresa':'empresa','Nombre':'nombre','Barrio':'prenbarrio','Dirección':'predirecc'},inplace=True)
                df['isin'] = 1
                df         = df[['isin','empresa','nombre','prenbarrio','predirecc']]
                datamerge  = data.merge(df,on=['empresa','nombre','prenbarrio','predirecc'],how='left',validate='m:1')
                datamerge  = datamerge[datamerge['isin']==1]
                data       = data[data.index.isin(datamerge.index)]

    #---------------------------------------------------------------------#
    # Mapa de referencia
    #---------------------------------------------------------------------#
    st.dataframe(data)
    st.write(data['radio'].iloc[0])
    st.write(json.loads(data['radio'].iloc[0]))
    
    if not data.empty:
        
        latitud,longitud = 4.688002,-74.054444  # Para centrarlo en Bogota 
        if 'latitud' in data and 'longitud' in data:
            latitud  = data['latitud'].mean()
            longitud = data['longitud'].mean()
        
        m = folium.Map(location=[latitud, longitud], zoom_start=11,tiles="cartodbpositron")

        geojson = data2geopandas(data)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        # Marker        
        #folium.GeoJson(geojsonpoints,style_function=style_function_geojson).add_to(m)
        
        df = data.copy()
        df = df[(df['latitud'].notnull()) & (df['longitud'].notnull())]
        if not df.empty:
            for _,items in df.iterrows():
                icon = folium.features.CustomIcon(
                    icon_image = items["marker"],
                    icon_size  = (25, 25),
                )
                try:    empresa = f"<b> Empresa:</b> {items['empresa']}<br>" if isinstance(items['empresa'],str) and items['empresa']!='' else 'Sin información'
                except: empresa = "<b> Empresa:</b> Sin información <br>" 
                try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>" if isinstance(items['direccion'],str) and items['direccion']!='' else 'Sin información'
                except: direccion = "<b> Dirección:</b> Sin información <br>" 
                try:    nombre = f"<b> Nombre:</b> {items['nombre']}<br>" if isinstance(items['nombre'],str) and items['nombre']!='' else 'Sin información'
                except: nombre = "<b> Nombre:</b> Sin información <br>" 
                try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>" if isinstance(items['prenbarrio'],str) and items['prenbarrio']!='' else 'Sin información'
                except: barrio = "<b> Barrio:</b> Sin información <br>"      
                
                popup_content = ""
                if 'barmanpre' in items and isinstance(items['barmanpre'],str) and items['barmanpre']!='':
                    urllink       = f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}"
                    popup_content =  f'''
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                        <h5 style="text-align: center; margin-bottom: 10px;">Detalle del predio:</h5>
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {empresa}
                            {direccion}
                            {nombre}
                            {barrio}
                        </a>
                    </div>
                    '''
                
                if 'radio' in items and isinstance(items['radio'],str) and items['radio']!='':
                    urllink = f"http://www.urbex.com.co/Busqueda_avanzada?type=marcaradio&code={items['id']}&vartype=id&token={st.session_state.token}"
                    popup_content +=  f'''
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                        <h5 style="text-align: center; margin-bottom: 10px;">Análisis de radio:</h5>
                        <a href="{urllink}" target="_blank" style="color: black;">
                            <b> Empresa:</b> {items['empresa']}<br>
                            <b> Nombre:</b> {items['nombre']}<br>
                            <b> Dirección:</b> {items['direccion']}<br>
                        </a>
                    </div>
                    '''
                if popup_content=='':
                    popup_content =  f'''
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                        {empresa}
                        {direccion}
                        {nombre}
                        {barrio}
                    </div>
                    '''
                    
                popup_content =  f'''
                <!DOCTYPE html>
                <html>
                    <body>
                        {popup_content}
                    </body>
                </html>
                '''
                
                folium.Marker(location=[items["latitud"], items["longitud"]], icon=icon,popup=popup_content).add_to(m)
            
        with col1:
            folium_static(m,width=int(mapwidth*0.4),height=900)
    
    #-------------------------------------------------------------------------#
    # Dashboard
    #-------------------------------------------------------------------------#
    with col2:
        html = reporteHtml(data=data,mapwidth=mapwidth,mapheight=200)
        st.components.v1.html(html, height=900)


@st.cache_data(show_spinner=False)
def data2geopandas(data,barmanpreref=None):
    
    urlexport = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color'] = '#5A189A'    
        data['popup'] = None
        data.index    = range(len(data))
        for idd,items in data.iterrows():
            try:    empresa = f"<b> Empresa:</b> {items['empresa']}<br>"
            except: empresa = "<b> Empresa:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>" 
            try:    nombre = f"<b> Nombre:</b> {items['nombre']}<br>"
            except: nombre = "<b> Nombre:</b> Sin información <br>" 
            try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>"
            except: barrio = "<b> Barrio:</b> Sin información <br>"      
            
            urllink   = urlexport+f"?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}"

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {empresa}
                            {direccion}
                            {nombre}
                            {barrio}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        variables = [x for x in ['color','popup','geometry'] if x in data]
        data      = data[variables]
        geojson   = data.to_json()
    
    return geojson

@st.cache_data(show_spinner=False)
def geopoints(data,barmanpreref=None):
    
    geojson = pd.DataFrame().to_json()
    
    if not data.empty:
        if 'latitud' in data and 'longitud' in data:
            data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]

    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data             = data[['geometry','marker']]
        data['color']    = '#A16CFF'
        geojson          = data.to_json()
        
    return geojson
        
@st.cache_data(show_spinner=False)
def reporteHtml(data=pd.DataFrame(),mapwidth=1280,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Header
    html_header = ""
    if not data.empty:
        formato = [
                   {'texto':'Total locaciones','value': '{:,.0f}'.format(int(len(data))) if len(data)>0 else None },
                   {'texto':'Barrios','value': '{:,.0f}'.format(int(len(data['prenbarrio'].unique()))) if len(data)>0 else None  },
                   ]
        html_paso = ""
        for i in formato:
            if i['value'] is not None:
                html_paso += f"""
                <div class="col-6 col-md-6 mb-3">
                    <div class="card card-stats card-round">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="numbers">
                                        <h4 class="card-title">{i['value']}</h4>
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
            
    html_barrio  = ""
    html_grafica = ""
    if not data.empty:
        df         = data.groupby('prenbarrio')['barmanpre'].count().reset_index()
        df.columns = ['barrio','conteo']
        df         = df.sort_values(by='conteo',ascending=False)
        df.index   = range(len(df))
        df         = df.sort_values(by='conteo',ascending=False)
        df         = df.head(8)
        
        fig = px.bar(df, x='barrio', y="conteo", text="conteo", title='Barrio')
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#A16CFF', textfont=dict(color='white'))
        fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
        fig.update_xaxes(tickmode='linear', dtick=1)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'title_font':dict(color='black'),
            'legend':dict(bgcolor='black'),
            'height':int(mapheight), 
            'width':int(mapwidth*0.3),
            'margin':dict(l=0, r=0, t=0, b=50),
        })
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(size=7,color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'), type='log')

        html_fig_paso = fig.to_html(config={'displayModeBar': False})
        try:
            soup = BeautifulSoup(html_fig_paso, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>', '<div style="width: 100%; height: 100%;margin-bottom: 0px;">').replace('</body>', '</div>')
            html_grafica += f""" 
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
    if not data.empty:
        df         = data.groupby('prenbarrio')['barmanpre'].count().reset_index()
        df.columns = ['barrio','conteo']
        df         = df.sort_values(by='conteo',ascending=False)
        df.index   = range(len(df))
        df         = df.sort_values(by='conteo',ascending=False)
        df         = df.iloc[8:]
        df         = pd.DataFrame([{'barrio': 'Otros Barrios', 'conteo': df['conteo'].sum()}])

        fig = px.bar(df, x='barrio', y="conteo", text="conteo", title='Barrio')
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#A16CFF', textfont=dict(color='white'))
        fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
        fig.update_xaxes(tickmode='linear', dtick=1)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'title_font':dict(color='black'),
            'legend':dict(bgcolor='black'),
            'height':int(mapheight), 
            'width':int(mapwidth*0.2),
            'margin':dict(l=0, r=0, t=0, b=20),
        })
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'), type='log')

        html_fig_paso = fig.to_html(config={'displayModeBar': False})
        try:
            soup = BeautifulSoup(html_fig_paso, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>', '<div style="width: 100%; height: 100%;margin-bottom: 0px;">').replace('</body>', '</div>')
            html_grafica += f""" 
            <div class="col-4">
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
    html_barrio = f"""
    <div class="row" style="margin-top:20px;">
        {html_grafica}
    </div>
    """

    #-------------------------------------------------------------------------#
    # Tiplogias
    html_tipologias = ""
    html_grafica    = ""
    if not data.empty:
        formato = [{'variable':'empresa' ,'titulo':'Empresa'}]
        
        variable   = 'empresa'
        titulo     = 'Empresa'
        df         = data.copy()
        df         = df.groupby([variable]).agg({'barmanpre':'count','marker_color':'first'}).reset_index()
        df.columns = [variable,'conteo','color']
                
        fig          = px.bar(df, x=variable, y="conteo", text="conteo", title=titulo)
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#A16CFF', textfont=dict(color='white'))
        fig.update_traces(marker_color=df['color'])
        fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
        fig.update_xaxes(tickmode='linear', dtick=1)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'title_font':dict(color='black'),
            'legend':dict(bgcolor='black'),
            'height':int(mapheight), 
            'width':int(mapwidth*0.35),
            'margin':dict(l=0, r=0, t=30, b=20),
        })    
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))

        html_fig_paso = fig.to_html(config={'displayModeBar': False})
        try:
            soup = BeautifulSoup(html_fig_paso, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>', '<div style="width: 100%; height: 100%;margin-bottom: 0px;">').replace('</body>', '</div>')
            html_grafica += f""" 
            <div class="col-12">
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
        <div class="row" style="margin-top:20px;">
            {html_grafica}
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
            {html_tipologias}
            {html_barrio}
        </div>
    </body>
    </html>
    """
    return html
if __name__ == "__main__":
    main()
