import streamlit as st
import pandas as pd
import geopandas as gpd
import pymysql
import folium
import plotly.express as px
from bs4 import BeautifulSoup
from streamlit_folium import st_folium
from sqlalchemy import create_engine 
from datetime import datetime, timedelta
from shapely.geometry import Point
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, AgGridTheme
from st_aggrid.shared import JsCode
from streamlit_js_eval import streamlit_js_eval

from data.getdatafrom_chip_matricula import main as mergegeoinfo
from data.lastTransacciones import main as lastTransacciones
from data.getpropertiesbyID import completeInfoAvaluo
from data.getuso_destino import usosuelo_class

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
               'datatest':pd.DataFrame(),
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    #-------------------------------------------------------------------------#
    # Subir data
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Subir portafolio de inmuebles")
        if uploaded_file:
            dataupload = pd.read_excel(uploaded_file)
            if st.button('Guardar datos'):
                with st.spinner('Guardando datos'):
                    uploadportafolio(dataupload)
                    st.rerun()

        st.write('')
        st.write('')
        st.write('')
        
    with col2:
        st.write('')
        st.write('')
        st.write('')
        plantilla = pd.DataFrame({'matricula': ['050C01304860', '050C01141309' ,'50N-20509663',None], 'chip': [None,None, None,'AAA0000AALW'], 'precioventa': [890000000, 750000000, None, 800000000], 'preciorenta': [4500000, None, None, 4120000], 'fecha_vencimiento_contrato': ['2024-08-25', None, None, '2024-09-01'],'fecha_publicacion':['2024-05-30', '2024-06-15', '2024-02-20', '2023-09-05']})
        csv       = convert_df(plantilla)
        st.download_button(
            label="Descargar Plantilla",
            data=csv,
            file_name='plantilla.csv',
            mime='text/csv',
        )

    #-------------------------------------------------------------------------#
    # Lectura de datos

    with st.spinner('Buscando datos del portfalio'):
        
        data = getportafolio(st.session_state.token)
        if data.empty:
            with col1:
                if st.button('Datos de prueba'):
                    st.session_state.datatest = getportafolio('bb256274fd474aeadbe67b9f4a59b703')
        if data.empty and not st.session_state.datatest.empty:
            data = st.session_state.datatest.copy()
            
        #---------------------------------------------------------------------#
        # Informacion de lotes
        datalotes = datawkt(data)
    
        #---------------------------------------------------------------------#
        # Completar informacion
        data = completarInfo(data)

        #---------------------------------------------------------------------#
        # Reporte
        if not data.empty:
            reporte(data=data,datalotes=datalotes,mapwidth=1600)
    

        # Grafica de valor de transacciones 
        # Arreglar la grafica de los barrios
        # seleccionar un inmueble para sacarlo de la bbdd (activo False)
