import streamlit as st
import pandas as pd
import geopandas as gpd
import pymysql
import folium
import matplotlib.pyplot as plt
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

    with col1:
        tipovariable = st.selectbox('Segmentación del mapa:',options=['# Inmuebles','Precio de venta','Precio de renta'])
        if '# Inmuebles' in tipovariable: tipovariable = 'conteo'
        elif 'Precio de venta' in tipovariable: tipovariable = 'precioventa'
        elif 'Precio de renta' in tipovariable: tipovariable = 'preciorenta'

    with col1:
        with st.spinner('Buscando datos del portfalio'):
            data        = getportafolio()
            dataheatmap = mergegeodata(data.copy(),tipovariable=tipovariable)
            data.index  = range(len(data))
            
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
        df['link'] = df['barmanpre'].apply(lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={x}&vartype=barmanpre&token={st.session_state.token}")

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
                    this.eGui.innerText = 'Link';
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
        # Heat Map
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
            folium.GeoJson(geopoints).add_to(m)

        # Select inmueble
        if isinstance(lista_selected, list) and lista_selected!=[]:
            lista     = [int(x) for x in lista_selected]
            idd       = data.index.isin(lista)
            df        = data[idd]
            geopoints = geopointsdata(df)
            marker    = folium.Marker(icon=folium.Icon(icon='star'))
            folium.GeoJson(geopoints,marker=marker).add_to(m)
        
        with colm2:
            st_map = st_folium(m,width=mapwidth,height=600)
            

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
        datashape = pd.read_sql_query(f"SELECT scacodigo, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_barriocatastro_simplify WHERE {query}" , engine)

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
def data2geopandas(data):
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        if 'color' not in data: data['color'] = '#5A189A'
        for idd,items in data.iterrows():
            
            popuptext = ""
            try:    popuptext += f"""<b>Valor transacciones mt2:</b> ${items['valormt2_transacciones']:,.0f} m²<br>"""
            except: pass
            try:    popuptext += f"""<b>Número de transacciones:</b> {items['transacciones']}<br>"""
            except: pass
            try:
                if isinstance(items['scacodigo'], str) and items['scacodigo']!="":
                    popuptext += f"""<b>Barrio catastral:</b> {items['scacodigo']}<br>"""
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
        data      = data[['geometry']]
        geojson   = data.to_json()
    return geojson

if __name__ == "__main__":
    main()
