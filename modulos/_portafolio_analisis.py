import streamlit as st
import pandas as pd
import geopandas as gpd
import pymysql
import folium
import matplotlib.pyplot as plt
import plotly.express as px
from matplotlib.colors import to_hex
from streamlit_folium import st_folium
from sqlalchemy import create_engine 
from datetime import datetime
from shapely.geometry import Point
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode, AgGridTheme
from st_aggrid.shared import JsCode
from streamlit_js_eval import streamlit_js_eval

from data.getdatafrom_chip_matricula import main as mergegeoinfo

from display.stylefunctions  import style_function_geojson

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
               'index':None,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Subir portafolio de inmuebles")
        if uploaded_file:
            dataupload = pd.read_excel(uploaded_file)
            if st.button('Guardar datos'):
                with st.spinner('Guardando datos'):
                    uploadportafolio(dataupload)
        st.write('')
        st.write('')
        st.write('')
                    
    with col2:
        st.write('')
        st.write('')
        st.write('')
        plantilla = pd.DataFrame({'ciudad': ['bogota', 'bogota', 'bogota', 'bogota'], 'matricula': [None, None, '050C01304860', '050C01141309'], 'chip': ['AAA0218YARJ', 'AAA0000AALW', None, None], 'direccion': ['KR 19A 103A 62', 'KR 73A BIS 25C 39', None, None], 'precioventa': [890000000, 750000000, 685000000, None], 'preciorenta': [4500000, None, None, 4120000]})
        csv       = convert_df(plantilla)
        st.download_button(
            label="Descargar Plantilla",
            data=csv,
            file_name='plantilla.csv',
            mime='text/csv',
        )

    col1, col2 = st.columns(2)
    tipovariable = 'conteo'
    #with col1:
    #    tipovariable = st.selectbox('Segmentación del mapa:',options=['# Inmuebles','Precio de venta','Precio de renta'])
    #    if '# Inmuebles' in tipovariable: tipovariable = 'conteo'
    #    elif 'Precio de venta' in tipovariable: tipovariable = 'precioventa'
    #    elif 'Precio de renta' in tipovariable: tipovariable = 'preciorenta'

    with col1:
        with st.spinner('Buscando datos del portfalio'):
            data        = getportafolio()
            dataheatmap = mergegeodata(data.copy(),tipovariable=tipovariable)
            data.index  = range(len(data))
            data        = matchdata(data)
    
    col1, col2 = st.columns(2)
    if not dataheatmap.empty:
        with col1:
            options = list(dataheatmap['scanombre'].unique())
            options = ['Todos'] + options
            barrio  = st.selectbox('Filtro de barrio:',options=options)
            if 'todo' not in barrio.lower():
                dataheatmap = dataheatmap[dataheatmap['scanombre']==barrio]
                data        = data[data['scacodigo'].isin(dataheatmap['scacodigo'])]
                
    lista_selected = []
    #-------------------------------------------------------------------------#
    # Merge barrios
    if not data.empty:
        colm1,colm2,colm3 = st.columns([0.025,0.95,0.025])
        cold1,cold2,cold3 = st.columns([0.025,0.95,0.025])

        #-------------------------------------------------------------------------#
        # Tabla de datos
        #-------------------------------------------------------------------------#
        df         = data.copy()
        df['link'] = df['barmanpre'].apply(lambda x: f"http://localhost:8501/Busqueda_avanzada?type=predio&code={x}&vartype=barmanpre&token={st.session_state.token}")

        df        = df.sort_values(by='fecha_creacion',ascending=False)
        df['id']  = range(len(df))
        variables = ['id','ciudad','matricula','chip','predirecc','precioventa','preciorenta','link']
        df        = df[[x for x in variables if x in df]]
        df.rename(columns={'ciudad':'Ciudad','matricula':'Matrícula','chip':'Chip','predirecc':'Dirección','precioventa':'Precio de venta','preciorenta':'Precio de renta'},inplace=True)
        
        gb = GridOptionsBuilder.from_dataframe(df,editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        cell_renderer =  JsCode("""function(params) {return `<a href=${params.value} target="_blank">${params.value}</a>`}""")
        
        gb.configure_column(
            "link",
            headerName="link",
            width=100,
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
    
        with cold2:
            response = AgGrid(df,
                        gridOptions=gb.build(),
                        columns_auto_size_mode="FIT_CONTENTS",
                        theme=AgGridTheme.STREAMLIT,
                        updateMode=GridUpdateMode.VALUE_CHANGED,
                        allow_unsafe_jscode=True)
        
            df = pd.DataFrame(response['selected_rows'])
            if not df.empty:
                lista_selected = df.index.to_list()
            
        #-------------------------------------------------------------------------#
        # Mapa
        #-------------------------------------------------------------------------#
        m = folium.Map(location=[4.652652, -74.077899], zoom_start=12,tiles="cartodbpositron") #"cartodbdark_matter"

        if not dataheatmap.empty:
            geojson = data2geopandas(dataheatmap)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
        
        # Markers
        if 'latitud' in data and 'longitud' in data:
            lista     = [int(x) for x in lista_selected]
            idd       = data.index.isin(lista)
            df        = data[~idd]
            geopoints = geopointsdata(df)
            folium.GeoJson(geopoints,style_function=style_function_geojson).add_to(m)

        # Select inmueble
        if isinstance(lista_selected, list) and lista_selected!=[]:
            lista     = [int(x) for x in lista_selected]
            idd       = data.index.isin(lista)
            df        = data[idd]
            geopoints = geopointsdata(df)
            marker    = folium.Marker(icon=folium.Icon(icon='star'))
            folium.GeoJson(geopoints,style_function=style_function_geojson,marker=marker).add_to(m)
        
        with colm2:
            st_map = st_folium(m,width=mapwidth,height=600)
            
    #-------------------------------------------------------------------------#
    # Exportar data
    #-------------------------------------------------------------------------#
    if not data.empty:
        dataexport = data.copy()
        variables = [x for x in ['id','token','barmanpre','direccion','mpio_ccdgo','scacodigo','localidad','fecha_creacion','fecha_actualizacion','activo','precuso','precdestin',] if x in dataexport]
        if variables!=[]:
            dataexport.drop(columns=variables,inplace=True)
        for i in ['latitud', 'longitud', 'precioventa', 'preciorenta', 'preaconst', 'preaterre', 'prevetustz', 'estrato', 'predios_precuso', 'preaconst_precuso', 'preaterre_precuso', 'preaconst_total', 'preaterre_total', 'connpisos', 'connsotano', 'avaluomt2', 'predialmt2', 'valormt2_transacciones', 'transacciones','impuesto_predial','avaluo_catastral']:
            if i in dataexport: dataexport[i] = pd.to_numeric(dataexport[i],errors='coerce')
        dataexport.rename(columns={'ciudad': 'Ciudad', 'matricula': 'Matricula', 'chip': 'Chip', 'predirecc': 'Predirecc', 'latitud': 'Latitud', 'longitud': 'Longitud', 'barrio': 'Barrio', 'precioventa': 'Precio de venta', 'preciorenta': 'Precio de renta', 'preaconst': 'Area privada', 'preaterre': 'Area de terreno', 'prevetustz': 'Antiguedad', 'preusoph': 'PH', 'estrato': 'Estrato', 'predios_precuso': '# Predios del mismo uso ', 'preaconst_precuso': 'Area privada de predios del mismo uso', 'preaterre_precuso': 'Area de terreno de predios del mismo uso', 'preaconst_total': 'Area construida total en el terreno', 'preaterre_total': 'Area total del terreno', 'connpisos': '# Pisos', 'connsotano': 'Sotanos', 'nombre_conjunto': 'Nombre copropiedad', 'avaluomt2': 'Avaluo Catastral mt2', 'predialmt2': 'Predial mt2', 'valormt2_transacciones': 'Valor mt2 de Transacciones de los ultimos 12 meses', 'transacciones': '# de Transacciones','impuesto_predial':'Predial','avaluo_catastral':'Avaluo catastral'},inplace=True)
        col1,col2,col3 = st.columns([0.7,0.2,0.1])
        with col2:
            st.write('')
            st.write('')
            if st.button('Descargar Excel Completo'):
                download_excel(dataexport)

    #-------------------------------------------------------------------------#
    # Estadisticas
    #-------------------------------------------------------------------------#
    col1,col2 = st.columns(2)
    if not data.empty:
        with col1:
            html = htmltable(data=data.copy())
            st.components.v1.html(html,height=300,scrolling=True)

    if not data.empty:

        # Numeor de inmuebles por barrio
        df = data.groupby(['barrio'])['id'].count().reset_index()
        df.columns = ['variable','value']
        df = df.sort_values(by=['value','variable'],ascending=[False,True])
        if not df.empty and len(df)>1:
            fig = px.bar(df, x="variable", y="value", text="variable", title='# de activos por barrio')
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })    
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with col2:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")

        col1,col2 = st.columns(2)
        if 'precioventa' in data:
            df = data.copy()
            df = df[df['precioventa']>0]
            if not df.empty and len(df)>1:
                fig = px.box(df,y='precioventa',title='Distribución del precio de venta los inmuebles',color_discrete_sequence=['#68c8ed'])
                fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                with col1:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
        if 'preciorenta' in data:
            df = data.copy()
            df = df[df['preciorenta']>0]
            if not df.empty and len(df)>1:
                fig = px.box(df,y='preciorenta',title='Distribución del precio de renta de los inmuebles',color_discrete_sequence=['#68c8ed'])
                fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                with col2:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                    
        col1,col2 = st.columns(2)
        if 'preaconst' in data:
            df = data.copy()
            df = df[df['preaconst']>0]
            if not df.empty and len(df)>1:
                fig = px.box(df,y='preaconst',title='Distribución del área privada de los inmuebles',color_discrete_sequence=['#68c8ed'])
                fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                with col1:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
        if 'prevetustz' in data:
            df = data.copy()
            df = df[df['prevetustz']>0]
            if not df.empty and len(df)>1:
                fig = px.box(df,y='prevetustz',title='Distribución de la antgiuedad de los inmuebles',color_discrete_sequence=['#68c8ed'])
                fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                with col2:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
                
