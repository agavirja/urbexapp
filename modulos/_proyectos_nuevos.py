import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import base64
import json
import shapely.wkt as wkt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping,shape,Point
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, AgGridTheme
from st_aggrid.shared import JsCode

from data.getdataproyectosnuevos import dataproyectosnuevos, datatransaccionesproyectos
from data.circle_polygon import circle_polygon

from display.stylefunctions  import style_function,style_function_geojson

def main(tipo=None,code=None):
    
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
        landing(tipo=tipo,code=code,mapwidth=mapwidth,mapheight=mapheight)
    else: 
        st.error('Por favor iniciar sesión para poder tener acceso a la plataforma de Urbex')
    
def landing(tipo=None,code=None,mapwidth=1280,mapheight=200):

    usosuelo = ['002','038']
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_proyectos':None,
               'zoom_start':12,
               'latitud':4.652652, 
               'longitud':-74.077899,
               'estado':'search',
               'metros':500,
               'dataproyectos':pd.DataFrame(),
               'dataformulada':pd.DataFrame(),
               'datalongproyectos':pd.DataFrame(),
               'datapricing':pd.DataFrame(),
               'datatransacciones':pd.DataFrame(),
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if not 'reporte' in st.session_state.estado and isinstance(tipo,str) and 'polygon' in tipo and isinstance(code,str) and code!='':
        try:
            codejson = base64.b64decode(code)
            codejson = codejson.decode('utf-8')
            codejson = json.loads(codejson)
    
            st.session_state.latitud  = codejson['latitud'] if 'latitud' in codejson else st.session_state.latitud
            st.session_state.longitud = codejson['longitud'] if 'longitud' in codejson else st.session_state.longitud
            st.session_state.metros   = codejson['metros'] if 'metros' in codejson else st.session_state.metros
            st.session_state.estado = 'polygon'
        except: 
            st.session_state.estado = 'search'
            
    colm1,colm2,colm3 = st.columns([0.025,0.95,0.025])
    colb1,colb2       = st.columns(2)
    colf1,colf2       = st.columns(2)
    
    dataproyectos     = st.session_state.dataproyectos.copy()
    dataformulada     = st.session_state.dataformulada.copy()
    datalongproyectos = st.session_state.datalongproyectos.copy()
    datapricing       = st.session_state.datapricing.copy()
    
    if not dataproyectos.empty:
        if 'estado' in dataproyectos:
            dataproyectos['tipoestado'] = dataproyectos['estado'].replace(['Term','Desist','Const','Prev'],['Terminado','Desistido','Construcción','Preventas'])
            with colf1:
                options = list(dataproyectos['tipoestado'].unique())
                estado  = st.multiselect('Estado:',options=options)
                if isinstance(estado,list) and estado!=[]:
                    dataproyectos = dataproyectos[dataproyectos['tipoestado'].isin(estado)]
                  
        if 'proyecto' in dataproyectos:
            with colf2:
                options  = list(sorted(dataproyectos['proyecto'].unique()))
                proyecto = st.multiselect('Proyecto:',options=options)
                if isinstance(proyecto,list) and proyecto!=[]:
                    dataproyectos = dataproyectos[dataproyectos['proyecto'].isin(proyecto)]
                             
        if 'construye' in dataproyectos:
            dataproyectos['construye'] = dataproyectos['construye'].apply(lambda x: x.replace('Const.','').strip() if isinstance(x,str) else None)
            with colf1:
                options     = list(sorted(dataproyectos['construye'].unique()))
                constructor = st.multiselect('Constructor:',options=options)
                if isinstance(constructor,list) and constructor!=[]:
                    dataproyectos = dataproyectos[dataproyectos['construye'].isin(constructor)]
                    
        if 'vende' in dataproyectos:
            with colf2:
                options = list(sorted(dataproyectos['vende'].unique()))
                vende   = st.multiselect('Vende:',options=options)
                if isinstance(vende,list) and vende!=[]:
                    dataproyectos = dataproyectos[dataproyectos['vende'].isin(vende)]
                    
        if 'fecha_inicio' in dataproyectos:
            dataproyectos['fecha_inicio'] = pd.to_datetime(dataproyectos['fecha_inicio'])
            
            with colf1:
                fecha_desde  = st.date_input('Fecha de inicio del proyecto (desde)',dataproyectos['fecha_inicio'].min())
                fecha_desde  = datetime.combine(fecha_desde, datetime.min.time())
            with colf2:
                fecha_hasta  = st.date_input('Fecha de inicio del proyecto (hasta)',max(datetime.now(),dataproyectos['fecha_inicio'].max()))
                fecha_hasta  = datetime.combine(fecha_hasta, datetime.min.time())
            dataproyectos = dataproyectos[(dataproyectos['fecha_inicio']>=fecha_desde) & (dataproyectos['fecha_inicio']<=fecha_hasta)]
            
        if 'fecha_entrega' in dataproyectos:
            dataproyectos['fecha_entrega'] = pd.to_datetime(dataproyectos['fecha_entrega'])
            
            with colf1:
                fecha_desde  = st.date_input('Fecha de entrega del proyecto (desde)',dataproyectos['fecha_entrega'].min())
                fecha_desde  = datetime.combine(fecha_desde, datetime.min.time())
            with colf2:
                fecha_hasta  = st.date_input('Fecha de entrega del proyecto (hasta)',max(datetime.now(),dataproyectos['fecha_entrega'].max()))
                fecha_hasta  = datetime.combine(fecha_hasta, datetime.min.time())
            dataproyectos = dataproyectos[(dataproyectos['fecha_entrega']>=fecha_desde) & (dataproyectos['fecha_entrega']<=fecha_hasta)]
            
    #-------------------------------------------------------------------------#
    # Filtros:
    if not dataproyectos.empty and not dataformulada.empty:
         dataformulada = dataformulada[dataformulada['codproyecto'].isin(dataproyectos['codproyecto'])]
    if not dataproyectos.empty and not datalongproyectos.empty:
         datalongproyectos = datalongproyectos[datalongproyectos['codproyecto'].isin(dataproyectos['codproyecto'])]
    if not dataproyectos.empty and not datapricing.empty:
         datapricing = datapricing[datapricing['codproyecto'].isin(dataproyectos['codproyecto'])]
    
    if 'search' in st.session_state.estado:
        #---------------------------------------------------------------------#
        # Mapa
        m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        draw = Draw(
                    draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                    edit_options={"poly": {"allowIntersection": False}}
                    )
        draw.add_to(m)

        if st.session_state.polygon_proyectos is not None:
            folium.GeoJson(st.session_state.polygon_proyectos, style_function=style_function).add_to(m)
            
        with colm2:
            st_map = st_folium(m,width=int(mapwidth),height=int(mapheight*0.3))
            
        if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
            if st_map['all_drawings']!=[]:
                if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                    coordenadas                              = st_map['all_drawings'][0]['geometry']['coordinates']
                    st.session_state.polygon_proyectos = Polygon(coordenadas[0])
                    geojson                            = mapping(st.session_state.polygon_proyectos)
                    polygon_shape                      = shape(geojson)
                    centroid                           = polygon_shape.centroid
                    st.session_state.latitud           = centroid.y
                    st.session_state.longitud          = centroid.x
                    st.session_state.zoom_start        = 14
                    st.rerun()
                
    col1,col2 = st.columns(2)
    #-------------------------------------------------------------------------#
    # Reporte
    if 'search' in st.session_state.estado and st.session_state.polygon_proyectos is not None: 
        with colb1:
            if st.button('Buscar'):
                with st.spinner('Buscando información'):
                    st.session_state.dataproyectos,st.session_state.dataformulada,st.session_state.datalongproyectos,st.session_state.datapricing = dataproyectosnuevos(str(st.session_state.polygon_proyectos))
                    st.session_state.datatransacciones = datatransaccionesproyectos({'polygon':str(st.session_state.polygon_proyectos),'precuso':usosuelo})
                    st.session_state.estado = 'reporte'
                    st.rerun()
    with colb2:
        if st.button('Resetear búsqueda'):
            for key,value in formato.items():
                del st.session_state[key]
            st.rerun()
               
    if 'polygon' in st.session_state.estado:
        with st.spinner('Buscando información'):
            st.session_state.polygon_proyectos = circle_polygon(st.session_state.metros,st.session_state.latitud,st.session_state.longitud)
            st.session_state.dataproyectos,st.session_state.dataformulada,st.session_state.datalongproyectos,st.session_state.datapricing = dataproyectosnuevos(str(st.session_state.polygon_proyectos))
            st.session_state.datatransacciones =  datatransaccionesproyectos({'polygon':str(st.session_state.polygon_proyectos),'precuso':usosuelo})
            st.session_state.estado     = 'reporte'
            st.session_state.zoom_start = 14
            st.rerun()
        
    st.dataframe(st.session_state.datatransacciones)
    
    if 'reporte' in st.session_state.estado and not dataproyectos.empty:
        
        col1,col2 = st.columns([0.3,0.7])
        #-------------------------------------------------------------------------#
        # Mapa
        m    = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start,tiles="cartodbpositron")
        draw = Draw(
                    draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                    edit_options={"poly": {"allowIntersection": False}}
                    )
        draw.add_to(m)

        if st.session_state.polygon_proyectos is not None:
            folium.GeoJson(st.session_state.polygon_proyectos, style_function=style_function_opacity).add_to(m)
            
        if not dataproyectos.empty:
            geopoints = point2geopandas(dataproyectos)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            #folium.GeoJson(geopoints,popup=popup).add_to(m)

            #marker = folium.Marker(icon=folium.Icon(icon='point',color="color"))
            marker = folium.Circle(radius=20,fill=True,fill_opacity=1)
            folium.GeoJson(geopoints,popup=popup,style_function=style_function_geojson,marker=marker).add_to(m)

        with col1:
            st_map = st_folium(m,width=int(mapwidth*0.3),height=920)
            
        #-------------------------------------------------------------------------#
        # Reporte
        with col2:
            html = reporteHtml(dataproyectos=dataproyectos,dataformulada=dataformulada,datapricing=datapricing,mapwidth=mapwidth,mapheight=200)
            st.components.v1.html(html, height=920)

        #-------------------------------------------------------------------------#
        # Tipologias
        html = tipologiaHtml(dataformulada=dataformulada,mapwidth=mapwidth,mapheight=200)
        st.components.v1.html(html, height=300)
        
        #-------------------------------------------------------------------------#
        # Seleccion del inmueble
        dataproyecto_select      = pd.DataFrame()
        dataformulada_select     = pd.DataFrame()
        datalongproyectos_select = pd.DataFrame()
        datapricing_select       = pd.DataFrame()

        if 'last_object_clicked' in st_map and st_map['last_object_clicked']:
            try:
                proyecto = st_map["last_object_clicked_popup"].split('Proyecto:')[-1].split('Estado')[0].strip()
                proyecto = proyecto if isinstance(proyecto,str) else None
            except: proyecto = None
            if isinstance(proyecto,str) and proyecto!='':
                idd   = dataproyectos['proyecto'].astype(str).str.contains(proyecto)
                if sum(idd)>0:
                    dataproyecto_select      = dataproyectos[idd]
                    dataformulada_select     = dataformulada[dataformulada['codproyecto'].isin(dataproyecto_select['codproyecto'])]
                    datalongproyectos_select = datalongproyectos[datalongproyectos['codproyecto'].isin(dataproyecto_select['codproyecto'])]
                    datapricing_select       = datapricing[datapricing['codproyecto'].isin(dataproyecto_select['codproyecto'])]
            
        #-------------------------------------------------------------------------#
        # Tabla
        col1,col2 = st.columns([0.6,0.4])
        dftable = dataformulada_select.copy()
        if not dftable.empty:
            dftable   = dftable.sort_values(by='areaconstruida',ascending=True)
            variables = ['proyecto','tipo','areaconstruida','habitaciones','banos','garajes']
            variables = [x for x in variables if x in dftable]
            dftable   = dftable[variables]   
            dftable.rename(columns={'proyecto':'Proyecto','tipo':'Tipo de inmueble','areaconstruida':'Área construida','habitaciones':'Habitaciones','banos':'Baños','garajes':'Garajes'},inplace=True)
    
        if not dftable.empty:
            
            gb = GridOptionsBuilder.from_dataframe(dftable,editable=True)
            gb.configure_selection(selection_mode="single", use_checkbox=True)
            gb.configure_grid_options(preSelectedRows=[0])
            
            if   len(dftable)>=5: tableH = 200
            elif len(dftable)>=3:  tableH = int(len(dftable)*60)
            elif len(dftable)>1:   tableH = int(len(dftable)*80)
            else: tableH = 100
    
            with col1:
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
            if df.empty:
                df = dftable.iloc[[0]]
            if not df.empty:
                df.rename(columns={'Proyecto': 'proyecto', 'Tipo de inmueble': 'tipo', 'Área construida': 'areaconstruida', 'Habitaciones': 'habitaciones', 'Baños': 'banos', 'Garajes': 'garajes'},inplace=True)
                df['isin']        = 1
                dataformulada     = dataformulada.merge(df,on=['proyecto', 'tipo', 'areaconstruida', 'habitaciones', 'banos', 'garajes'],how='left',validate='m:1')
                dataformulada     = dataformulada[dataformulada['isin']==1]
                datalongproyectos = datalongproyectos[datalongproyectos['codinmueble'].isin(dataformulada['codinmueble'])]

                with col2:
                    html = pricingHtml(datapricing=datalongproyectos,mapwidth=mapwidth,mapheight=200)
                    st.components.v1.html(html, height=300)
    elif 'reporte' in st.session_state.estado and dataproyectos.empty:
        st.error('No se encontraron proyectos nuevos')
        
    
