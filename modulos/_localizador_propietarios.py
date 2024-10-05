import folium
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
from streamlit_folium import folium_static
from bs4 import BeautifulSoup
from streamlit_js_eval import streamlit_js_eval
from shapely.geometry import Point
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, AgGridTheme
from st_aggrid.shared import JsCode
from datetime import datetime

from data.getpropertiesbyID import main as getpropertiesbyID

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
    
    #-------------------------------------------------------------------------#
    # Variables
    formato = {
               'data_localizador_predios':pd.DataFrame(),
               'search_localizador_predios':False,
               }

    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value

    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
    col1,col2 = st.columns(2)
    if st.session_state.search_localizador_predios is False:
        
        with col1:
            tipodocumento  = st.selectbox('Tipo de documento',options=['','C.C.', 'N.I.T.', 'C.E.', 'PASAPORTE', 'T.I.'])
        with col2:
            identificacion = st.text_input('Número de documento',value='')
              
        with col1:
            inputvar = {'tipodocumento':tipodocumento, 'identificacion':identificacion}
            if st.button('Buscar'):
                with st.spinner('Buscando data'):
                    st.session_state.data_localizador_predios   = getpropertiesbyID(inputvar)
                    st.session_state.search_localizador_predios = True
                    st.rerun()
                   
    with col2:
        if st.button('Resetear búsqueda'):
            for key,value in formato.items():
                del st.session_state[key]
            st.rerun()
                    
    if st.session_state.search_localizador_predios and not st.session_state.data_localizador_predios.empty:
        reporte(st.session_state.data_localizador_predios,mapwidth=mapwidth)
    elif st.session_state.search_localizador_predios and st.session_state.data_localizador_predios.empty:
        st.error('No se encontró información de predios')
    
    
def reporte(data,mapwidth=1088):

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

    colf = st.columns(2,gap="small")
    cola = st.columns(2,gap="small")
    
    if not data.empty and 'active' in data:
        lista = [int(x) for x in data['active'].unique()]
        activo = None
        if 1 in lista:
            with cola[0]:
                activo = st.selectbox('Filtro:',options=['Actuales','Históricos','Todos'])
        elif 0 in lista:
            with cola[0]:
                activo = st.selectbox('Filtro:',options=['Históricos','Todos'])
        if isinstance(activo,str) and 'Actuales' in activo:
            data = data[data['active']==1]
        elif isinstance(activo,str) and 'Históricos' in activo:
            data = data[data['active']==0]
            
    ff   = 0
    if not data.empty and 'prenbarrio' in data:
        options = sorted([x for x in data['prenbarrio'].unique() if not pd.isna(x)])
        with colf[ff]:
            barrio = st.multiselect('Barrio',options=options)
            if barrio!=[]:
                data = data[data['prenbarrio'].isin(barrio)]
        ff +=1
    
    if not data.empty and 'usosuelo' in data:
        options = sorted([x for x in data['usosuelo'].unique() if not pd.isna(x)])
        with colf[ff]:
            usodelsuelo = st.multiselect('Uso del suelo',options=options)
            if usodelsuelo!=[]:
                data = data[data['usosuelo'].isin(usodelsuelo)]
        ff +=1
        
    if areamin>0:
        data = data[data['preaconst']>=areamin]
    if areamax>0:
        data = data[data['preaconst']<=areamax]
    if antiguedadmin>0:
        antiguedadmin = datetime.now().year-antiguedadmin
        data  = data[data['prevetustz']<=antiguedadmin]
    if antiguedadmax>0:
        antiguedadmax = datetime.now().year-antiguedadmax
        data  = data[data['prevetustz']>=antiguedadmax]
        
        
    cold1,cold2 = st.columns([0.6,0.3])
    col1,col2   = st.columns([0.3,0.6])

    #-------------------------------------------------------------------------#
    # Tabla de datos
    #-------------------------------------------------------------------------#
    dftable      = data.copy()
    chipselected = None
    if not dftable.empty:
        variables = ['barmanpre','prechip','matriculainmobiliaria','predirecc','preaconst','preaterre','prevetustz','usosuelo']
        variables = [x for x in variables if x in dftable]
        dftable   = dftable[variables]
        dftable.rename(columns={'prechip':'Chip','matriculainmobiliaria':'Matrícula','predirecc':'Dirección','preaconst':'Área construida','preaterre':'Área terreno','prevetustz':'Antiguedad','usosuelo':'Uso del suelo'},inplace=True)
        
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

        if   len(dftable)>=13: tableH = 300
        elif len(dftable)>=5:  tableH = int(len(dftable)*50)
        elif len(dftable)>1:   tableH = int(len(dftable)*60)
        elif len(dftable)==1:  tableH = 100
        else: tableH = 100
        with col2:
            response = AgGrid(dftable,
                        gridOptions=gb.build(),
                        columns_auto_size_mode="FIT_CONTENTS",
                        theme=AgGridTheme.STREAMLIT,
                        updateMode=GridUpdateMode.VALUE_CHANGED,
                        allow_unsafe_jscode=True,
                        width=int(mapwidth*0.6),
                        #height=400,
                        height=int(min(300, tableH)),
                        )
        
            df = pd.DataFrame(response['selected_rows'])
            if not df.empty:
                chipselected = list(df['Chip'].unique())
                if isinstance(chipselected,list) and chipselected!=[]:
                    data = data[data['prechip'].isin(chipselected)]

    with cold2:
        if st.button('Descargar Excel'):
            #download_excel(dftable)
            
            df        = data.copy()
            variables = [x for x in ['barmanpre','wkt','precuso','precdestin','active','year'] if x in df]
            if isinstance(variables,list) and variables!=[]:
                df = df.drop(columns=variables)
            df.rename(columns={'prechip':'Chip','matriculainmobiliaria':'Matrícula','predirecc':'Dirección','preaconst':'Área construida','preaterre':'Área terreno','prevetustz':'Antiguedad','usosuelo':'Uso del suelo','avaluo_catastral':'Avalúo Catastral','impuesto_ajustado':'Predial'},inplace=True)
            download_excel(df)
            
    #---------------------------------------------------------------------#
    # Mapa de referencia
    #---------------------------------------------------------------------#
    if not data.empty:
        
        latitud,longitud = 4.688002,-74.054444
        if 'latitud' in data and 'longitud' in data:
            latitud  = data['latitud'].mean()
            longitud = data['longitud'].mean()
        
        m = folium.Map(location=[latitud, longitud], zoom_start=11,tiles="cartodbpositron")

        geojson,geojsonpoints = data2geopandas(data)
        popup                 = folium.GeoJsonPopup(
            fields=["popup"],
            aliases=[""],
            localize=True,
            labels=True,
        )
        folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)

        # Marker        
        folium.GeoJson(geojsonpoints,style_function=style_function_geojson).add_to(m)

        with col1:
            folium_static(m,width=int(mapwidth*0.35),height=900)
    

    #-------------------------------------------------------------------------#
    # Dashboard
    #-------------------------------------------------------------------------#
    with col2:
        html = reporteHtml(data=data,mapwidth=mapwidth,mapheight=200)
        st.components.v1.html(html, height=900)