@st.cache_data(show_spinner=False)
def completarInfo(data):
    #---------------------------------------------------------------------#
    # Datos de la ultima transaccion
    if not data.empty and 'chip' in data:
        chip = list(data['chip'].unique())
        datatransacciones,_du = lastTransacciones(chip=chip)
        
        if not datatransacciones.empty: 
            datatransacciones = datatransacciones.sort_values(by=['prechip','fecha_documento_publico'],ascending=False)
            datamerge         = datatransacciones.drop_duplicates(subset='prechip',keep='first')
            datamerge.rename(columns={'prechip':'chip','fecha_documento_publico':'fecha_ultima_transaccion'},inplace=True)
            data = data.merge(datamerge[['chip','fecha_ultima_transaccion','cuantia']],on='chip',how='left',validate='m:1')
      
    #---------------------------------------------------------------------#
    # Datos de los avaluos catastrales
    if not data.empty and 'chip' in data:
        chip      = list(data['chip'].unique())
        datavaluo = completeInfoAvaluo(chip)
        
        if not datavaluo.empty:
            datamerge = datavaluo.groupby('prechip').agg({'avaluo_catastral':'max','impuesto_ajustado':'max'}).reset_index()
            datamerge.columns = ['prechip','avaluo_catastral','impuesto_ajustado']
            datamerge.rename(columns={'prechip':'chip'},inplace=True)
            data = data.merge(datamerge,on='chip',how='left',validate='m:1')

    #---------------------------------------------------------------------#
    # Dias para finalizar el contrato   
    if not data.empty and 'fecha_vencimiento_contrato' in data:
        data['fecha_vencimiento_contrato'] = pd.to_datetime(data['fecha_vencimiento_contrato'])
        data['diasvencimiento'] = data['fecha_vencimiento_contrato'].apply(lambda x: x-datetime.now())
        data['diasvencimiento'] = data['diasvencimiento'].apply(lambda x: x.days)

    #---------------------------------------------------------------------#
    # Dias de publicacion 
    if not data.empty and 'fecha_publicacion' in data:
        data['fecha_publicacion'] = pd.to_datetime(data['fecha_publicacion'])
        data['diaspublicacion'] = data['fecha_publicacion'].apply(lambda x: datetime.now()-x)
        data['diaspublicacion'] = data['diaspublicacion'].apply(lambda x: x.days)

    #---------------------------------------------------------------------#
    # Tipo de inmueble
    if not data.empty and 'precuso' in data:
        datausosuelo = usosuelo_class()
        data         = data.merge(datausosuelo,on='precuso',how='left',validate='m:1')
        
    #---------------------------------------------------------------------#
    # Uso del suelo
    #from data.getuso_destino import getuso_destino
    #if not data.empty and 'precuso' in data:
    #    dataprecuso,dataprecdestin = getuso_destino()
    #    dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
    #    data = data.merge(dataprecuso,on='precuso',how='left',validate='m:1')
   
    return data
            
       
@st.cache_data(show_spinner=False)
def uploadportafolio(data):
    
    if not data.empty and isinstance(st.session_state.token, str) and st.session_state.token!='':
        
        for i in ['fecha_vencimiento_contrato','fecha_publicacion']:
            if i in data:
                try:
                    data[i] = pd.to_datetime(data[i])
                    data[i] = data[i].dt.strftime('%Y-%m-%d')
                except: pass
            
        
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
                
            variables = [x for x in ['precioventa','preciorenta','fecha_actualizacion','fecha_vencimiento_contrato','fecha_publicacion','chip','token'] if x in data]
            df        = data[variables]
            df        = df.fillna(0)
            conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=schema)
            with conn.cursor() as cursor:
                sql = "UPDATE urbex.portafolio SET precioventa=%s, preciorenta=%s,fecha_actualizacion=%s,fecha_vencimiento_contrato=%s,fecha_publicacion=%s WHERE chip=%s AND token=%s "
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
def getportafolio(token):
    data = pd.DataFrame()
    if isinstance(token,str) and token!='':
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata"]
        schema   = 'urbex'
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT * FROM urbex.portafolio WHERE token='{token}'" , engine)
        engine.dispose()
    return data
     
@st.cache_data(show_spinner=False)
def datawkt(data):
    user      = st.secrets["user_bigdata"]
    password  = st.secrets["password_bigdata"]
    host      = st.secrets["host_bigdata"]
    schema    = 'urbex'
    engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    datalotes = pd.DataFrame()
    
    if not data.empty and 'barmanpre' in data: 
        query     = "','".join(data['barmanpre'].unique())
        query     = f" lotcodigo IN ('{query}')" 
        datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        
        if not  datalotes.empty:
            datamerge = data.groupby('barmanpre').apply(lambda x: x.to_dict(orient='records')).reset_index()
            datamerge.columns = ['barmanpre','lista']
            datalotes = datalotes.merge(datamerge,on='barmanpre',how='left',validate='m:1')
            
    engine.dispose()
    return datalotes

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
    