@st.cache_data(show_spinner=False)
def mergegeodata(data,tipovariable='conteo'):
    if not data.empty and 'scacodigo' in data:
        data      = datagroupby(data,tipovariable=tipovariable)
        user      = st.secrets["user_bigdata"]
        password  = st.secrets["password_bigdata"]
        host      = st.secrets["host_bigdata"]
        schema    = 'urbex'
        engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

        lista     = "','".join(data['scacodigo'].astype(str).unique())
        query     = f" scacodigo IN ('{lista}')"
        datashape = pd.read_sql_query(f"SELECT scacodigo,scanombre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_barriocatastro_simplify WHERE {query}" , engine)

        if not datashape.empty:
            datamerge = datashape.drop_duplicates(subset='scacodigo',keep='first')
            data      = data.merge(datamerge,on='scacodigo',how='left',validate='m:1')
    return data

@st.cache_data(show_spinner=False)
def datagroupby(data,tipovariable='conteo'):
    if 'conteo' in tipovariable.lower():
        data = data.groupby('scacodigo')['chip'].count().reset_index()
        data.columns = ['scacodigo','variable']
    elif 'precioventa' in tipovariable.lower() and 'precioventa' in data:
        data = data.groupby('scacodigo')['precioventa'].median().reset_index()
        data.columns = ['scacodigo','variable']
    elif 'preciorenta' in tipovariable.lower() and 'preciorenta' in data:
        data = data.groupby('scacodigo')['preciorenta'].median().reset_index()
        data.columns = ['scacodigo','variable']
    try:
        data['normvalue'] = data['variable'].rank(pct=True)
        cmap              = plt.cm.RdYlGn # plt.cm.viridis
        data['color']     = data['normvalue'].apply(lambda x: to_hex(cmap(x)))
        data.drop(columns=['normvalue'],inplace=True)
    except: pass
    return data
        