@st.cache_data(show_spinner=False)
def data2geopandas(data,barmanpreref=None):
    
    urlexport     = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson       = pd.DataFrame().to_json()
    geojsonpoints = pd.DataFrame().to_json()
    data2points   = data.copy()

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

            urllink = ""
            prechip = items['prechip'] if 'prechip' in items and isinstance(items['prechip'], str) else None
            if prechip is not None and isinstance(prechip,str):
                urllink = urlexport+f"?type=predio&code={prechip}&vartype=chip&token={st.session_state.token}"

            popupinfo = ""
            try:    popupinfo += f"""<b> Dirección:</b> {items['predirecc']}<br>"""
            except: pass
            try:    popupinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """
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
        data    = data[['popup','color','geometry']]
        geojson = data.to_json()
        
    if not data2points.empty:
        if 'latitud' in data and 'longitud' in data:
            data2points = data2points[(data2points['latitud'].notnull()) & (data2points['longitud'].notnull())]
    if not data2points.empty and 'latitud' in data2points and 'longitud' in data2points:
        data2points['geometry'] = data2points.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data2points             = gpd.GeoDataFrame(data2points, geometry='geometry')
        data2points             = data2points[['geometry']]
        data2points['color']    = '#A16CFF'
        geojsonpoints           = data2points.to_json()
    return geojson,geojsonpoints

@st.cache_data(show_spinner=False)
def reporteHtml(data=pd.DataFrame(),mapwidth=1280,mapheight=200):
    
    #-------------------------------------------------------------------------#
    # Header
    html_header = ""
    html_barrio = ""
    if not data.empty:
        formato = [
                   {'texto':'Predios','value': '{:,.0f}'.format(int(len(data))) if len(data)>0 else None },
                   {'texto':'Edificios','value': '{:,.0f}'.format(int(len(data.drop_duplicates(subset='barmanpre',keep='first')))) if len(data)>0 else None  },
                   {'texto':'Avaluo de los predios','value': f"${data['avaluo_catastral'].sum():,.0f}"  if 'avaluo_catastral' in data else None},
                   {'texto':'Predial','value':f"${data['impuesto_ajustado'].sum():,.0f}" if 'impuesto_ajustado' in data else None},
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
        # Barrios
        html_grafica = ""
        df         = data.groupby('prenbarrio')['prechip'].count().reset_index()
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
                'margin':dict(l=0, r=0, t=20, b=30),
                'title_font':dict(size=11,color='black'),
            })
            fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(size=7,color='black'),showgrid=False, zeroline=False)
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
            <div class="row">
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
                    width=int(mapwidth*0.3),
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(l=60, r=0, t=20, b=0),
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
            {html_barrio}
            {html_tipologias}
        </div>
    </body>
    </html>
    """
    return html

def download_excel(df):
    excel_file = df.to_excel('lista_propiedades.xlsx', index=False)
    with open('lista_propiedades.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Haz clic aquí para descargar",
        data=data,
        file_name='lista_propiedades.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )     
    
if __name__ == "__main__":
    main()