@st.cache_data(show_spinner=False)
def point2geopandas(data):
    
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        #data['color']    = '#5A189A'
        data['color']    = data['estado'].replace(['Term', 'Desist', 'Const', 'Prev'],['#5CE092','#E07C5C','#E0BF5C','#5C9AE0'])
        data['popup']    = None
        for idd,items in data.iterrows():
            try:    proyecto = f"<b> Proyecto:</b> {items['proyecto']}<br>"
            except: proyecto = "<b> Proyecto:</b> Sin información <br>" 
            try:    estado = f"<b> Estado:</b> {items['estado']}<br>"
            except: estado = "<b> Estado:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>"
            try:    construye = f"<b> Construye:</b> {items['construye']}<br>"
            except: construye = "<b> Construye:</b> Sin información <br>"
            try:    vende = f"<b> Vende:</b> {items['vende']}<br>"
            except: vende = "<b> Vende:</b> Sin información <br>"
            try:    estrato = f"<b> Estrato:</b> {items['estrato']}<br>"
            except: estrato = "<b> Estrato:</b> Sin información <br>"
            try:    unidades = f"<b> Unidades:</b> {items['unidades_proyecto']}<br>"
            except: unidades = "<b> Unidades:</b> Sin información <br>" 
            try:    fechainicio = f"<b> Fecha inicio:</b> {items['fecha_inicio'].strftime('%Y-%m')}<br>"
            except: fechainicio = "<b> Fecha inicio:</b> Sin información <br>" 
            try:    fechaentrega = f"<b> Fecha entrega:</b> {items['fecha_entrega'].strftime('%Y-%m')}<br>"
            except: fechaentrega = "<b> Fecha entrega:</b> Sin información <br>" 
            try:    fiduciaria = f"<b> Fiduciaria:</b> {items['fiduciaria']}<br>"
            except: fiduciaria = "<b> Fiduciaria:</b> Sin información <br>"            
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 14px;">
                        <a style="color: black;">
                            {direccion}    
                            {proyecto}
                            {estado}
                            {construye}
                            {vende}
                            {estrato}
                            {unidades}
                            {fechainicio}
                            {fechaentrega}
                            {fiduciaria}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        data    = data[['geometry','popup','color']]
        geojson = data.to_json()
        
    return geojson