@st.cache_data(show_spinner=False)
def uploadportafolio(data):
    
    if not data.empty and isinstance(st.session_state.token, str) and st.session_state.token!='':
        data      = mergegeoinfo(data)
        user      = st.secrets["user_bigdata"]
        password  = st.secrets["password_bigdata"]
        host      = st.secrets["host_bigdata"]
        schema    = 'urbex'
        engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        
        datastock = pd.read_sql_query(f"SELECT * FROM urbex.portafolio WHERE token='{st.session_state.token}'" , engine)
        datanames = pd.read_sql_query("SELECT * FROM urbex.portafolio LIMIT 1" , engine)
        
        # Data Nueva
        datacompleta = data.copy()
        idd  = (data['matricula'].isin(datastock['matricula'])) | (data['chip'].isin(datastock['chip']))
        data = data[~idd]
        
        if not data.empty:
            variables = [x for x in list(datanames) if x in data]
            data      = data[variables]
            data['token']               = st.session_state.token
            data['fecha_creacion']      = datetime.now().strftime('%Y-%m-%d')
            data['fecha_actualizacion'] = datetime.now().strftime('%Y-%m-%d')
            data['activo']              = 1
            data.to_sql('portafolio', engine, if_exists='append', index=False, chunksize=100)
        engine.dispose()
            
        # Data ya existente
        data = datacompleta[idd]
        data = data[data['chip'].notnull()]
        if not data.empty and 'chip' in data:
            data['token']               = st.session_state.token
            data['fecha_actualizacion'] = datetime.now().strftime('%Y-%m-%d')
            for i in ['precioventa','preciorenta']:
                if i not in data: 
                    data[i] = None
                else:
                    data[i] = pd.to_numeric(data[i],errors='coerce')
                
            variables = [x for x in ['precioventa','preciorenta','fecha_actualizacion','chip','token'] if x in data]
            df        = data[variables]
            df        = df.fillna(0)
            conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=schema)
            with conn.cursor() as cursor:
                sql = "UPDATE urbex.portafolio SET precioventa=%s, preciorenta=%s,fecha_actualizacion=%s WHERE chip=%s AND token=%s "
                list_of_tuples = df.to_records(index=False).tolist()
                cursor.executemany(sql, list_of_tuples)
            conn.commit()
            try:
                with conn.cursor() as cursor:
                    sql = "UPDATE urbex.portafolio SET precioventa = CASE WHEN precioventa = 0 THEN NULL ELSE precioventa END, preciorenta = CASE WHEN preciorenta = 0 THEN NULL ELSE preciorenta END WHERE precioventa = 0 OR preciorenta = 0;"
                    cursor.execute(sql)
                conn.commit()
            except: pass
            conn.close() 
        st.cache_data.clear()
        st.rerun()

