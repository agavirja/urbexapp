import streamlit as st
import re
import folium
import pandas as pd
import geopandas as gpd
import plotly.express as px
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,Point,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup

from data.coddir import coddir

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
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'geojson_proyectos_nuevos':None,
               'polygon_proyectos_nuevos':None,
               'zoom_start_proyectos_nuevos':12,
               'latitud_proyectos_nuevos':4.652652, 
               'longitud_proyectos_nuevos':-74.077899,
               'reporte_proyectos_nuevos':False,
               'default':[]
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
        
    #-------------------------------------------------------------------------#
    # Data 
    dataproyectos = pd.DataFrame()
    dataformulada = pd.DataFrame()
    datalong      = pd.DataFrame()
    colm1,colm2,colm3 = st.columns([0.025,0.95,0.025])
    colb1, colb2      = st.columns(2)
    cole1, cole2      = st.columns(2)
    if st.session_state.polygon_proyectos_nuevos is not None:
        with colb1:
            if st.button('Buscar proyectos'):
                st.session_state.reporte_proyectos_nuevos = True
            
    if st.session_state.polygon_proyectos_nuevos is not None and st.session_state.reporte_proyectos_nuevos:
        with st.spinner('Buscando proyectos'):
            dataproyectos,dataformulada,datalong = getdataproyectosnuevos(str(st.session_state.polygon_proyectos_nuevos))
            
    if not dataproyectos.empty and 'estado' in dataproyectos:
        with cole1:
            options = ['Todo']+list(dataproyectos['estado'].unique())
            estado  = st.selectbox('Estaod del proyecto',options=options)
            if 'Todo' not in estado:
                dataproyectos = dataproyectos[dataproyectos['estado'].str.contains(estado)]
                dataformulada = dataformulada[dataformulada['codproyecto'].isin(dataproyectos['codproyecto'])]
                datalong      = datalong[datalong['codproyecto'].isin(dataproyectos['codproyecto'])]

    st.dataframe(dataproyectos)
    st.dataframe(dataformulada)
    st.dataframe(datalong)       
            
    #-------------------------------------------------------------------------#
    # Mapa
    m    = folium.Map(location=[st.session_state.latitud_proyectos_nuevos, st.session_state.longitud_proyectos_nuevos], zoom_start=st.session_state.zoom_start_proyectos_nuevos,tiles="cartodbpositron")
    draw = Draw(
                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                edit_options={"poly": {"allowIntersection": False}}
                )
    draw.add_to(m)

    if not dataproyectos.empty:
        geopoints = point2geopandas(dataproyectos)
        popup   = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geopoints,popup=popup).add_to(m)
            
    if st.session_state.geojson_proyectos_nuevos is not None:
        folium.GeoJson(st.session_state.geojson_proyectos_nuevos, style_function=style_function_color).add_to(m)

    with colm2:
        st_map = st_folium(m,width=mapwidth,height=mapheight)

    if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
        if st_map['all_drawings']!=[]:
            if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                coordenadas                                  = st_map['all_drawings'][0]['geometry']['coordinates']
                st.session_state.polygon_proyectos_nuevos    = Polygon(coordenadas[0])
                st.session_state.geojson_proyectos_nuevos    = mapping(st.session_state.polygon_proyectos_nuevos)
                polygon_shape                                = shape(st.session_state.geojson_proyectos_nuevos)
                centroid                                     = polygon_shape.centroid
                st.session_state.latitud_proyectos_nuevos    = centroid.y
                st.session_state.longitud_proyectos_nuevos   = centroid.x
                st.session_state.zoom_start_proyectos_nuevos = 16
                st.rerun()
                
    #-------------------------------------------------------------------------#
    # Graficas  
    colg1,colg2 = st.columns(2)


    if not dataproyectos.empty:
        with colg1:
            html = htmltable(data=dataproyectos.copy())
            st.components.v1.html(html,height=300,scrolling=True)


        df = dataproyectos.copy()
        df['year'] = df['fecha_inicio'].apply(lambda x: x.year)
        
        df = df.groupby('year').agg({'codproyecto':'count'}).reset_index()
        df.columns = ['year','count']
        df.index = range(len(df))
        if not df.empty:
            fig = px.bar(df, x="year", y="count", text="count", title='Proyectos iniciados')
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_xaxes(tickmode='linear', dtick=1)
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
                'legend':dict(bgcolor='black'),
            })    
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with colg2:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
            
            
        