@st.cache_data(show_spinner=False)
def data2geopandas(data,barmanpreref=None):
    
    urlexport     = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson       = pd.DataFrame().to_json()

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
            
            popup_paso = ""
            try:    popup_paso += f"""<b> Barrio:</b> {items['lista'][0]['prenbarrio']}<br>  """
            except: pass

            for j in items['lista']:
                
                urllink = ""
                prechip = j['chip'] if 'chip' in j and isinstance(j['chip'], str) else None
                if prechip is not None and isinstance(prechip,str):
                    urllink = urlexport+f"?type=predio&code={prechip}&vartype=chip&token={st.session_state.token}"
                
                popupinfo  = ""
                try:    popupinfo += f"""<b> Dirección:</b> {j['predirecc']}<br>"""
                except: pass

                popup_paso += f"""
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                    <a href="{urllink}" target="_blank" style="color: black;">
                        {popupinfo}
                    </a>
                </div>
                """
    
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    {popup_paso}
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        data    = data[['popup','color','geometry']]
        geojson = data.to_json()
        
    return geojson

@st.cache_data(show_spinner=False)
def data2geopoint(data):
    
    geojsonpoints = pd.DataFrame().to_json()
    if not data.empty:
        if 'latitud' in data and 'longitud' in data:
            data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data             = data[['geometry']]
        data['color']    = '#A16CFF'
        geojsonpoints    = data.to_json()
    return geojsonpoints