@st.cache_data(show_spinner=False)
def getportafolio():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata"]
    schema   = 'urbex'
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"SELECT * FROM urbex.portafolio WHERE token='{st.session_state.token}'" , engine)
    engine.dispose()
    return data
       
@st.cache_data(show_spinner=False)
def matchdata(data):
    if not data.empty:
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

        datasearch = pd.DataFrame()
        datachip   = pd.DataFrame()
        
        #---------------------------------------------------------------------#
        # Data General Barmanpre
        query = ""
        if 'barmanpre' in data:
            datapaso = data[data['barmanpre'].notnull()]
            if not datapaso.empty:
                lista = "','".join(datapaso['barmanpre'].unique())
                query = f" barmanpre IN ('{lista}')"

        if query!="":
            datasearch = pd.read_sql_query(f"SELECT barmanpre,precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst as preaconst_total,preaterre as preaterre_total, connpisos, connsotano, nombre_conjunto, avaluomt2, predialmt2,valormt2_transacciones,transacciones FROM {schema}.bogota_barmanpre_general WHERE {query}" , engine)
        
        #---------------------------------------------------------------------#
        # Data Chip
        query = ""
        if 'chip' in data:
            datapaso = data[data['chip'].notnull()]
            if not datapaso.empty:
                lista = "','".join(datapaso['chip'].unique())
                query = f" chip IN ('{lista}')"
                
        if query!="":
            datachip = pd.read_sql_query(f"SELECT chip,impuesto_predial,avaluo_catastral FROM {schema}.data_bogota_shd_2024 WHERE {query}" , engine)
            
        if not datasearch.empty:
            datamerge = datasearch.drop_duplicates(subset=['barmanpre','precuso'],keep='first')
            data      = data.merge(datamerge,on=['barmanpre','precuso'],how='left',validate='m:1')
            
        if not datachip.empty:
            datamerge = datachip.drop_duplicates(subset=['chip'],keep='first')
            data      = data.merge(datamerge,on=['chip'],how='left',validate='m:1')
            
        engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def data2geopandas(data):
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        
        data['color']    = '#A16CFF'
        if 'color' not in data: data['color'] = '#5A189A'
        for idd,items in data.iterrows():
            
            popuptext = ""
            try:
                if isinstance(items['scacodigo'], str) and items['scacodigo']!="":
                    popuptext += f"""<b>Barrio catastral:</b> {items['scanombre']}<br>"""
            except: pass
            try:    popuptext += f"""<b># Inmuebles:</b> {items['variable']}<br>"""
            except: pass
        
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                    {popuptext}
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson 