@st.cache_data(show_spinner=False)
def getdataproyectosnuevos(polygon):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datalatlng    = pd.DataFrame()
    dataproyectos = pd.DataFrame()
    dataformulada = pd.DataFrame()
    datalong      = pd.DataFrame()
    
    query = ""
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
        
    if query!="":
        query = query.strip().strip('AND')
        datalatlng  = pd.read_sql_query(f"SELECT codproyecto,latitud,longitud FROM  bigdata.data_bogota_gi_nueva_latlng WHERE {query}" , engine)
        
    if not datalatlng.empty:
        lista = "','".join(datalatlng['codproyecto'].astype(str).unique())
        query = f" codproyecto IN ('{lista}')"
        dataproyectos  = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_proyectos WHERE {query}" , engine)
        if not dataproyectos.empty:
            datamerge     = datalatlng.drop_duplicates(subset='codproyecto',keep='first')
            dataproyectos = dataproyectos.merge(datamerge,on='codproyecto',how='left',validate='m:1')
            for i in ['estado','tipo','tipo_vivienda']:
                if i in dataproyectos: 
                    dataproyectos[i] = dataproyectos[i].apply(lambda x: formatovariables(x))
            dataproyectos['estado'] = dataproyectos['estado'].apply(lambda x: x.split(',')[-1])
            
            
        dataformulada = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_formulada WHERE {query}" , engine)
        datalong      = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_long WHERE {query}" , engine)
    
    #-------------------------------------------------------------------------#
    # Merge direccion/barmanpre
    if not dataproyectos.empty:
        dataproyectos['coddir'] = dataproyectos['direccion'].apply(lambda x: coddir(x))
        
        lista = "','".join(dataproyectos['coddir'].astype(str).unique())
        query = f" coddir IN ('{lista}')"
        
        datacatastro = pd.read_sql_query(f"SELECT coddir,barmanpre FROM bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            datamerge     = datacatastro.drop_duplicates(subset='coddir',keep='first')
            dataproyectos = dataproyectos.merge(datamerge,on='coddir',how='left',validate='m:1')
        
        if 'barmanpre' in dataproyectos and sum(dataproyectos['barmanpre'].isnull())>0:
            lista = []
            for palabras in dataproyectos['proyecto'].unique():
                for palabra in palabras.split(' '):
                    if len(palabra) >= 3:
                        lista.append(palabra)
            if lista!=[]:
                lista         = "','".join(lista)
                query         = f" nombre_conjunto IN ('{lista}')"
                dataconjuntos = pd.read_sql_query(f"SELECT coddir,nombre_conjunto as proyectonew FROM bigdata.bogota_nombre_conjuntos WHERE {query}" , engine)
                if not dataconjuntos.empty:
                    lista        = "','".join(dataconjuntos['coddir'].astype(str).unique())
                    query        = f" coddir IN ('{lista}')"
                    datacatastro = pd.read_sql_query(f"SELECT coddir,barmanpre as barmanprenew FROM bigdata.data_bogota_catastro WHERE {query}" , engine)
                    if not datacatastro.empty:
                        datamerge     = datacatastro.drop_duplicates(subset='coddir',keep='first')
                        dataconjuntos = dataconjuntos.merge(datamerge,on='coddir',how='left',validate='m:1')
                        dataconjuntos = dataconjuntos[dataconjuntos['barmanprenew'].notnull()]
            if not dataconjuntos.empty and 'barmanprenew' in dataconjuntos:
                datamerge                    = dataconjuntos.drop_duplicates(subset='proyectonew',keep='first')
                datamerge['proyectonew']     = datamerge['proyectonew'].astype(str).str.lower()
                dataproyectos['proyectonew'] = dataproyectos['proyecto'].astype(str).str.lower()
                dataproyectos                = dataproyectos.merge(datamerge[['proyectonew','barmanprenew']],on='proyectonew',how='left',validate='m:1')
                if 'barmanprenew' in dataproyectos:
                    idd = (dataproyectos['barmanpre'].isnull()) & (dataproyectos['barmanprenew'].notnull())
                    if sum(idd)>0:
                        dataproyectos.loc[idd,'barmanpre'] = dataproyectos.loc[idd,'barmanprenew']
                variables = [x for x in ['barmanprenew','proyectonew'] if x in dataproyectos]
                if variables!=[]: dataproyectos.drop(columns=variables,inplace=True)

    return dataproyectos,dataformulada,datalong
        
@st.cache_data(show_spinner=False)
def point2geopandas(data):
    
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A'
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
                        <a href="http://www.urbex.com.co/Proyectos_nuevos?code={items['codproyecto']}&token={st.session_state.token}" target="_blank" style="color: black;">
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
     
def htmltable(data=pd.DataFrame()):
    tablaresumen = ""
    #---------------------------------------------------------------------#
    # Seccion ubicacion
    if not data.empty:

        #precioventa = f"${data['precioventa'].median():,.0f}" if 'precioventa' in data and sum(data['precioventa']>0)>0 else 'Sin información'
        #preciorenta = f"${data['preciorenta'].median():,.0f}" if 'preciorenta' in data and sum(data['preciorenta']>0)>0 else 'Sin información'
        formato     = [
            {'variable':'# de proyectos','value':len(data)},
            #{'variable':'Precio de venta promedio ','value':precioventa},
            #{'variable':'Precio de venta promedio por m²','value':precioventamt2},
            ]
        
        html_paso = ""
        for i in formato: 
            key  = i['variable']
            value = i['value']
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            labeltable     = "Resumen:"
            tablaresumen = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablaresumen = f"""<div class="col-md-12"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaresumen}</tbody></table></div></div>"""
            
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

def formatovariables(x):
    try:
        return ','.join([re.sub('[^a-zA-Z]','',w) for w in x.strip('/').split('/')])
    except: 
        return x
            
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }      
if __name__ == "__main__":
    main()