def reporte(data=pd.DataFrame(),datalotes=pd.DataFrame(),mapwidth=1600):

    #---------------------------------------------------------------------#
    # filtros
    #---------------------------------------------------------------------#
    cols1,cols2 = st.columns(2,gap="small")
    with cols1:
        areamin = st.number_input('Área mínima',value=0,min_value=0)
    with cols2:
        areamax = st.number_input('Área máxima',value=0,min_value=0)
    with cols1:
        antiguedadmin = st.number_input('Antigüedad desde (años)',value=0,min_value=0)
    with cols2:
        antiguedadmax = st.number_input('Antigüedad hasta (años)',value=0,min_value=0)
        
    with cols1:
        if 'estrato' in data and len(data['estrato'])>1:
            options = sorted(data['estrato'].unique())
            estrato = st.multiselect('Estrato',options=options)
            if isinstance(estrato,list) and estrato!=[]:
                data = data[data['estrato'].isin(estrato)]

    if not data.empty and 'prenbarrio' in data:
        options = list(sorted(data['prenbarrio'].unique()))
        with cols2:
            barrio = st.multiselect('Barrio',options=options)
            if isinstance(barrio,list) and barrio!=[]:
                data = data[data['prenbarrio'].isin(barrio)]
        
    if not data.empty and 'clasificacion' in data:
        if len(data['clasificacion'].unique())>1:
            options = list(sorted(data['clasificacion'].unique()))
            with cols1:
                clasificacion = st.multiselect('Tipo de inmueble',options=options)
                if isinstance(clasificacion,list) and clasificacion!=[]:
                    data   = data[data['clasificacion'].isin(clasificacion)]
                
    #if not data.empty and 'usosuelo' in data:
    #    if len(data['usosuelo'].unique())>1:
        #    options = list(sorted(data['usosuelo'].unique()))
        #    with cols1:
        #        usodelsuelo = st.multiselect('Uso del suelo',options=options)
        #        if isinstance(usodelsuelo,list) and usodelsuelo!=[]:
        #            data   = data[data['usosuelo'].isin(usodelsuelo)]
                
    diasvencimiento = 0
    if 'diasvencimiento' in data: 
        df = data[data['diasvencimiento'].notnull()]
        if not df.empty:
            with cols1:
                diasvencimiento = st.number_input('Días para el vencimiento',value=0,min_value=0)

    diaspublicacion = 0
    if 'diaspublicacion' in data: 
        df = data[data['diaspublicacion'].notnull()]
        if not df.empty:
            with cols2:
                diaspublicacion = st.number_input('Días de publicación',value=0,min_value=0)

    if 'fecha_ultima_transaccion' in data: 
        df = data[data['fecha_ultima_transaccion'].notnull()]
        if not df.empty:
            with cols1:
                fecha_filtro   = st.date_input('Filtro por fecha de trasacciones')
                fecha_filtro_d = datetime.combine(fecha_filtro, datetime.min.time())
                dias = (datetime.now() - fecha_filtro_d).days
                if dias>0:
                    filtrodate = datetime.now()-timedelta(days=dias)
                    data       = data[data['fecha_ultima_transaccion']>=filtrodate]
                    
    if areamin>0:
        data   = data[data['preaconst']>=areamin]
    if areamax>0:
        data   = data[data['preaconst']<=areamax]
    if antiguedadmin>0:
        antiguedadmin = datetime.now().year-antiguedadmin
        data   = data[data['prevetustz']<=antiguedadmin]
    if antiguedadmax>0:
        antiguedadmax = datetime.now().year-antiguedadmax
        data   = data[data['prevetustz']>=antiguedadmax]
    if diasvencimiento>0:
        data   = data[data['diasvencimiento']<=diasvencimiento]
    if diaspublicacion>0:
        data   = data[data['diaspublicacion']>=diaspublicacion]
    if not data.empty and not datalotes.empty:
        datalotes = datalotes[datalotes['barmanpre'].isin(data['barmanpre'])]

    #-------------------------------------------------------------------------#
    # Tabla de datos
    #-------------------------------------------------------------------------#
    dftable      = data.copy()
    chipselected = None
    if not dftable.empty:
        variables = ['barmanpre','chip','matricula','predirecc','prenbarrio','estrato','preaconst','preaterre','prevetustz','usosuelo','precioventa','preciorenta','fecha_vencimiento_contrato','diasvencimiento','fecha_publicacion','diaspublicacion','fecha_ultima_transaccion','cuantia','avaluo_catastral','impuesto_ajustado']
        variables = [x for x in variables if x in dftable]
        dftable   = dftable[variables]
        for i in ['fecha_vencimiento_contrato','fecha_publicacion']:
            if i in dftable:
                idd   = dftable[i].isnull()
                if sum(idd)>0:
                    dftable.loc[idd,i] = ''
                    
        dftable.rename(columns={'chip':'Chip','matricula':'Matrícula','prenbarrio':'Barrio','predirecc':'Dirección','preaconst':'Área construida','preaterre':'Área terreno','prevetustz':'Antiguedad','usosuelo':'Uso del suelo','estrato':'Estrato','precioventa':'Precio de venta','preciorenta':'Precio de renta','fecha_vencimiento_contrato':'Fecha vencimiento del contrato','diasvencimiento':'Días para el vencimiento','fecha_publicacion':'Fecha de publicación','fecha_ultima_transaccion':'Fecha de la última transacción','cuantia':'Valor de la última transacción','avaluo_catastral':'Avalúo Catastral','impuesto_ajustado':'Predial','diaspublicacion':'Días de publicación'},inplace=True)

    if not dftable.empty:
        dftable['link'] = dftable['Chip'].apply(lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={x}&vartype=chip&token={st.session_state.token}")
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
            chipselected = list(df['Chip'].unique())
            if isinstance(chipselected,list) and chipselected!=[]:
                data = data[data['prechip'].isin(chipselected)]

    #-------------------------------------------------------------------------#
    # Exportar data
    #-------------------------------------------------------------------------#
    if not dftable.empty:
        dataexport = dftable.copy()
        col1,col2,col3 = st.columns([0.7,0.2,0.1])
        with col2:
            st.write('')
            st.write('')
            if st.button('Descargar Excel Completo'):
                download_excel(dataexport)
                
    col1,col2 = st.columns([0.3,0.6])
    #---------------------------------------------------------------------#
    # Mapa de referencia
    #---------------------------------------------------------------------#
    if not data.empty and not datalotes.empty:
        
        latitud,longitud = 4.688002,-74.054444
        if 'latitud' in data and 'longitud' in data:
            latitud  = data['latitud'].mean()
            longitud = data['longitud'].mean()
        
        m = folium.Map(location=[latitud, longitud], zoom_start=11,tiles="cartodbpositron")

        geojson = data2geopandas(datalotes)
        popup                 = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        # Marker  
        geojsonpoints = data2geopoint(data)
        folium.GeoJson(geojsonpoints,style_function=style_function_geojson).add_to(m)

        with col1:
            st_map = st_folium(m,width=int(mapwidth*0.4),height=900)

    #-------------------------------------------------------------------------#
    # Dashboard
    #-------------------------------------------------------------------------#
    with col2:
        html = reporteHtml(data=data,mapwidth=1900,mapheight=200)
        st.components.v1.html(html, height=900)
        

@st.cache_data(show_spinner=False)
def reporteHtml(data=pd.DataFrame(),mapwidth=600,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Header
    html_header = ""
    if not data.empty:
        formato = [
                   {'texto':'Predios','value': '{:,.0f}'.format(int(len(data))) if len(data)>0 else None },
                   {'texto':'Edificios','value': '{:,.0f}'.format(int(len(data.drop_duplicates(subset='barmanpre',keep='first')))) if len(data)>0 else None  },
                   {'texto':'Avalúo catastral total','value': f"${data['avaluo_catastral'].sum():,.0f}"  if 'avaluo_catastral' in data else None},
                   {'texto':'Predial total','value':f"${data['impuesto_ajustado'].sum():,.0f}" if 'impuesto_ajustado' in data else None},
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

    #-------------------------------------------------------------------------#
    # Analisis de dias
    html_analisis_dias = ""
    html_grafica       = ""
    if not data.empty:
        for items in ['diaspublicacion','diasvencimiento']:
            titulo  = {'diaspublicacion':'Días de publicación','diasvencimiento':'Días de vencimiento del contrato'}
            formato = {'diaspublicacion':{'bins':[0, 60, 180, float('inf')],'labels':['<60', '60-180', '>180'],'colores':{'<60': '#65EBB7', '60-180': '#EBD465', '>180': '#EB5F71'}},
                       'diasvencimiento':{'bins':[0, 60, 120, float('inf')],'labels':['<60','60-120','>120'],'colores':{'<60': '#65EBB7', '60-120': '#EBD465', '>120': '#EB5F71'}}
                       }
            if items in data:
                df = data.copy()
                df['categoria'] = pd.cut(df[items], bins=formato[items]['bins'], labels=formato[items]['labels'], right=False)
                df          = df.groupby('categoria')['chip'].count().reset_index()
                df.columns  = ['categoria','conteo']
                df          = df.sort_values(by='conteo',ascending=False)
                df.index    = range(len(df))
                colores     = formato[items]['colores']
                df['color'] = df['categoria'].map(colores)
                if not df.empty:
                    fig = px.bar(df, x="categoria", y="conteo", text="conteo", title=titulo[items])
                    fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#A16CFF', textfont=dict(color='white'))
                    fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
                    fig.update_xaxes(tickmode='linear', dtick=1)
                    fig.update_traces(marker_color=df['color'])
                    fig.update_layout({
                        'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                        'legend':dict(bgcolor='black'),
                        'height':int(mapheight), 
                        'width':int(mapwidth*0.25),
                        'margin':dict(l=0, r=0, t=20, b=20),
                        'title_font':dict(size=11,color='black'),
                    })
                    fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(color='black'),showgrid=False, zeroline=False)
                    fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'),type='log')
                    html_fig_paso = fig.to_html(config={'displayModeBar': False})
                    try:
                        soup = BeautifulSoup(html_fig_paso, 'html.parser')
                        soup = soup.find('body')
                        soup = str(soup.prettify())
                        soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
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
        html_analisis_dias = f"""
        <div class="row" style="margin-top:20px;">
            {html_grafica}
        </div>
        """
            
    #-------------------------------------------------------------------------#
    # Barrios
    html_barrio  = ""
    html_grafica = ""
    if not data.empty:
        df         = data.groupby('prenbarrio')['chip'].count().reset_index()
        df.columns = ['barrio','conteo']
        df         = df.sort_values(by='conteo',ascending=False)
        df.index   = range(len(df))
        if not df.empty:
            fig = px.bar(df, x="barrio", y="conteo", text="conteo", title='Barrios')
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#A16CFF', textfont=dict(color='white'))
            fig.update_layout(title_x=0.4,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_xaxes(tickmode='linear', dtick=1)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'legend':dict(bgcolor='black'),
                'height':int(mapheight), 
                'width':int(mapwidth*0.35),
                'margin':dict(l=0, r=0, t=20, b=20),
                'title_font':dict(size=11,color='black'),
            })
            fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(color='black'),showgrid=False, zeroline=False)
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
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
        if not df.empty:
            input1      = '{:,.0f}'.format(len(df))
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
                                            <p class="card-category">Barrios</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
        if html_grafica!="":
            html_barrio = f"""
            <div class="row" style="margin-top:20px;">
                {html_inputs}
                {html_grafica}
            </div>
            """
          
    #-------------------------------------------------------------------------#
    # Tiplogias
    html_tipologias = ""
    html_grafica    = ""
    if not data.empty:
        formato = [{'variable':'preaconst' ,'titulo':'Distribución por Área Privada'},
                  {'variable':'prevetustz','titulo':'Distribución por Antigüedad'}]
        for iiter in formato:
            variable = iiter['variable']
            titulo   = iiter['titulo']
            df         = data.copy()
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
                w['linf'] = df[variable].min()
                w['lsup'] = df[variable].max()
                df        = df.merge(w[['isin','linf','lsup']],on='isin',how='left',validate='m:1')
                df        = df[(df[variable]>=df['linf']) & (df[variable]<=df['lsup'])]
                
                w         = df.groupby('isin')['chip'].count().reset_index() 
                w.columns = ['isin','count']
                df        = df.merge(w,on='isin',how='left',validate='m:1')
                df        = df[df['count']>2]
        
            if not df.empty:
                fig = px.box(df,x='isin',y=variable,title=titulo,color_discrete_sequence=['#624CAB'])
                fig.update_layout(
                    title_x=0.55,
                    height=int(mapheight),
                    #width=600,
                    width=int(mapwidth*0.3),
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
        <div class="row" style="margin-top:20px;">
            {html_grafica}
        </div>
        """
        
    #-------------------------------------------------------------------------#
    # General
    html_general  = ""
    html_grafica = ""
    if not data.empty and 'estrato' in data:
        df         = data.groupby('estrato')['chip'].count().reset_index()
        df.columns = ['estrato','conteo']
        df         = df.sort_values(by='estrato',ascending=True)
        df.index   = range(len(df))
        if not df.empty:
            fig = px.pie(df, names="estrato", values="conteo", title='Estrato',color_discrete_sequence=px.colors.sequential.RdBu[::-1])
            fig.update_traces(textinfo='percent+label',textfont_color='white',textposition='inside')
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
                'height': 200, 
                'width': int(mapwidth*0.5*0.5),
                'margin': dict(l=0, r=0, t=20, b=0),
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
                soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
                html_grafica += f""" 
                <div class="col-6">
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
    if not data.empty and 'clasificacion' in data:
        df         = data.groupby('clasificacion')['chip'].count().reset_index()
        df.columns = ['clasificacion','conteo']
        df         = df.sort_values(by='clasificacion',ascending=True)
        df.index   = range(len(df))
        if not df.empty:
            fig = px.pie(df, names="clasificacion", values="conteo", title='Tipo de inmueble',color_discrete_sequence=px.colors.sequential.RdBu[::-1])
            fig.update_traces(textinfo='percent+label',textfont_color='white',textposition='inside')
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
                'height': 200, 
                'width': int(mapwidth*0.5*0.5),
                'margin': dict(l=0, r=0, t=20, b=0),
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
                soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
                html_grafica += f""" 
                <div class="col-6">
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
    if html_grafica!="":
        html_general = f"""
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
            {html_analisis_dias}
            {html_general}
            {html_barrio}
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    main()
