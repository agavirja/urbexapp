import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import folium
from streamlit_folium import folium_static
from streamlit_js_eval import streamlit_js_eval
from bs4 import BeautifulSoup

from modulos._propietarios import main as _propietarios
from modulos._busqueda_avanzada_descripcion_lote import gruoptransactions,analytics_transacciones,showlistings

from data.googleStreetView import mapstreetview,mapsatelite
from data.getdatabuilding import main as getdatabuilding
from data.datacomplemento import main as datacomplemento
from data.data_listings import buildingMarketValues
from data.getlicencias import getlicencias
from data.getdatalotescombinacion import getdatacombinacionlotes,mergedatabybarmanpre
from data.getreporte_sinupot import main as getreportesinupot

from display.stylefunctions  import style_function_geojson

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

    #-------------------------------------------------------------------------#
    # Buscar data
    #-------------------------------------------------------------------------#
    with st.spinner('Consolidando lotes'):
        datapredios,datalotescatastro,datausosuelo = getdatacombinacionlotes(code)
        #-------------------------------------------------------------------------#
        # Mapa
        #-------------------------------------------------------------------------#
        col1,col2,col3,col4,col5   = st.columns([0.2,0.02,0.2,0.05,0.5])
        latitud,longitud = [None]*2
        polygon          = None
        if not datapredios.empty:
            try:
                polygon  = wkt.loads(datapredios['wkt'].iloc[0]) 
                latitud  = polygon.centroid.y
                longitud = polygon.centroid.x
            except: pass
            
        if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
    
            m = folium.Map(location=[latitud, longitud], zoom_start=18,tiles="cartodbpositron")
        
            if not datapredios.empty:
                folium.GeoJson(wkt.loads(datapredios['wkt'].iloc[0]), style_function=style_function_consolidacion).add_to(m)
        
            if not datalotescatastro.empty:
                geojson = data2geopandas(datalotescatastro)
                popup   = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
                
            with col5:
                folium_static(m,width=int(mapwidth*0.4),height=400)
        
        #-------------------------------------------------------------------------#
        # Google maps streetview
        #-------------------------------------------------------------------------#
        with col1:
            if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
                html = mapstreetview(latitud,longitud)
                st.components.v1.html(html, width=int(mapwidth*0.2), height=400)
        with col3:
            if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
                html = mapsatelite(latitud,longitud,polygon=str(polygon) if polygon is not None else None)
                st.components.v1.html(html, width=int(mapwidth*0.2), height=400)
            
        #-------------------------------------------------------------------------#
        # Data vigencia y transacciones
        #-------------------------------------------------------------------------#
        barmanpre = None
        datavigencia,datatransacciones,datadirecciones,datactl,_du,_dl = [pd.DataFrame()]*6
        input_transacciones = {}
        if isinstance(code, str) and code!='':
            barmanpre = code.split('|')
            datadirecciones,_du,_dl,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
            datalotescatastro = mergedatabybarmanpre(datalotescatastro.copy(),_du.copy(),['prenbarrio','formato_direccion','construcciones','prevetustzmin'])
            
        if not datatransacciones.empty and not datavigencia.empty:
            input_transacciones = analytics_transacciones(datatransacciones,datavigencia)
                
        #-------------------------------------------------------------------------#
        # Data complemento
        #-------------------------------------------------------------------------#
        precuso    = None
        direccion  = None
        polygonstr = None
        
        if not _du.empty and 'formato_direccion' in _du:
            direccion = list(_du['formato_direccion'].unique())
    
        if not datapredios.empty:
            polygonstr = datapredios['wkt'].iloc[0]
      
        if not datausosuelo.empty and 'precuso' in datausosuelo: 
            precuso = list(datausosuelo['precuso'].unique())
            
        input_complemento = datacomplemento(barmanpre=code,latitud=latitud,longitud=longitud,direccion=direccion,polygon=polygonstr,precuso=precuso)
        try:    input_complemento['direcciones'] = ' | '.join(direccion)
        except: input_complemento['direcciones'] = ''
    
        html,conteo = principal_table(datapredios=datapredios,datausosuelo=datausosuelo,input_complemento=input_complemento,input_transacciones=input_transacciones)
        st.components.v1.html(html,height=int(conteo*600/26),scrolling=True)
    
        #-------------------------------------------------------------------------#
        # Tabla Lotes
        #-------------------------------------------------------------------------#
        if not datalotescatastro.empty and len(datalotescatastro)>1:       
            
            col1,col2,col3,col4 = st.columns([0.04,0.2,0.5,0.26])
            with col3:
                st.write('')
                titulo = 'Lotes que conforman el terreno'
                html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto  = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
                
            if   len(datalotescatastro)>=10: tableH = 450
            elif len(datalotescatastro)>=5:  tableH = int(len(datalotescatastro)*45)
            elif len(datalotescatastro)>1:   tableH = int(len(datalotescatastro)*60)
            elif len(datalotescatastro)==1:  tableH = 100
            else: tableH = 100
            
            html_paso = ""
            for _,items in datalotescatastro.iterrows():
                try:    barrio = f"{items['prenbarrio']}"
                except: barrio = ''  
                try:    direccion = f"{items['formato_direccion']}"
                except: direccion = ''
                try:    areaconstruida = f"{round(items['preaconst'],2)}"
                except: areaconstruida = ''     
                try:    areaterreno = f"{round(items['preaterre'],2)}"
                except: areaterreno = ''
                try:    estrato = f"{int(items['estrato'])}"
                except: estrato = ""
                try:    predios = f"{int(items['predios'])}"
                except: predios = ""
                try:    pisos = f"{int(items['pisos'])}"
                except: pisos = ""
                try:    sotanos = f"{int(items['sotanos'])}"
                except: sotanos = ""
                try:    construcciones = f"{int(items['construcciones'])}"
                except: construcciones = ""
                try:    antiguedadmin = f"{int(items['prevetustzmin'])}"
                except: antiguedadmin = ""                
                try:    link = f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}"
                except: link = ""
                html_paso += f"""
                <tr>
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{link}" target="_blank">
                       <img src="https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    <td>{barrio}</td>
                    <td>{direccion}</td>
                    <td>{areaterreno}</td> 
                    <td>{areaconstruida}</td>
                    <td>{estrato}</td>
                    <td>{predios}</td>
                    <td>{pisos}</td>
                    <td>{sotanos}</td>
                    <td>{construcciones}</td>
                    <td>{antiguedadmin}</td>
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Barrio</th>
                    <th>Dirección</th>
                    <th>Área de terreno</th>
                    <th>Área construida</th>
                    <th>Estrato</th>
                    <th>Predios</th>
                    <th>Pisos Máx</th>
                    <th>Sotanos</th>
                    <th>Construcciones</th>
                    <th>Antiguedad</th>            
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
            
            datatransacciones_paso = gruoptransactions(datatransacciones)
    
            st.write('')
            titulo = 'Transacciones'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
    
            if   len(datatransacciones_paso)>=10: tableH = 450
            elif len(datatransacciones_paso)>=5:  tableH = int(len(datatransacciones_paso)*45)
            elif len(datatransacciones_paso)>1:   tableH = int(len(datatransacciones_paso)*60)
            elif len(datatransacciones_paso)==1:  tableH = 100
            else: tableH = 100
                
            html_paso = ""
            for _,items in datatransacciones_paso.iterrows():
                
                try:    cuantia = f"${items['cuantia']:,.0f}"
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
        # Propietarios
        #-------------------------------------------------------------------------#  
        if barmanpre is not None:
            titulo = 'Propietarios'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            _propietarios(chip=None,barmanpre=barmanpre,vartype=None,infilter=False,descargar=False)
    
        #-------------------------------------------------------------------------#
        # Licencias
        #-------------------------------------------------------------------------# 
        barmanprelist = str(code).split('|')
        datalicencias,html,tableh = getlicencias(barmanprelist)
        if html!="":
            titulo      = 'Licencias del lote'
            html_titulo = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html_titulo, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            st.components.v1.html(html,height=tableh)
            
        #-------------------------------------------------------------------------#
        # SINUPOT
        #-------------------------------------------------------------------------# 
        getreportesinupot(barmanpre=code,reporte_chip=True,licencias=True,plusvalia=False,estratificacion=False,telecomunicacion=False,pot_190=True)
    
    #-------------------------------------------------------------------------#
    # Listings
    #-------------------------------------------------------------------------#
    if not datadirecciones.empty:
        with st.spinner('Buscando listings'):
            datalistings = pd.DataFrame()
            direccion    = datadirecciones['predirecc'].to_list()
            if isinstance(direccion, list):
                datalistings = buildingMarketValues(direccion,precuso=None,mpioccdgo=None)
            
            #if not datalistings.empty: 
                #datalistings = datalistings.sort_values(by='tipo',ascending=True)
                #datalistings = datalistings.drop_duplicates(subset=['tipoinmueble','tiponegocio','valor','areaconstruida','direccion'])
                
            if not datalistings.empty:   
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

@st.cache_data(show_spinner=False)
def data2geopandas(data):
    
    urlexport = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = ""
        data.index       = range(len(data))
        for idd,items in data.iterrows():
            
            barmanpre =  items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"

            infopopup = ""
            try:    infopopup += f"""<b> Dirección:</b> {items['formato_direccion']}<br>"""
            except: pass
            try:    infopopup += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """
            except: pass
            try:    infopopup += f"""<b> Área construida total:</b> {round(items['preaconst'],2)}<br>"""
            except: pass
            try:    infopopup += f"""<b> Área de terreno:</b> {round(items['preaterre'],2)}<br> """
            except: pass
            try:    infopopup += f"""<b> Estrato:</b> {int(items['estrato'])}<br> """
            except: pass
            try:    infopopup += f"""<b> Pisos:</b> {int(items['pisos'])}<br> """
            except: pass
            try:    infopopup += f"""<b> Sotanos:</b> {int(items['pisos'])}<br> """
            except: pass
            try:    infopopup += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>"""
            except: pass            
            try:    infopopup += f"""<b> Total de predios:</b> {int(items['predios'])}<br> """
            except: pass            
            try:    infopopup += f"""<b> Propietarios:</b> {int(items['propietarios'])}<br> """
            except: pass            

            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {infopopup}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def principal_table(datapredios=pd.DataFrame(),datausosuelo=pd.DataFrame(),input_complemento={},input_transacciones={}):
   
    conteo = 0
    labelbarrio = ""
    try:
        if isinstance(input_complemento['barrio'], str): 
            labelbarrio = f"[{input_complemento['barrio'].title()}]"
    except: pass

    #---------------------------------------------------------------------#
    # Seccion Tipologias
    tablaubicacion = ""
    html_paso = ""
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Dirección:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['direcciones']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Localidad:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['localidad']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Barrio:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['barrio']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Código UPL:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['codigoupl']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">UPL:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['upl']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Estrato:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{int(datapredios['estrato'].iloc[0])}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    try:    
        html_paso += f"""
        <tr>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">LatLng:</h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['latlng']}</h6></td>
        </tr>"""
        conteo += 1
    except: pass
    
    if html_paso!="":
        html_paso = f"""
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
            <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
        {html_paso}
        """
    if html_paso!="":
        
        labeltable     = "Ubicación"
        tablaubicacion = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaubicacion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaubicacion}</tbody></table></div></div>"""


    #---------------------------------------------------------------------#
    # Terreno consildado
    tablaterreno = ""
    html_paso = ""
    
    try:    preaterre = f"{round(datapredios['preaterre'].iloc[0],2)}" 
    except: preaterre = None
    try:    preaconst = f"{round(datapredios['preaconst'].iloc[0],2)}" 
    except: preaconst = None
    try:    lotes = f"{int(datapredios['lotes'].iloc[0])}" 
    except: lotes = None
    try:    prediostotal = f"{int(datapredios['predios_total'].iloc[0])}" 
    except: prediostotal = None
    try:    pisos = f"{int(datapredios['pisos'].iloc[0])}" 
    except: pisos = None
    try:    sotanos = f"{int(datapredios['sotanos'].iloc[0])}" 
    except: sotanos = None
    try:    propietarios = f"{int(datapredios['propietarios'].iloc[0])}" 
    except: propietarios = None
    try:    avaluo = f"${int(datapredios['avaluo_catastral'].iloc[0]):,.0f}" 
    except: avaluo = None
    try:    predial = f"${int(datapredios['predial'].iloc[0]):,.0f}" 
    except: predial = None
    try:    esquinero = "Si" if datapredios['predial'].iloc[0]==1 else "No"
    except: esquinero = None
    try:    viaprincipal = "Si" if datapredios['tipovia'].iloc[0]==1 else "No"
    except: viaprincipal = None
    
    formato = {"Área de terreno":preaterre,"Área construida":preaconst,"Número de lotes":lotes,
               "Total de predios":prediostotal,"Pisos máximos":pisos,"Sotanos máximos":sotanos,
               "Esquinero":esquinero,"Vía principal":viaprincipal,
               "Propietarios":propietarios,"Avaúo catastral total":avaluo,"Predial total":predial,
               }
    
    for key,value in formato.items():
        if value is not None: 
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{value}</h6></td>
            </tr>"""
            conteo += 1
    if html_paso!="":
        labeltable     = "Terreno consolidado"
        tablaterreno = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaterreno = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0" style="table-layout: auto; width: 100%;"><tbody>{tablaterreno}</tbody></table></div></div>"""

    #-------------------------------------------------------------------------#
    # Seccion Transacciones
    tablatransacciones = ""
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
    # Seccion Tipologias
    datausosuelo.index = range(len(datausosuelo))
    tablatipologia     = ""
    html_paso          = ""
    if len(datausosuelo)>0:
        areatotalconstruida = datausosuelo['preaconst_precuso'].sum()
        for i in range(len(datausosuelo)):
            try:    usosuelo = datausosuelo['usosuelo'].iloc[i]
            except: usosuelo = ''            
            try:    areaconstruida = round(datausosuelo['preaconst_precuso'].iloc[i],2)
            except: areaconstruida = ''       
            try:    areaterreno = round(datausosuelo['preaterre_precuso'].iloc[i],2)
            except: areaterreno = '' 
            try:    predios = int(datausosuelo['predios_precuso'].iloc[i])
            except: predios = ''                 
            try:    proporcion = f"{round(datausosuelo['preaconst_precuso'].iloc[i]/areatotalconstruida,2):,.1%}" 
            except: proporcion = ''
            conteo    += 1
            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;font-size: 12px;">{usosuelo}</h6></td>
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

    #---------------------------------------------------------------------#
    # POT
    tablapot  = ""
    html_paso = ""
    if 'POT' in input_complemento and input_complemento['POT']!=[]:
        
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
    # Seccion Condiciones de mercado
    tablavalorizacion = ""
    html_paso         = ""
    if 'valorizacion' in input_complemento and isinstance(input_complemento['valorizacion'], list):
        html_paso     = ""
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
    # Seccion Demografica
    tablademografica = ""
    html_paso        = ""
    if 'dane' in input_complemento:
        html_paso = ""
        for key,value in input_complemento['dane'].items():
            try: 
                valor = "{:,}".format(int(value))
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}:</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{valor}</h6></td></tr>"""
                conteo    += 1
            except: pass
        if html_paso!="":
            labeltable     = f"Información Demográfica {labelbarrio}"
            tablademografica = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablademografica = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablademografica}</tbody></table></div></div>"""
        
    #---------------------------------------------------------------------#
    # Seccion Transporte
    tablatransporte = ""
    html_paso       = ""
    if 'transmilenio' in input_complemento and isinstance(input_complemento['transmilenio'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['transmilenio']}</h6></td></tr>"""
        labeltable     = "Transmilenio"
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
    tablasitp = ""
    html_paso = ""
    if 'sitp' in input_complemento and isinstance(input_complemento['sitp'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['sitp']}</h6></td></tr>"""
        labeltable     = "SITP"
        tablasitp = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablasitp = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablasitp}</tbody></table></div></div>"""
        conteo    += 1
    #---------------------------------------------------------------------#
    # Seccion Vias
    tablavias = ""
    html_paso = ""
    if 'vias' in input_complemento and isinstance(input_complemento['vias'],str): 
        html_paso = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{input_complemento['vias']}</h6></td></tr>"""
        labeltable     = "Vías"
        tablavias = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablavias = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablavias}</tbody></table></div></div>"""
        conteo    += 1
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
      <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: 0px;">
        <div class="row">
          <div class="col-md-12 mb-md-0 mb-2">
            <div class="card h-100">
              <div class="card-body p-3">
                <div class="container-fluid py-4">
                  <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                    {tablaubicacion}
                    {tablaterreno}
                    {tablatransacciones}
                    {tablatipologia}
                    {tablapot}
                    {tablavalorizacion}
                    {tablademografica}
                    {tablatransporte}
                    {tablasitp}
                    {tablavias}
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
        
@st.cache_data
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
        
def style_function_consolidacion(feature):
    return {
        'fillColor': '#006400',
        'color': 'blue',
        'weight': 3,
        'dashArray': '6, 6'
    }

if __name__ == "__main__":
    main()