@st.cache_data(show_spinner=False)
def reporteHtml(dataproyectos=pd.DataFrame(),dataformulada=pd.DataFrame(),datapricing=pd.DataFrame(),mapwidth=1280,mapheight=200):
            
    #-------------------------------------------------------------------------#
    # Fix data
    if not datapricing.empty and not dataproyectos.empty:
        datamerge   = dataproyectos.drop_duplicates(subset=['codproyecto','tipo'],keep='first')
        datapricing = datapricing.merge(datamerge[['codproyecto','tipo']],on='codproyecto',how='left',validate='m:1')

        valormin    = 3000000
        valormax    = 50000000
        idd         = (datapricing['tipo'].astype(str).str.lower().str.contains('apt')) & ((datapricing['valormt2']<valormin) | (datapricing['valormt2']>valormax))
        datapricing = datapricing[~idd]

        datamerge         = datapricing.groupby(['codproyecto'])['valormt2'].max().reset_index()
        datamerge.columns = ['codproyecto','valormt2']
        dataproyectos     = dataproyectos.merge(datamerge,on='codproyecto',how='left',validate='m:1')

    #-------------------------------------------------------------------------#
    # Header
    html_header = ""
    if not dataproyectos.empty:
        formato = [{'texto':'Total proyectos','value':int(len(dataproyectos))},
                           {'texto':'Proyectos en construcción o preventa','value':int(len(dataproyectos[dataproyectos['estado'].isin(['Const', 'Prev'])]))}]

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

    html_pricing = ""
    if not datapricing.empty:
        df          = datapricing.copy()
        df['fecha'] = pd.to_datetime(df['fecha'])
        #df          = df.resample('Y', on='fecha').valormt2.mean().reset_index()
        df          = df.resample('Y', on='fecha').valormt2.max().reset_index()
        df['year']  = df['fecha'].apply(lambda x: x.year)
        df.columns  = ['fecha','valormt2','year']
        df          = df[df['year']==datetime.now().year]
        if not df.empty:
            html_pricing = f"""
            <div class="row">
                <div class="col-12 col-md-12 mb-3">
                    <div class="card card-stats card-round">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col col-stats ms-3 ms-sm-0">
                                    <div class="numbers">
                                        <h4 class="card-title">${df['valormt2'].iloc[0]:,.0f}</h4>
                                        <p class="card-category">Precio referencia por mt2</p>
                                        <p class="card-category" style="font-size: 0.6rem;">(proyectos nuevos en {datetime.now().year})</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
    #-------------------------------------------------------------------------#
    # Estado y Precios
    html_estado  = ""
    html_grafica = ""
    if not dataproyectos.empty and 'estado' in dataproyectos:
        df          = dataproyectos.copy()
        df          = df.groupby('estado')['id'].count().reset_index()
        df.columns  = ['estado','conteo']
        df['color'] = df['estado'].replace(['Term', 'Desist', 'Const', 'Prev'],['#5CE092','#E07C5C','#E0BF5C','#5C9AE0'])
        df['tipoestado'] =  df['estado'].replace(['Term','Desist','Const','Prev'],['Terminado','Desistido','Construcción','Preventas'])
        idd = df['color'].astype(str).str.contains('#')
        if sum(~idd)>0:
            df.loc[~idd,'color'] = '#808080'
            
        titulo = 'Proyectos por estado'
        fig    = px.bar(df, x='tipoestado', y="conteo", text="conteo", title=titulo)
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
            'width':int(mapwidth*0.6*0.4),
            'margin':dict(l=0, r=0, t=30, b=20),
        })    
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(size=8,color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'),type='log')

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
    if not dataproyectos.empty and not datapricing.empty:
        df          = datapricing.copy()
        df['fecha'] = pd.to_datetime(df['fecha'])
        #df         = df.resample('Y', on='fecha').valormt2.median().reset_index()
        df          = df.resample('Y', on='fecha').valormt2.max().reset_index()
        df['year']  = df['fecha'].apply(lambda x: x.year)
        df.columns  = ['fecha','valormt2','year']
        df          = df[df['year']>=2020]
        df.index = range(len(df))
        if not df.empty:
            
            titulo = 'Precio por mt2'
            fig    = px.bar(df, x='year', y="valormt2", text="valormt2", title=titulo)
            fig.update_traces(texttemplate='$%{y:,.0f}', textposition='inside', textfont=dict(color='white'),marker_color='#624CAB')
            fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_xaxes(tickmode='linear', dtick=1)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'title_font':dict(color='black'),
                'legend':dict(bgcolor='black'),
                'height':int(mapheight), 
                'width':int(mapwidth*0.6*0.4),
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
        
    if html_grafica!="":
        html_estado = f"""
        <div class="row" style="margin-top:20px;">
            {html_grafica}
        </div>
        """
    #-------------------------------------------------------------------------#
    # Entregas
    html_entrega = ""
    html_grafica = ""
    if not dataproyectos.empty:
        df1                 = dataproyectos.copy()
        df1['fecha_inicio'] = pd.to_datetime(df1['fecha_inicio'])
        df1                 = df1.resample('Y', on='fecha_inicio').id.count().reset_index()
        df1['year']         = df1['fecha_inicio'].apply(lambda x: x.year)
        df1.columns         = ['fecha_inicio','inicio','year']
       
        df2                  = dataproyectos.copy()
        df2['fecha_entrega'] = pd.to_datetime(df2['fecha_entrega'])
        df2                  = df2.resample('Y', on='fecha_entrega').id.count().reset_index()
        df2['year']          = df2['fecha_entrega'].apply(lambda x: x.year)
        df2.columns          = ['fecha_entrega','entrega','year']
        
        del df1['fecha_inicio']
        del df2['fecha_entrega']
        df       = df1.merge(df2,how='outer')
        df       = df[df['year']>=max(2000,df[df['inicio']>0]['year'].min())]
        df.index = range(len(df))
        
        if not df.empty:
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df['year'],y=df['inicio'],name='Proyectos iniciados',marker_color='#7189FF',offsetgroup=0,width=0.4,showlegend=True,text=df['inicio'],texttemplate='%{text}',textposition='inside',textangle=0,textfont=dict(color='white')),secondary_y=False)
            fig.add_trace(go.Bar(x=df['year'],y=df['entrega'],name='Proyectos entregados',marker_color='#624CAB',offsetgroup=1,width=0.4,showlegend=True,text=df['entrega'],texttemplate='%{text}',textposition='inside',textangle=0,textfont=dict(color='white')),secondary_y=True)
            
            fig.update_layout(
                title='Proyectos iniciados y entregados',
                xaxis_title=None,
                yaxis_title=None,
                yaxis2_title=None,
                barmode='group',
                height=int(mapheight), 
                width=int(mapwidth*0.6*0.8),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                margin=dict(l=0, r=0, t=20, b=5),
                legend=dict(orientation='h', yanchor='top',y=-0.2,xanchor='center',x=0.5,bgcolor='white',font=dict(color='black')),
                title_font=dict(size=11,color='black'),
            )
            fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(size=8,color='black'),showgrid=False, zeroline=False,)
            fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'), title_font=dict(color='black'))
            fig.update_yaxes(title=None, secondary_y=True, showgrid=False, zeroline=False, tickfont=dict(color='black'))
            html_fig_paso = fig.to_html(config={'displayModeBar': False})
            try:
                soup = BeautifulSoup(html_fig_paso, 'html.parser')
                soup = soup.find('body')
                soup = str(soup.prettify())
                soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
                html_grafica += f""" 
                <div class="col-12">
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
        html_entrega = f"""
        <div class="row" style="margin-top:20px;">
            {html_grafica}
        </div>
        """
        
    #-------------------------------------------------------------------------#
    # Proyectos y Constructoras
    html_constructora = ""
    html_grafica = ""
    if not dataproyectos.empty:
        df  = dataproyectos.copy()
        df  = df.groupby('proyecto').agg({'valormt2':'first'}).reset_index()
        df.columns  = ['proyecto','valormt2']
        df         = df.sort_values(by=['valormt2'],ascending=False)
        df         = df.iloc[0:4,:]
        
        titulo = 'Proyectos por m²'
        fig = px.bar(df, y='proyecto', x="valormt2", text="valormt2", title=titulo, orientation='h')
        fig.update_traces(texttemplate='%{x:,.0f}', textposition='inside', textfont=dict(color='white'), marker_color='#7189FF')
        fig.update_layout(title_x=0.4, height=350, xaxis_title=None, yaxis_title=None)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'title_font': dict(color='black'),
            'legend': dict(bgcolor='black'),
            'height': int(mapheight), 
            'width': int(mapwidth*0.3),
            'margin': dict(l=100, r=0, t=30, b=20),
        })    
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'))
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
    if not dataproyectos.empty:
        df  = dataproyectos.copy()
        df  = df.groupby('construye')['id'].count().reset_index()
        df.columns  = ['construye','conteo']
        df         = df.sort_values(by=['conteo'],ascending=False)
        df         = df.iloc[0:4,:]
        
        titulo = 'Lista constructores'
        fig = px.bar(df, y='construye', x="conteo", text="conteo", title=titulo, orientation='h')
        fig.update_traces(texttemplate='%{x:,.0f}', textposition='inside', textfont=dict(color='white'), marker_color='#7189FF')
        fig.update_layout(title_x=0.4, height=350, xaxis_title=None, yaxis_title=None)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'title_font': dict(color='black'),
            'legend': dict(bgcolor='black'),
            'height': int(mapheight), 
            'width': int(mapwidth*0.3),
            'margin': dict(l=100, r=0, t=30, b=20),
        })    
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'))
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
    if html_grafica!="":
        html_constructora = f"""
        <div class="row" style="margin-top:20px;">
            {html_grafica}
        </div>
        """
        
    style = stylehtml()
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
            {html_pricing}
            {html_estado}
            {html_entrega}
            {html_constructora}
        </div>
    </body>
    </html>
    """
    return html

@st.cache_data(show_spinner=False)
def tipologiaHtml(dataformulada=pd.DataFrame(),mapwidth=600,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Tiplogias
    html_tipologias = ""
    html_grafica    = ""
    if not dataformulada.empty:
        formato = [{'variable':'habitaciones' ,'titulo':'Habitaciones'},
                  {'variable':'banos','titulo':'Baños'},
                  {'variable':'garajes','titulo':'Garajes'}]
        
        for iiter in formato:
            variable = iiter['variable']
            titulo   = iiter['titulo']
            df         = dataformulada.copy()
            df         = df[df[variable]>0]
            
            if not df.empty:
                df         = df.groupby(variable)['id'].count().reset_index()
                df.columns = ['variable','conteo']
                df         = df.sort_values(by='variable',ascending=True)
                category_order = df['variable'].tolist()
                
                fig = px.pie(df, names="variable", values="conteo", title=titulo,color_discrete_sequence=px.colors.sequential.RdBu[::-1],category_orders={"variable": category_order})
                fig.update_traces(textinfo='percent+label',textfont_color='white',textposition='inside')
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                    'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
                    'height': 200, 
                    'width': int(mapwidth*0.2),
                    'margin': dict(l=20, r=0, t=20, b=0),
                    'title_font': dict(size=11, color='black'),
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
                    soup = soup.replace('<body>', '<div style="width: 100%; height: 100%;margin-bottom: 0px;">').replace('</body>', '</div>')
                    html_grafica += f""" 
                    <div class="col-3">
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
            
        #---------------------------------------------------------------------#
        # Area construida
        df         = dataformulada.copy()
        df['isin'] = 1
        q1         = df.groupby('isin')['areaconstruida'].quantile(0.25).reset_index()
        q1.columns = ['isin','q1']
        q3         = df.groupby('isin')['areaconstruida'].quantile(0.75).reset_index()
        q3.columns = ['isin','q3']
        
        # Remover outliers
        w         = q1.merge(q3,on='isin',how='outer')
        w['iqr']  = w['q3']-w['q1']
        #w['linf'] = w['q1'] - 1.5*w['iqr']
        #w['lsup'] = w['q3'] + 1.5*w['iqr']
        w['linf'] = df['areaconstruida'].min()
        w['lsup'] = df['areaconstruida'].max()
        df        = df.merge(w[['isin','linf','lsup']],on='isin',how='left',validate='m:1')
        df        = df[(df['areaconstruida']>=df['linf']) & (df['areaconstruida']<=df['lsup'])]
        
        w         = df.groupby('isin')['id'].count().reset_index() 
        w.columns = ['isin','count']
        df        = df.merge(w,on='isin',how='left',validate='m:1')
        df        = df[df['count']>2]

        if not df.empty:
            fig = px.box(df,x='isin',y='areaconstruida',title='Área construida',color_discrete_sequence=['#624CAB'])
            fig.update_layout(
                title_x=0.55,
                height=int(mapheight),
                #width=600,
                width=int(mapwidth*0.25),
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=70, r=0, t=20, b=0),
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
                <div class="col-3">
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
        
    style = stylehtml()
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
            {html_tipologias}
        </div>
    </body>
    </html>
    """
    return html

@st.cache_data(show_spinner=False)
def pricingHtml(datapricing=pd.DataFrame(),mapwidth=600,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Pricing
    html_pricing = ""
    html_grafica = ""
    if not datapricing.empty:
        df          = datapricing.copy()
        df          = df[df['fecha'].notnull()]
        df['fecha'] = pd.to_datetime(df['fecha'])
        df          = df.resample('Y', on='fecha').valor_P.max().reset_index()
        df['year']  = df['fecha'].apply(lambda x: x.year)
        df.columns  = ['fecha','precio','year']
        if not df.empty:
            
            titulo = 'Evolución del precio'
            fig    = px.bar(df, x='year', y="precio", text="precio", title=titulo)
            fig.update_traces(texttemplate='$%{y:,.0f}', textposition='inside', textfont=dict(size=10,color='white'),marker_color='#624CAB')
            fig.update_layout(title_x=0.5,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_xaxes(tickmode='linear', dtick=1)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'title_font':dict(color='black'),
                'legend':dict(bgcolor='black'),
                'height':int(mapheight), 
                'width':int(mapwidth*0.28),
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
        
    if html_grafica!="":
        html_pricing = f"""
        <div class="row" >
            {html_grafica}
        </div>
        """
        
    style = stylehtml()
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
            {html_pricing}
        </div>
    </body>
    </html>
    """
    return html

def stylehtml():
    return """
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
    
def style_function_opacity(feature):
    return {
        'fillColor': '#0095ff',
        'color': 'blue',
        'weight': 0,
        'fillOpacity': 0.05,
        #'dashArray': '5, 5'
    }
