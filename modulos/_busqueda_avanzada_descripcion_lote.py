import folium
import streamlit as st
import pandas as pd
import shapely.wkt as wkt
import plotly.graph_objects as go
import plotly.express as px
from bs4 import BeautifulSoup
from streamlit_folium import folium_static
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime
from plotly.subplots import make_subplots

from data.getlatlng import getlatlng
from data.datacomplemento import main as datacomplemento
from data.getdatabuilding import main as getdatabuilding
from data.googleStreetView import mapstreetview,mapsatelite
from data.data_listings import buildingMarketValues
from data.getuso_destino import usosuelo_class

def main(code=None):
    
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

    col1,col2  = st.columns([0.75,0.25],gap="small")

    with st.spinner('Buscando información'):
        datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(code)
        datausopredio = usosuelo_class()
        
        #-------------------------------------------------------------------------#
        # Latitud y longitud
        #-------------------------------------------------------------------------#
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
        
        #-------------------------------------------------------------------------#
        # Mapa & streetview
        #-------------------------------------------------------------------------#
        col1,col2,col3,col4,col5   = st.columns([0.23,0.02,0.23,0.02,0.5])

        m  = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
        if polygon:
            try: folium.GeoJson(polygon, style_function=style_function_color).add_to(m)
            except:
                try: folium.GeoJson(wkt.loads(polygon) , style_function=style_function_color).add_to(m)
                except: pass
        folium.Marker(location=[latitud, longitud]).add_to(m)
        with col5:
            folium_static(m,width=int(mapwidth*0.5),height=400)
    
        with col1:
            html = mapstreetview(latitud,longitud)
            st.components.v1.html(html, height=400)
        with col3:
            html = mapsatelite(latitud,longitud,polygon=str(polygon) if polygon is not None else None)
            st.components.v1.html(html, height=400)
            
        #-------------------------------------------------------------------------#
        # Tabla Principal 
        #-------------------------------------------------------------------------#
        html,conteo = principal_table(code=code,datacatastro=datacatastro,datausosuelo=datausosuelo,datalote=datalote,datavigencia=datavigencia,datatransacciones=datatransacciones,polygon=polygonstr,latitud=latitud,longitud=longitud,direccion=direccion)
        st.components.v1.html(html,height=int(conteo*1100/60),scrolling=True)
        cols1,cols2,cols3,cols4 = st.columns([0.04,0.26,0.5,0.2])
        colg1,colg2 = st.columns([0.001,0.999])
        
        #-------------------------------------------------------------------------#
        # Tabla Propiedades
        #-------------------------------------------------------------------------#
        #if not datacatastro.empty and len(datacatastro)>1:
        if not datacatastro.empty:
            #datacatastro['url']  = datacatastro['prechip'].apply(lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=unidad&code={x}")
            datacatastro['url']  = datacatastro['prechip'].apply(lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={x}&vartype=chip&token={st.session_state.token}")
            datacatastro         = datacatastro.sort_values(by='predirecc',ascending=True)
            
            col1,col2,col3,col4 = st.columns([0.04,0.26,0.5,0.2])
            with col2:
                options = ['Todos'] + list(datacatastro['predirecc'].unique())
                filtro = st.selectbox('Filtro por predio:',key='filtro_direccion_tabla1',options=options,placeholder='Seleccionar un predio')
            
            with col3:
                st.write('')
                titulo = 'Predios'
                html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto  = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                
            datapaso = datacatastro.copy()
            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
            
            for icol in ['predirecc','usosuelo','prechip','matriculainmobiliaria','precedcata','preaconst','preaterre']:
                if icol not in datapaso:
                    datapaso[icol] = ''
                    
            html_paso    = ""
            for _,items in datapaso.iterrows():
                html_paso += f"""
                <tr>
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{items['url']}" target="_blank">
                       <img src="https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    <td>{items['predirecc']}</td>
                    <td>{items['usosuelo']}</td>
                    <td>{items['prechip']}</td>
                    <td>{items['matriculainmobiliaria']}</td>
                    <td>{items['precedcata']}</td>
                    <td>{items['preaconst']}</td>
                    <td>{items['preaterre']}</td>
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Dirección</th>
                    <th>Uso del suelo</th>
                    <th>Chip</th>
                    <th>Matrícula Inmobiliaria</th>
                    <th>Cédula catastral</th>
                    <th>Área construida</th>
                    <th>Área de terreno</th>
                </tr>
            </thead>
            <tbody>
            {html_paso}
            </tbody>
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH)       
        
        #-------------------------------------------------------------------------#
        # Tabla Transacciones
        #-------------------------------------------------------------------------#
        if not datatransacciones.empty:       
            
            datatransacciones = gruoptransactions(datatransacciones)
            datapaso          = datatransacciones.copy()
            dataoptions       = datatransacciones.copy()
            dataoptions       = dataoptions.sort_values(by=['predirecc'],ascending=True)
            
            col1,col2,col3,col4 = st.columns([0.04,0.26,0.5,0.2])
            with col2:
                options = ['Todos'] + list(dataoptions['predirecc'].unique())
                filtro = st.selectbox('Filtro por predio: ',key='filtro_direccion_tabla2',options=options,placeholder='Seleccionar un predio')
            
            with col3:
                st.write('')
                titulo = 'Transacciones'
                html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto  = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                
            for inputval in ['cuantia']:
                iddnull = datatransacciones[inputval].isnull()
                if sum(iddnull)>0:
                    datatransacciones.loc[iddnull,inputval] = ''
                    
            if 'todo' not in filtro.lower():
                datapaso = datatransacciones[datatransacciones['predirecc']==filtro]
                
            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
        
            html_paso = ""
            for _,items in datapaso.iterrows():
                
                try:    cuantia = f"${items['cuantia']:,.0f}" if 'cuantia' in items and isinstance(items['cuantia'],(int,float)) else ''
                except: cuantia = ''
                try:    areaconstruida = f"{round(items['preaconst'],2)}"
                except: areaconstruida = ''     
                try:    areaterreno = f"{round(items['preaterre'],2)}"
                except: areaterreno = ''  
                html_paso += f"""
                <tr>
                    <td>{items['group']}</td>    
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{items['link']}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
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
            html_paso = f"""
            <thead>
                <tr>
                    <th>Grupo</th>
                    <th>Link</th>
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
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH)       
            
        #-------------------------------------------------------------------------#
        # Tabla CTL
        #-------------------------------------------------------------------------#
        if not datactl.empty:
            
            datapaso = datactl.copy()
            col1,col2,col3,col4 = st.columns([0.04,0.26,0.5,0.2])
            with col2:
                options = ['Todos'] + list(datactl['predirecc'].unique())
                filtro = st.selectbox('Filtro por predio: ',key='filtro_direccion_tabla3',options=options,placeholder='Seleccionar un predio')
            
            with col3:
                st.write('')
                titulo = 'Certificados de libertad y tradición'
                html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto  = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)

            if 'todo' not in filtro.lower():
                datapaso = datactl[datactl['predirecc']==filtro]

            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
            
            html_paso = ""
            for _,items in datapaso.iterrows():
                try:    areaconstruida = f"{round(items['preaconst'],2)}"
                except: areaconstruida = ''     
                try:    areaterreno = f"{round(items['preaterre'],2)}"
                except: areaterreno = ''  

                html_paso += f"""
                <tr> 
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{items['url']}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    <td>{items['last_fecha']}</td>
                    <td>{items['predirecc']}</td>
                    <td>{items['matriculainmobiliaria']}</td>
                    <td>{areaconstruida}</td>
                    <td>{areaterreno}</td>
                    <td>{items['usosuelo']}</td>            
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Fecha</th>
                    <th>Dirección</th>
                    <th>Matrícula</th>
                    <th>Área construida</th>
                    <th>Área de terreno</th>
                    <th>Uso del suelo</th>             
                </tr>
            </thead>
            <tbody>
            {html_paso}
            </tbody>
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH) 
    #-------------------------------------------------------------------------#
    # Listings
    #-------------------------------------------------------------------------#
    with st.spinner('Buscando listings'):
        datalistings = pd.DataFrame()
        if direccion is not None:
            datalistings = buildingMarketValues(direccion,precuso=None,mpioccdgo=None)
            
        if not datalistings.empty: 
            datalistings = datalistings.sort_values(by='tipo',ascending=True)
            datalistings = datalistings.drop_duplicates(subset=['tipoinmueble','tiponegocio','valor','areaconstruida','direccion'])
            
            datapaso = datalistings[datalistings['tipo']=='activos']
            if not datapaso.empty:
                titulo   = 'Listings activos'
                html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto    = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                datapaso = datapaso.sort_values(by='tiponegocio',ascending=True)
                html  = showlistings(datapaso)
                texto = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                
            datapaso = datalistings[datalistings['tipo']=='historico']
            if not datapaso.empty:
                titulo   = 'Listings históricos'
                html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto    = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                datapaso = datapaso.sort_values(by='tiponegocio',ascending=True)
                html  = showlistings(datapaso)
                texto = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)

    #-------------------------------------------------------------------------#
    # Graficas
    #-------------------------------------------------------------------------#
    datavigencia = mergeprecuso(datacatastro=datacatastro,datavigencia=datavigencia)
    tiposelect   = None
    options      = []

    if not datatransacciones.empty:
        options_paso = list(datausopredio[datausopredio['precuso'].isin(datatransacciones['precuso'])]['clasificacion'].unique())
        if isinstance(options_paso,list) and options_paso!=[]:
            options += options_paso
        if 'cuantiamt2' not in datatransacciones:
            datatransacciones['cuantiamt2'] = datatransacciones['cuantia']/datatransacciones['preaconst']

    if isinstance(options,list) and options!=[]:
        options = list(set(options))
        options = [x for x in options if not any([s for s in ['Depósitos','Parqueadero','Otros'] if s in x])]
        
    if isinstance(options,list) and options!=[]:
        if len(options)>1:
            with cols2:
                options    = ['Todos']+options
                tiposelect = st.selectbox('Seleccion tipo de inmueble',options=options)
        else: tiposelect = options[0]
        
    if isinstance(tiposelect,str) and tiposelect!='' and 'todos' not in tiposelect.lower():
        precusolist       = list(datausopredio[datausopredio['clasificacion']==tiposelect]['precuso'].unique())
        datavigencia      = datavigencia[datavigencia['precuso'].isin(precusolist)]
        datatransacciones = datatransacciones[datatransacciones['precuso'].isin(precusolist)]
        datacatastro      = datacatastro[datacatastro['precuso'].isin(precusolist)]
        
        seleccionlisting  = None
        formatodir = {'Residencial':['Apartamento','Casa'], 'Comercio':['Local'], 'Bodegas':['Bodega'],'Oficinas':['Oficina'],'Hoteles':['Hotel'] }
        if tiposelect in formatodir:
            seleccionlisting = formatodir[tiposelect]
        if not datalistings.empty and isinstance(seleccionlisting,list) and seleccionlisting!=[]:
            datalistings  = datalistings[datalistings['tipoinmueble'].isin(seleccionlisting)]

    if isinstance(tiposelect,str) and tiposelect!='':
        with colg2:
            html,numgraph = graficasHtml(datatransacciones=datatransacciones,datavigencia=datavigencia,datalistings=datalistings,datacatastro=datacatastro,datausosuelo=datausosuelo,datausopredio=datausopredio,mapwidth=mapwidth,mapheight=400)
            st.components.v1.html(html, height=numgraph*420)
        with cols3:
            st.write('')
            titulo = 'Estadísticas'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def principal_table(code=None,datacatastro=pd.DataFrame(),datausosuelo=pd.DataFrame(),datalote=pd.DataFrame(),datavigencia=pd.DataFrame(),datatransacciones=pd.DataFrame(),polygon=None,latitud=None,longitud=None,direccion=None):
            
    #-------------------------------------------------------------------------#
    # Data complemento
    precuso = None
    if not datausosuelo.empty and 'precuso' in datausosuelo: 
        precuso = list(datausosuelo['precuso'].unique())
    input_complemento = datacomplemento(barmanpre=code,latitud=latitud,longitud=longitud,direccion=direccion,polygon=polygon,precuso=precuso)
    #-------------------------------------------------------------------------#
    # Data analisis predial
    input_predial = analytics_predial(datavigencia,datacatastro)

    #-------------------------------------------------------------------------#
    # Data analisis transacciones
    input_transacciones = analytics_transacciones(datatransacciones,datavigencia)

    #-------------------------------------------------------------------------#
    # Modulo descriptivo
    #-------------------------------------------------------------------------#
    tablaubicacion       = ""
    tablacaracteristicas = ""
    tablaterreno         = ""
    tablatipologia       = ""
    tablatransacciones   = ""
    tablapredial         = ""
    tablamarketventa     = ""
    tablamarketarriendo  = ""
    tablavalorizacion    = ""
    tablademografica     = ""
    tablatransporte      = ""
    tablavias            = ""
    tablagalerianuevos   = ""
    tablapot             = ""
    tablasitp            = ""

    barrio = None
    conteo = 0
    
    if not datausosuelo.empty:
        #---------------------------------------------------------------------#
        # Seccion ubicacion
        try:    barrio = datausosuelo['prenbarrio'].iloc[0]
        except: barrio = None
        try:    direccion = datausosuelo['formato_direccion'].iloc[0]
        except: direccion = None
        try:    estrato = int(datausosuelo['estrato'].iloc[0])
        except: estrato = None
        try:    localidad = input_complemento['localidad'] if isinstance(input_complemento['localidad'], str) else None
        except: localidad = None
        try:    codigoupl = input_complemento['codigoupl'] if isinstance(input_complemento['codigoupl'], str) else None
        except: codigoupl = None       
        try:    upl = input_complemento['upl'] if isinstance(input_complemento['upl'], str) else None
        except: upl = None      
        try:    nombre_conjunto = input_complemento['nombre_conjunto'] if isinstance(input_complemento['nombre_conjunto'], str) else None
        except: nombre_conjunto = None  
        try:    latlng = f"{round(latitud,2)} | {round(longitud,2)}"
        except: latlng = None
        
        if 'direccion' in input_complemento and isinstance(input_complemento['direccion'], str): 
            direccion = input_complemento['direccion']
        if 'nombre_conjunto' in input_complemento and isinstance(input_complemento['nombre_conjunto'], str): 
            nombre_conjunto = input_complemento['nombre_conjunto']
            
        formato   = {'Dirección:':direccion,'Localidad:':localidad,'Código UPL:':codigoupl,'UPL:':upl,'Barrio:':barrio,'Estrato:':estrato,'Nombre:':nombre_conjunto,'lat-lng':latlng}
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                conteo    += 1
        if html_paso!="":
            labeltable     = "Ubicación"
            tablaubicacion = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablaubicacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaubicacion}</tbody></table></div></div>"""
        
        #---------------------------------------------------------------------#
        # Seccion caracteristicas
        try:    predios = int(datausosuelo['predios_total'].iloc[0])
        except: predios = None
        try:    antiguedad = int(datausosuelo['prevetustzmin'].iloc[0])
        except: antiguedad = None
        try:    pisos = int(datausosuelo['connpisos'].iloc[0])
        except: pisos = None
        try:    sotanos = int(datausosuelo['connsotano'].iloc[0])
        except: sotanos = None
        try:    areaconstruida = f"{round(datausosuelo['preaconst_total'].iloc[0],2)} m²"
        except: areaconstruida = None
        administracionmt2 = f"${input_complemento['administracion']:,.0f} m²" if 'administracion' in input_complemento and (isinstance(input_complemento['administracion'], float) or isinstance(input_complemento['administracion'], int)) else None
        ph        = input_complemento['ph'] if 'ph' in input_complemento and isinstance(input_complemento['ph'], str) else None
        formato   = {'Predios [matrículas independientes]:':predios,'Pisos:':pisos,'Sotanos:':sotanos,'Antigüedad:':antiguedad,'Área total construida :':areaconstruida,'Valor administración (*):': administracionmt2,'PH':ph}
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                conteo    += 1
        if html_paso!="":
            labeltable     = "Caracteristicas"
            tablacaracteristicas = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablacaracteristicas = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablacaracteristicas}</tbody></table></div></div>"""
        
        #---------------------------------------------------------------------#
        # Seccion terreno
        try:    areaterreno = f"{round(datausosuelo['preaterre_total'].iloc[0],2)} m²"
        except: areaterreno = None
        try:    esquinero = input_complemento['esquinero'] if 'esquinero' in input_complemento and  isinstance(input_complemento['esquinero'], str) else None
        except: esquinero = None      
        try:    viaprincipal = input_complemento['viaprincipal'] if 'viaprincipal' in input_complemento and isinstance(input_complemento['viaprincipal'], str) else None
        except: viaprincipal = None  
        try:    frentefondo = f"{input_complemento['areafrente']} x {input_complemento['areafondo']}"
        except: frentefondo = None
        try:    areapoligono = input_complemento['areapoligono'] if 'areapoligono' in input_complemento and (isinstance(input_complemento['areapoligono'], float) or isinstance(input_complemento['areapoligono'], int)) else None
        except: areapoligono = None
        try:    construcciones = int(datausosuelo['construcciones'].iloc[0]) if 'construcciones' in datausosuelo and (isinstance(datausosuelo['construcciones'].iloc[0], int) or isinstance(datausosuelo['construcciones'].iloc[0], float)) else None
        except: construcciones = None
        formato   = {'Área del terreno:':areaterreno,'Lote esquinero':esquinero,'Lote sobre vía principal':viaprincipal,'Frente x Fondo (*)':frentefondo,'Construcciones':construcciones,'Área del poligono':areapoligono}
        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                conteo    += 1
        if html_paso!="":
            labeltable   = "Terreno"
            tablaterreno = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablaterreno = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaterreno}</tbody></table></div></div>"""
        
        #---------------------------------------------------------------------#
        # Seccion Tipologias
        datausosuelo.index = range(len(datausosuelo))
        if len(datausosuelo)>1:
            html_paso = ""
            for i in range(len(datausosuelo)):
                try:    usosuelo = datausosuelo['usosuelo'].iloc[i]
                except: usosuelo = ''            
                try:    areaconstruida = round(datausosuelo['preaconst_precuso'].iloc[i],2)
                except: areaconstruida = ''       
                try:    areaterreno = round(datausosuelo['preaterre_precuso'].iloc[i],2)
                except: areaterreno = '' 
                try:    predios = int(datausosuelo['predios_precuso'].iloc[i])
                except: predios = ''                 
                try:    proporcion = f"{round(datausosuelo['preaconst_precuso'].iloc[i]/datausosuelo['preaconst_total'].iloc[i],2):,.1%}" 
                except: proporcion = ''
                conteo    += 1
                html_paso += f"""
                <tr>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{usosuelo}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{predios}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaconstruida}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{proporcion}</h6></td>
                    <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaterreno}</h6></td>
                </tr>
                """
            html_paso = f"""
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Predios</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área construida</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Proporción</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área de terreno</h6></td>
            {html_paso}
            """
            if html_paso!="":
                labeltable     = "Tipologías de activos"
                tablatipologia = f"""
                <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                {html_paso}
                <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                """
                tablatipologia = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablatipologia}</tbody></table></div></div>"""
    
    labelbarrio = ""
    try:
        if isinstance(barrio, str): 
            labelbarrio = f'[{barrio.title()}]'
    except: pass
    #---------------------------------------------------------------------#
    # Seccion Transacciones
    try:    transacciones_total = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(input_transacciones['transacciones_total'])}</h6></td></tr>"""  if (isinstance(input_transacciones['transacciones_total'],float) or isinstance(input_transacciones['transacciones_total'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: transacciones_total = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""  
    try:    valortrasnacciones = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${round(input_transacciones['valortrasnacciones'],2):,.0f} m²</h6></td></tr>""" if (isinstance(input_transacciones['valortrasnacciones'],float) or isinstance(input_transacciones['valortrasnacciones'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: valortrasnacciones = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    try:    transacciones_lastyear = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(input_transacciones['transacciones_lastyear'])}</h6></td></tr>"""  if (isinstance(input_transacciones['transacciones_lastyear'],float) or isinstance(input_transacciones['transacciones_lastyear'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: transacciones_lastyear = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Total compraventas y/o leasing:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    try:    valortrasnacciones_lastyear = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${round(input_transacciones['valortransacciones_lastyear'],2):,.0f} m²</h6></td></tr>""" if (isinstance(input_transacciones['valortransacciones_lastyear'],float) or isinstance(input_transacciones['valortransacciones_lastyear'],int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    except: valortrasnacciones_lastyear = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio de las transacciones:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>"""
    
    titulo    = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Último año</h6></td></tr>"""
    html_paso = f"""
    {titulo}
    <tr><td style="border: none;"><h6></h6></td></tr>
    {valortrasnacciones_lastyear}
    {transacciones_lastyear}
    <tr><td style="border: none;"><h6></h6></td></tr>
    """
    
    titulo     = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">Desde el 2019 a la fecha</h6></td></tr>"""
    html_paso += f"""
    {titulo}
    <tr><td style="border: none;"><h6></h6></td></tr>
    {valortrasnacciones}
    {transacciones_total}
    <tr><td style="border: none;"><h6></h6></td></tr>
    """   
    if html_paso!="":
        conteo += 6
        labeltable         = "Transacciones"
        tablatransacciones = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablatransacciones = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatransacciones}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion precios de referencia
    if 'market_venta' in input_complemento:
        html_paso     = ""
        df            = pd.DataFrame(input_complemento['market_venta'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        df            = df.set_index('index').T.reset_index()
        if 'valor' in df: df['valor'] = df['valor'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        if 'obs'   in df: df['obs']   = df['obs'].apply(lambda x:   f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(x)}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        namedict = {'activos':'Listings Activos','historico':'Listings no Activos'}
        for i in ['activos','historico']:
            datapaso = df[df['index']==i]
            if not datapaso.empty:
                variables          = [x for x in ['valor', 'obs'] if x in datapaso]
                datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            else:
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            conteo    += 4

        if html_paso!="":
            labeltable         = "Precios de Referencia en Venta"
            tablamarketventa = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablamarketventa = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablamarketventa}</tbody></table></div></div>"""

    if 'market_arriendo' in input_complemento:
        html_paso     = ""
        df            = pd.DataFrame(input_complemento['market_arriendo'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        df            = df.set_index('index').T.reset_index()
        if 'valor' in df: df['valor'] = df['valor'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        if 'obs'   in df: df['obs']   = df['obs'].apply(lambda x:   f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{int(x)}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>""")
        namedict = {'activos':'Listings Activos','historico':'Listings no Activos'}
        for i in ['activos','historico']:
            datapaso = df[df['index']==i]
            if not datapaso.empty:
                variables          = [x for x in ['valor', 'obs'] if x in datapaso]
                datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            else:
                titulo     = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: left;">{namedict[i].title()}:</h6></td></tr>"""
                html_paso += f"""
                {titulo}
                <tr><td style="border: none;"><h6></h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"># de listings:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">Sin información</h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td></tr>
                """
            conteo    += 4

        if html_paso!="":
            labeltable         = "Precios de Referencia en Arriendo"
            tablamarketarriendo = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablamarketarriendo = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablamarketarriendo}</tbody></table></div></div>"""
    
    #---------------------------------------------------------------------#
    # Seccion Condiciones de mercado
    html_paso = ""
    if 'valorizacion' in input_complemento and isinstance(input_complemento['valorizacion'], list):
        df            = pd.DataFrame(input_complemento['valorizacion'])
        colnull       = df.columns[df.isnull().all()]
        df            = df.drop(columns=colnull)
        variables     = [var for var in list(df) if var not in ['tipoinmueble']]
        tipoinmuebles = list(df['tipoinmueble'].unique())
        k             = len(tipoinmuebles)
        if 'valormt2'     in df: df['valormt2']     = df['valormt2'].apply(lambda x:     f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valor promedio m²:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">${x:,.0f} m²</h6></td></tr>""" if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else '')
        if 'valorizacion' in df: df['valorizacion'] = df['valorizacion'].apply(lambda x: f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Valorización:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{x:.2%}</h6></td></tr>"""   if not pd.isnull(x) and (isinstance(x, float) or isinstance(x, int)) else '')
        if 'tiponegocio'  in df: df['tiponegocio']  = df['tiponegocio'].apply(lambda x:  f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{x.title()}:</h6></td></tr>"""   if not pd.isnull(x) and isinstance(x, str)  else '')

        for i in tipoinmuebles:
            datapaso           = df[df['tipoinmueble']==i]
            datapaso['output'] = df[variables].apply(lambda x: ''.join(x), axis=1)
            titulo = ""
            if k>1: titulo = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;text-align: center;">{i.title()}:</h6></td></tr>"""
            conteo    += 1
            html_paso += f"""
            {titulo}
            <tr><td style="border: none;"><h6></h6></td></tr>
            {'<tr><td style="border: none;"><h6></h6></td></tr>'.join(datapaso['output'].unique())}
            <tr><td style="border: none;"><h6></h6></td></tr>
            """
    if html_paso!="":
        labeltable         = f"Precios de referencia {labelbarrio}"
        tablavalorizacion = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablavalorizacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavalorizacion}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion Galeria Nuevos
    #formato   = {'# Proyectos activos en barrio:':'','Valor de venta:':' m²'}
    #html_paso = ""
    #for key,value in formato.items():
    #    if value is not None:
    #        html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
    #if html_paso!="":
    #    tablagalerianuevos = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Proyectos nuevos</td></tr>{html_paso}</tbody></table></div>"""
    #    tablagalerianuevos = f"""<div class="col-md-6">{tablagalerianuevos}</div>"""
   
    #---------------------------------------------------------------------#
    # Seccion POT
    if 'POT' in input_complemento and input_complemento['POT']!=[]:
        html_paso = ""
        for items in input_complemento['POT']:
            if 'data' in items:
                if len(items['data'])>1:
                    html_paso += f"""
                    <tr><td style="border: none;"><h6></h6></td></tr>
                    <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{items['nombre']}:</h6></td></tr>
                    """
                    for key,value in items['data'].items():
                        html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                else:
                    for key,value in items['data'].items():
                        html_paso += f"""
                        <tr><td style="border: none;"><h6></h6></td></tr>
                        <tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">{items['nombre']}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>
                        """
                conteo += 1
            
        if html_paso!="":
            labeltable = "P.O.T"
            tablapot   = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablapot = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablapot}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion Demografica
    if 'dane' in input_complemento:
        html_paso = ""
        for key,value in input_complemento['dane'].items():
            try: 
                valor = "{:,}".format(int(value))
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{valor}</h6></td></tr>"""
                conteo    += 1
            except: pass
        if html_paso!="":
            labeltable         = f"Información Demográfica {labelbarrio}"
            tablademografica = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablademografica = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablademografica}</tbody></table></div></div>"""

    #---------------------------------------------------------------------#
    # Seccion Transporte
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso       = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        labeltable      = "Transmilenio"
        tablatransporte = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablatransporte = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablatransporte}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion SITP
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso  = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        labeltable = "SITP"
        tablasitp  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablasitp = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablasitp}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion Vias
    if 'vias' in input_complemento and isinstance(input_complemento['vias'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['vias']}</h6></td></tr>"""
        labeltable = "Vías"
        tablavias  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablavias = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavias}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion Predial
    try:    avaluomt2 = f"${round(input_predial['avaluocatastral'],0):,.0f} m²" if (isinstance(input_predial['avaluocatastral'],float) or isinstance(input_predial['avaluocatastral'],int)) else None
    except: avaluomt2 = None
    try:    predialmt2 = f"${round(input_predial['predial'],0):,.0f} m²" if (isinstance(input_predial['predial'],float) or isinstance(input_predial['predial'],int)) else None
    except: predialmt2 = None
    try:    propietarios = int(input_predial['propietarios'])
    except: propietarios = None
    formato   = {'Avalúo catastral:':avaluomt2,'Predial:':predialmt2, '# Propietarios (*):': propietarios}
    html_paso = ""
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
            conteo    += 1
    if html_paso!="":
        labeltable = "Información Catastral"
        tablapredial  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablapredial = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablapredial}</tbody></table></div></div>"""
        
    #---------------------------------------------------------------------#
    # Cuando es un solo predio
    tablasolopredio = ""
    html_paso       = ""
    if not datacatastro.empty and len(datacatastro)==1:
        try:    chip = datacatastro['prechip'].iloc[0]
        except: chip = None
        try:    matricula = datacatastro['matriculainmobiliaria'].iloc[0]
        except: matricula = None
        try:    cedulacatastral = datacatastro['precedcata'].iloc[0]
        except: cedulacatastral = None
        try:    areaconstruida = f"{round(datacatastro['preaconst'].iloc[0],2)} m²"
        except: areaconstruida = None    
        formato   = {'Chip:':chip,'Matrícula Inmobiliaria:':matricula,'Cédula catastral':cedulacatastral}
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                conteo    += 1
        if not datausosuelo.empty:
            try:    usosuelo = datausosuelo['usosuelo'].iloc[0]
            except: usosuelo = None
            formato   = {'Uso del suelo:':usosuelo}
            for key,value in formato.items():
                if value is not None:
                    html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                    conteo    += 1
        if html_paso!="":
            labeltable = "Información del predio"
            tablasolopredio  = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablasolopredio = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablasolopredio}</tbody></table></div></div>"""
        
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
                    {tablaubicacion}
                    {tablasolopredio}
                    {tablacaracteristicas}
                    {tablaterreno}
                    {tablatipologia}
                    {tablapredial}
                    {tablatransacciones}
                    {tablamarketventa}
                    {tablamarketarriendo}
                    {tablavalorizacion}
                    {tablagalerianuevos}
                    {tablapot}
                    {tablademografica}
                    {tablatransporte}
                    {tablasitp}
                    {tablavias}
                    <p style="margin-top:50px;font-size: 0.6em;color: #908F8F;">(*) cálculos aproximados<a href="#nota1">nota al pie</a>.</p>
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
    return html,conteo
    
@st.cache_data(show_spinner=False)
def graficasHtml(datatransacciones=pd.DataFrame(),datavigencia=pd.DataFrame(),datalistings=pd.DataFrame(),datacatastro=pd.DataFrame(),datausosuelo=pd.DataFrame(),datausopredio=pd.DataFrame(),mapwidth=600,mapheight=500):
  
    numgraph = 0
    #-------------------------------------------------------------------------#
    # Transacciones
    html_barras  = ""
    html_grafica = ""
    datapaso     = pd.DataFrame()
    df           = pd.DataFrame()
    if not datatransacciones.empty:
        df               = datatransacciones.copy()
        df['cuantiamt2'] = df['cuantia']/df['preaconst']
        df               = df[df['cuantiamt2']>1500000]
        if not df.empty and 'codigo' in df:
            df = df[df['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
            
        if not df.empty:
            df['year'] = pd.to_datetime(df['fecha_documento_publico'])
            df['year'] = df['year'].dt.year
            df         = df[df['year']>=(datetime.now().year-4)]
            df         = df.groupby('year').agg({'cuantiamt2':['count','median']}).reset_index()
            df.columns = ['fecha','count','value']
            df.index   = range(len(df))
            datapaso   = df.copy()
    
    if not datavigencia.empty:
        df         = datavigencia.copy()
        df         = df.groupby(['chip','vigencia']).agg({'avaluomt2':'max'}).reset_index()
        df.columns = ['chip','vigencia','avaluomt2']
        df         = df.groupby('vigencia').agg({'avaluomt2':'median'}).reset_index()
        df.columns = ['fecha','avaluomt2']
        df         = df[df['fecha']>=(datetime.now().year-4)]
        if not datapaso.empty and not df.empty:
            datapaso = datapaso.merge(df,on='fecha',how='outer',validate='1:1')
        elif datapaso.empty and not df.empty:
            datapaso = df.copy()
            
    df = pd.DataFrame()
    if not datalistings.empty:
        df = datalistings.copy()
        df = df[df['tiponegocio']=='Venta']
        df = df[df['valormt2']>1500000]
    if not df.empty:
        df['year'] = pd.to_datetime(df['fecha_inicial'])
        df['year'] = df['year'].dt.year
        df         = df[df['year']>=(datetime.now().year-4)]
        df         = df.groupby('year').agg({'valormt2':'median'}).reset_index()
        df.columns = ['fecha','valormt2']
        df.index   = range(len(df))
        if not datapaso.empty and not df.empty:
            datapaso = datapaso.merge(df,on='fecha',how='outer',validate='1:1')
        elif datapaso.empty and not df.empty:
            datapaso = df.copy()

    if not datapaso.empty:
        fig         = make_subplots(specs=[[{"secondary_y": True}]])
        offsetgrpah = -1
        if 'count' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['count'],name='Transacciones (#)' ,marker_color='#7189FF',offsetgroup=offsetgrpah,width=0.2,showlegend=True,text=datapaso['count'],texttemplate='%{text}',textposition='inside',textangle=0,textfont=dict(color='white')),secondary_y=False)
        if 'value' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['value']    ,name='Valor transacciones (m2)',marker_color='#624CAB',offsetgroup=1,width=0.2,showlegend=True,text=datapaso['value'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)
        if 'avaluomt2' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['avaluomt2'],name='Avalúo catastral (m2)',marker_color='#FF6B6B',offsetgroup=2,width=0.2,showlegend=True,text=datapaso['avaluomt2'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)
        if 'valormt2' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['valormt2'] ,name='Listings en venta (m2)',marker_color='#D9CBBF',offsetgroup=3,width=0.2,showlegend=True,text=datapaso['valormt2'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)

        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            yaxis2_title=None,
            barmode='group',
            height=int(mapheight), 
            width=int(mapwidth*0.55),
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=0, r=0, t=0, b=100),
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
    #-------------------------------------------------------------------------#
    # Transacciones - Box
    if not datatransacciones.empty:
        df               = datatransacciones.copy()
        df['cuantiamt2'] = df['cuantia']/df['preaconst']
        df               = df[df['cuantiamt2']>1500000]
        if not df.empty and 'codigo' in df:
            df = df[df['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
    
        if not df.empty:
            df               = df.merge(datausopredio[['precuso','clasificacion']],on='precuso',how='left',validate='m:1')
            w                = df.groupby('clasificacion')['docid'].count().reset_index() 
            w.columns        = ['clasificacion','count']
            df               = df.merge(w,on='clasificacion',how='left',validate='m:1')
            df               = df[df['count']>2]
            df               = df[df['cuantiamt2']>0]
            if not df.empty:
                fig = px.box(df,x='clasificacion',y='cuantiamt2',title="Distribución de transacciones (m2)",color_discrete_sequence=px.colors.sequential.RdBu[::-1])
                fig.update_layout({
                    'xaxis_title':None,
                    'yaxis_title':None,
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                    'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
                    'height': int(mapheight), 
                    'width': int(mapwidth*0.25),
                    'margin': dict(l=70, r=0, t=50, b=50),
                    'title_font': dict(size=11, color='black'),
                })
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
    if isinstance(html_grafica,str) and html_grafica!="":
        numgraph += 1
        html_barras = f"""
        <div class="row mb-20">
            {html_grafica}
        </div>
        """

    #-------------------------------------------------------------------------#
    # Tiplogias
    html_tipologias = ""
    html_grafica    = ""
    if not datausosuelo.empty and len(datausosuelo)>1:
        df         = datausosuelo.copy()
        df         = df.merge(datausopredio[['precuso','clasificacion']],on='precuso',how='left',validate='m:1')
        df         = df.groupby('clasificacion')['preaconst_precuso'].sum().reset_index()
        df.columns = ['clasificacion','area']
        df         = df.sort_values(by='clasificacion',ascending=True)
        category_order = df['clasificacion'].tolist()
        
        fig = px.pie(df, names="clasificacion", values="area", title="Proporción de Área Total",color_discrete_sequence=px.colors.sequential.RdBu[::-1],category_orders={"clasificacion": category_order})
        fig.update_traces(textinfo='percent+label',textfont_color='white',textposition='inside')
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
            'height': int(mapheight), 
            'width': int(mapwidth*0.28),
            'margin': dict(l=20, r=0, t=50, b=50),
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
    
    if not datacatastro.empty:
        df         = datacatastro.copy()
        df         = df.merge(datausopredio[['precuso','clasificacion']],on='precuso',how='left',validate='m:1')
        q1         = df.groupby('clasificacion')['preaconst'].quantile(0.25).reset_index()
        q1.columns = ['clasificacion','q1']
        q3         = df.groupby('clasificacion')['preaconst'].quantile(0.75).reset_index()
        q3.columns = ['clasificacion','q3']
                
        # Remover outliers
        w         = q1.merge(q3,on='clasificacion',how='outer')
        w['iqr']  = w['q3']-w['q1']
        w['linf'] = w['q1'] - 1.5*w['iqr']
        w['lsup'] = w['q3'] + 1.5*w['iqr']
        df        = df.merge(w[['clasificacion','linf','lsup']],on='clasificacion',how='left',validate='m:1')
        df        = df[(df['preaconst']>=df['linf']) & (df['preaconst']<=df['lsup'])]
        
        w         = df.groupby('clasificacion')['prechip'].count().reset_index() 
        w.columns = ['clasificacion','count']
        df        = df.merge(w,on='clasificacion',how='left',validate='m:1')
        df        = df[df['count']>2]

        if not df.empty:
            fig = px.box(df,x='clasificacion',y='preaconst',title="Distribución por Área",color_discrete_sequence=px.colors.sequential.RdBu[::-1])
            fig.update_layout({
                'xaxis_title':None,
                'yaxis_title':None,
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                'legend':dict(bgcolor='rgba(0, 0, 0, 0)'),
                'height': int(mapheight), 
                'width': int(mapwidth*0.28),
                'margin': dict(l=70, r=0, t=50, b=50),
                'title_font': dict(size=11, color='black'),
            })
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
                
    # Precios de renta
    df = pd.DataFrame()
    if not datalistings.empty:
        df = datalistings.copy()
        df = df[df['tiponegocio']=='Arriendo']
    if not df.empty:
        df['year'] = pd.to_datetime(df['fecha_inicial'])
        df['year'] = df['year'].dt.year
        df         = df[df['year']>=(datetime.now().year-4)]
        df         = df.groupby('year').agg({'valormt2':['median','count']}).reset_index()
        df.columns = ['fecha','valormt2','conteo']

        years = [2022, 2023, 2024]
        for year in years:
            if year not in df['fecha'].values:
                df = pd.concat([df, pd.DataFrame({'fecha': [year], 'valormt2': [None], 'conteo': [None]})], ignore_index=True)
        df.index = range(len(df))
        
        if not df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df['fecha'],y=df['conteo'],name='# inmuebles',marker_color='#7189FF',offsetgroup=0,width=0.4,showlegend=True,text=df['conteo'],texttemplate='%{text}',textposition='inside',textangle=0,textfont=dict(color='white')),secondary_y=False)
            fig.add_trace(go.Bar(x=df['fecha'],y=df['valormt2'],name='Arriendo (m2)',marker_color='#624CAB',offsetgroup=1,width=0.4,showlegend=True,text=df['valormt2'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)

            fig.update_layout(
                title='Precios de arriendo (m2)',
                xaxis_title=None,
                yaxis_title=None,
                yaxis2_title=None,
                barmode='group',
                height=int(mapheight), 
                width=int(mapwidth*0.28),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                margin=dict(l=0, r=0, t=50, b=50),
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
            
    if isinstance(html_grafica,str) and html_grafica!="":
        numgraph += 1
        html_tipologias = f"""
        <div class="row">
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
            height: 400px;
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
        
        .mb-20 {
            margin-bottom: 10px;
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
            {html_barras}
            {html_tipologias}
        </div>
    </body>
    </html>
    """
    return html,numgraph

@st.cache_data(show_spinner=False)
def gruoptransactions(datatransacciones):
    if not datatransacciones.empty and 'docid' in datatransacciones:
        datamerge = datatransacciones.drop_duplicates(subset='docid',keep='first')
        datamerge = datamerge.sort_values(by='docid',ascending=False)
        datamerge['group'] = range(len(datamerge))
        datamerge['group'] = datamerge['group']+1
        datatransacciones = datatransacciones.merge(datamerge[['docid','group']],on='docid',how='left',validate='m:1')
        datatransacciones = datatransacciones.sort_values(by=['docid','preaconst','cuantia'],ascending=[False,False,False])
    return datatransacciones
        
@st.cache_data(show_spinner=False)
def analytics_predial(datavigencia,datacatastro):
    
    result = {'avaluocatastral':None,'predial':None,'propietarios':None}
    if not datavigencia.empty and not datacatastro.empty: 
        datamerge = datacatastro.drop_duplicates(subset='prechip',keep='first')
        if 'usosuelo' in datamerge:
            datapaso = datavigencia.merge(datamerge[['prechip','precuso','preaconst']],left_on='chip',right_on='prechip',how='left',validate='m:1')
            idd      = datapaso['precuso'].isin(['048','049','051'])
            datapaso = datapaso[~idd]
            if not datapaso.empty: 
                datapaso = datapaso.sort_values(by=['vigencia','chip'],ascending=False)
                datapaso = datapaso.drop_duplicates(subset='chip',keep='first')
                datapaso['avaluomt2']  = datapaso['valorAutoavaluo']/datapaso['preaconst']  
                datapaso['predialmt2'] = datapaso['valorImpuesto']/datapaso['preaconst']
                try: result['avaluocatastral'] = datapaso['avaluomt2'].median()
                except: pass
                try: result['predial'] = datapaso['predialmt2'].median()
                except: pass
            
        if 'nroIdentificacion' in datavigencia: 
            datapaso  = datavigencia[datavigencia['nroIdentificacion'].notnull()]
            datapaso  = datapaso.sort_values(by=['chip','vigencia'],ascending=False)
            datagroup = datapaso.groupby(['chip'])['vigencia'].max().reset_index()
            datagroup.columns = ['chip','maxvigencia']
            datapaso  = datapaso.merge(datagroup,on='chip',how='left',validate='m:1')
            idd       = datapaso['vigencia']==datapaso['maxvigencia']
            datapaso  = datapaso[idd]
            if not datapaso.empty:
                datapaso = datapaso.drop_duplicates(subset=['nroIdentificacion','tipoDocumento'],keep='first')
                result['propietarios'] = len(datapaso)
    return result
           
@st.cache_data(show_spinner=False)
def mergeprecuso(datacatastro=pd.DataFrame(),datavigencia=pd.DataFrame()):
    if not datacatastro.empty and not datavigencia.empty:
        datamerge    = datacatastro.drop_duplicates(subset=['prechip'],keep='first')
        datamerge.rename(columns={'prechip':'chip'},inplace=True)
        variables = [x for x in ['precuso','preaconst'] if x not in datavigencia]
        if isinstance(variables,list) and variables!=[]:
            variables = [x for x in variables if x in datamerge]
        if isinstance(variables,list) and variables!=[]:
            variables.append('chip') 
            datavigencia = datavigencia.merge(datamerge[variables],on='chip',how='left',validate='m:1')
    
    if not datavigencia.empty and all([x for x in ['precuso','preaconst'] if x in datavigencia]):
        datavigencia['avaluomt2'] = datavigencia['valorAutoavaluo']/datavigencia['preaconst']
        
    for i in ['precuso','preaconst','avaluomt2']:
        if i not in datavigencia: 
            datavigencia[i] = None

    return datavigencia
        
@st.cache_data(show_spinner=False)
def analytics_transacciones(datatransacciones,datavigencia):
    
    result   = {'transacciones_total':None,'valortrasnacciones':None,'transacciones_lastyear':None,'valortransacciones_lastyear':None}
    datapaso = pd.DataFrame()
    
    if not datatransacciones.empty:
        datapaso = datatransacciones.sort_values(by=['docid','cuantia','preaconst'],ascending=[False,False,False])
        datapaso = datapaso.drop_duplicates(subset='docid',keep='first')
        datapaso = datapaso[datapaso['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
        datapaso['valormt2'] = datapaso['cuantia']/datapaso['preaconst']
        
    if not datapaso.empty and not datavigencia.empty:
        datamerge = datavigencia[datavigencia['vigencia']>=2019]
        if datamerge.empty: datamerge = datavigencia.copy()
        datamerge = datamerge.sort_values(by=['chip','vigencia'],ascending=[True,True])
        datamerge = datamerge.drop_duplicates(subset=['chip'],keep='first')
        datapaso  = datapaso.merge(datamerge[['chip','valorAutoavaluo']],left_on='prechip',right_on='chip',how='left',validate='m:1')
        datapaso  = datapaso[datapaso['cuantia']>=datapaso['valorAutoavaluo']*0.8]
        if not datapaso.empty:
            result['transacciones_total'] = len(datapaso)
            result['valortrasnacciones']  = datapaso['valormt2'].median()
            
        try:
            datapaso['fecha_documento_publico'] = pd.to_datetime(datapaso['fecha_documento_publico'])
            fecha_now      = pd.to_datetime('now')
            fecha_lastyear = fecha_now - pd.DateOffset(years=1)
            datapaso = datapaso[datapaso['fecha_documento_publico']>=fecha_lastyear]
            if not datapaso.empty:
                result['transacciones_lastyear']      = len(datapaso)
                result['valortransacciones_lastyear'] = datapaso['valormt2'].median()

        except: pass
    return result
        
@st.cache_data(show_spinner=False)
def tablestyle():
    return """
        <style>
            * {
                box-sizing: border-box;
                -webkit-box-sizing: border-box;
                -moz-box-sizing: border-box;
            }
        
            body {
                font-family: Helvetica;
                -webkit-font-smoothing: antialiased;
            }
        
            .table-background {
                background: rgba(71, 147, 227, 1);
            }
        
            h2 {
                text-align: center;
                font-size: 18px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: white;
                padding: 30px 0;
            }
        
            /* Table Styles */
        
            .table-wrapper {
                margin: 10px 70px 70px;
                box-shadow: 0px 35px 50px rgba(0, 0, 0, 0.2);
            }
        
            .fl-table {
                border-radius: 5px;
                font-size: 12px;
                font-weight: normal;
                border: none;
                border-collapse: collapse;
                width: 100%;
                max-width: 100%;
                white-space: nowrap;
                background-color: white;
            }
        
            .fl-table td,
            .fl-table th {
                text-align: center;
                padding: 8px;
            }
        
            .fl-table td {
                border-right: 1px solid #f8f8f8;
                font-size: 12px;
            }
        
            .fl-table thead th {
                color: #ffffff;
                background: #A16CFF; /* Manteniendo el color verde claro para el encabezado */
                position: sticky; /* Haciendo el encabezado fijo */
                top: 0; /* Fijando el encabezado en la parte superior */
            }
        
            .fl-table tr:nth-child(even) {
                background: #f8f8f8;
            }
            .table-scroll {
                overflow-x: auto;
                overflow-y: auto;
                max-height: 400px; /* Altura máxima ajustable según tus necesidades */
            }
        
            @media (max-width: 767px) {
                .fl-table {
                    display: block;
                    width: 100%;
                }
                .table-wrapper:before {
                    content: "Scroll horizontally >";
                    display: block;
                    text-align: right;
                    font-size: 11px;
                    color: white;
                    padding: 0 0 10px;
                }
                .fl-table thead,
                .fl-table tbody,
                .fl-table thead th {
                    display: block;
                }
                .fl-table thead th:last-child {
                    border-bottom: none;
                }
                .fl-table thead {
                    float: left;
                }
                .fl-table tbody {
                    width: auto;
                    position: relative;
                    overflow-x: auto;
                }
                .fl-table td,
                .fl-table th {
                    padding: 20px .625em .625em .625em;
                    height: 60px;
                    vertical-align: middle;
                    box-sizing: border-box;
                    overflow-x: hidden;
                    overflow-y: auto;
                    width: 120px;
                    font-size: 13px;
                    text-overflow: ellipsis;
                }
                .fl-table thead th {
                    text-align: left;
                    border-bottom: 1px solid #f7f7f9;
                }
                .fl-table tbody tr {
                    display: table-cell;
                }
                .fl-table tbody tr:nth-child(odd) {
                    background: none;
                }
                .fl-table tr:nth-child(even) {
                    background: transparent;
                }
                .fl-table tr td:nth-child(odd) {
                    background: #f8f8f8;
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tr td:nth-child(even) {
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tbody td {
                    display: block;
                    text-align: center;
                }
            }
        </style>
        """

@st.cache_data(show_spinner=False)
def showlistings(data):
    html = ""
    css_format = """
        <style>
            .card {
                background-color: #F0F0F0;
            }
          .property-image {
            width: 100%;
            height: 250px;
            overflow: hidden; 
            margin-bottom: 10px;
          }
          .price-info {
            font-family: 'Roboto', sans-serif;
            font-size: 20px;
            margin-bottom: 2px;
            text-align: center;
          }
          .caracteristicas-info {
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
            margin-bottom: 2px;
            text-align: center;
          }
          img{
            max-width: 100%;
            width: 100%;
            height:100%;
            object-fit: cover;
            margin-bottom: 10px; 
          }
        </style>
    """
    urlexport = "http://www.urbex.com.co/Ficha"
    imagenes  = ''
    for i, items in data.iterrows():
        urllink = urlexport+f"?code={items['code']}&tiponegocio={items['tiponegocio'].lower()}&tipoinmueble={items['tipoinmueble'].lower()}"

        imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
        precio           = f"<b> Precio:</b> ${items['valor']:,.0f}<br>" if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)) else ''
        direccion        = f"<b> Dirección:</b> {items['direccion']}<br>" if 'direccion' in items and isinstance(items['direccion'], str) else ''
        valormt2         = f"<b> Valor m²:</b> ${items['valormt2']:,.0f} m²<br>" if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)) else ''
        tiponegocio      = f"<b> Tipo de negocio:</b> {items['tiponegocio']}<br>" if 'tiponegocio' in items and isinstance(items['tiponegocio'], str) else ''
        tipoinmueble     = items['tipoinmueble'] if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else None
        caracteristicas  = f"<b> Área construida:</b> {items['areaconstruida']}<br>" if 'areaconstruida' in items and (isinstance(items['areaconstruida'], float) or isinstance(items['areaconstruida'], int)) else ''

        if any([x for x in ['apartamento','casa'] if x in tipoinmueble.lower()]):
            if all([x for x in ['habitaciones','banos','garajes'] if x in items]):
                try:    caracteristicas = f"{items['areaconstruida']} m<sup>2</sup> | {int(float(items['habitaciones']))} H | {int(float(items['banos']))} B | {int(float(items['garajes']))} G <br>"
                except: caracteristicas = "" 
        tipoinmueble = f"<b> Tipo de inmueble:</b> {items['tipoinmueble']}<br>" if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else ''
        imagenes += f'''
        <div class="col-xl-3 col-sm-6 mb-xl-2 mb-2">
          <div class="card h-100">
            <div class="card-body p-3">
            <a href="{urllink}" target="_blank" style="color: black;">
                <div class="property-image">
                  <img src="{imagen_principal}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                </div>
                {tiponegocio}
                {precio}
                {valormt2}
                {caracteristicas}
                {direccion}
                {tipoinmueble}
            </a>
            </div>
          </div>
        </div>            
        '''
    if imagenes!='':
        html = f"""
            <!DOCTYPE html>
            <html>
              <head>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet"/>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" id="pagestyle" rel="stylesheet"/>
              {css_format}
              </head>
              <body>
              <div class="container-fluid py-4">
                <div class="row">
                {imagenes}
                </div>
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