@st.cache_data(show_spinner=False)
def geopointsdata(data):
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data             = data[['geometry']]
        data['color']    = '#A16CFF'
        geojson          = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def download_excel(df):
    excel_file = df.to_excel('data_completa.xlsx', index=False)
    with open('data_completa.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Haz clic aquí para descargar",
        data=data,
        file_name='data_completa.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
def htmltable(data=pd.DataFrame()):
    
    tablaresumen = ""
    #---------------------------------------------------------------------#
    # Seccion ubicacion
    if not data.empty:
        
        precioventamt2 = 'Sin información'
        idd            = (data['precioventa'].notnull()) & (data['preaconst'].notnull())
        if sum(idd)>0: 
            precioventamt2 = data[idd]['precioventa']/data[idd]['preaconst']
            precioventamt2 = f"${precioventamt2.median():,.0f}" 
        
        preciorentamt2 = 'Sin información'
        idd            = (data['preciorenta'].notnull()) & (data['preaconst'].notnull())
        if sum(idd)>0: 
            preciorentamt2 = data[idd]['preciorenta']/data[idd]['preaconst']
            preciorentamt2 = f"${preciorentamt2.median():,.0f}" 
        
        precioventa = f"${data['precioventa'].median():,.0f}" if 'precioventa' in data and sum(data['precioventa']>0)>0 else 'Sin información'
        preciorenta = f"${data['preciorenta'].median():,.0f}" if 'preciorenta' in data and sum(data['preciorenta']>0)>0 else 'Sin información'
        formato     = [
            {'variable':'# de inmuebles','value':len(data)},
            {'variable':'Precio de venta promedio ','value':precioventa},
            {'variable':'Precio de venta promedio por m²','value':precioventamt2},
            {'variable':'Precio de renta promedio','value':preciorenta},
            {'variable':'Precio de renta promedio por m²','value':preciorentamt2},         
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

if __name__ == "__main__":
    main()