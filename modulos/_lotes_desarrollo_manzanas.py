import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from bs4 import BeautifulSoup
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Polygon,mapping
from streamlit_js_eval import streamlit_js_eval

from data.data_pot_manzana import builddata,getmanzanasfromlatlng,consolidacionlotesselected,getmanzanadescripcion,getscacodigofromlatlng,getconfiguracionmanazana
from modulos._propietarios import main as getpropietarios

from display.stylefunctions  import style_function,style_function_geojson

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
               'data_barrios':pd.DataFrame(),
               'data_manzanas':pd.DataFrame(),
               'data_lotes':pd.DataFrame(),
               'data_consolidacion':pd.DataFrame(),
               'showreport':False,
               'scacodigo':None,
               'codigomanzana':None,
               'geojson_onclick_barrio':None,
               'geojson_onclick_manzana':None,
               'geojson_consolidacion':None,
               'zoom_start_map1':12,
               'zoom_start_map2':16,
               'zoom_start_map3':18,
               'latitud':4.652652, 
               'longitud':-74.077899,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    
    col1, col2 = st.columns(2)
    with col1:
        #tratamiento = st.multiselect('Tratamiento',options=['CONSOLIDACION','DESARROLLO','RENOVACION','CONSERVACION','MEJORAMIENTO INTEGRAL'])
        tratamiento = st.selectbox('Tratamiento',options=['CONSOLIDACION','DESARROLLO','RENOVACION','CONSERVACION','MEJORAMIENTO INTEGRAL'])
        tratamiento = [tratamiento]
    with col2:
        alturaminpot = st.number_input('Altura mínima en tratamiento',value=0,min_value=0)
    with col1:
        #actividad = st.multiselect('Actuación estratégica',options=['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
        actividad = st.selectbox('Actuación estratégica',options=['Área de Actividad Grandes Servicios Metropolitanos - AAGSM', 'Área de Actividad de Proximidad - AAP- Generadora de soportes urbanos', 'Área de Actividad de Proximidad - AAP - Receptora de soportes urbanos', 'Área de Actividad Estructurante - AAE - Receptora de vivienda de interés social', 'Plan Especial de Manejo y Protección -PEMP BIC Nacional: se rige por lo establecido en la Resolución que lo aprueba o la norma que la modifique o sustituya', 'Área de Actividad Estructurante - AAE - Receptora de actividades económicas'])
        actividad = [actividad]
    with col2:
        #actuacion = st.selectbox('Actuación estratégica',options=['Todos','Si','No'])
        actuacion = st.selectbox('Actuación estratégica',options=['No','Si'])
    with col1:
        maxpropietarios = st.number_input('Máximo número de propietarios en la manzana',value=0,min_value=0)
    
    col1, col2 = st.columns(2)
    with col2:
        st.write('')
        st.write('')
        if st.button('Buscar'):
            st.session_state.showreport = True
            st.rerun()
            
    with col1:
        st.write('')
        st.write('')
        if st.button('Resetear la busqueda'):
            for key,value in formato.items():
                st.session_state[key] = value
            st.rerun()
    
    if st.session_state.showreport:
        with st.spinner('Buscando data'):
            st.session_state.data_manzanas,st.session_state.data_barrios = builddata(tratamiento,alturaminpot,actividad,actuacion)
            
        #-------------------------------------------------------------------------#
        # Mapa 1: barrios
        if not st.session_state.data_barrios.empty:
            titulo   = 'Barrios en los que se encuentran manzanas que cumplen con los criterios de busqueda'
            html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;background-color: #2B2D31;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #6EA4EE;">Haz click en un barrio</p></section></body></html>"""
            texto    = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
    
            m1      = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start_map1,tiles="cartodbpositron")
            geojson = data2geopandas(st.session_state.data_barrios)
            
            tooltip=folium.features.GeoJsonTooltip(
                fields=['scanombre','num_manzanas'],  # Campo a mostrar en el tooltip
                aliases=['Barrio: ','# de manzanas: '],  # Etiquetas para los campos
                localize=False)
        
            folium.GeoJson(geojson,style_function=style_function_geojson,tooltip=tooltip).add_to(m1)
            
            if st.session_state.geojson_onclick_barrio is not None:
                folium.GeoJson(st.session_state.geojson_onclick_barrio,style_function=style_function_geojson).add_to(m1)
        
            st_map1 = st_folium(m1,width=mapwidth,height=mapheight)
        
            if 'last_object_clicked' in st_map1 and st_map1['last_object_clicked']:
                st.session_state.latitud  = st_map1['last_object_clicked']['lat']
                st.session_state.longitud = st_map1['last_object_clicked']['lng']
                with st.spinner('Buscando manzanas'):
                    st.session_state.scacodigo = getscacodigofromlatlng(st.session_state.latitud,st.session_state.longitud)
                    st.session_state.data_consolidacion = pd.DataFrame()
                    if st.session_state.scacodigo is not None:
                        datapaso = st.session_state.data_barrios[st.session_state.data_barrios['scacodigo']==st.session_state.scacodigo]
                        st.session_state.geojson_onclick_barrio = data2geopandas(datapaso,color='blue')
                        st.session_state.zoom_start_map1 = 14
                        st.rerun()
                
        #---------------------------------------------------------------------#
        # Mapa 2: Manzanas   
        datapaso  = pd.DataFrame()
        if not st.session_state.data_manzanas.empty and st.session_state.scacodigo is not None:
            datapaso = st.session_state.data_manzanas[st.session_state.data_manzanas['scacodigo']==st.session_state.scacodigo]
            
        if not datapaso.empty:
            titulo   = 'Manzanas'
            html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;background-color: #2B2D31;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #6EA4EE;">Haz click en una manzana</p></section></body></html>"""
            texto    = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)

            m2 = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start_map2,tiles="cartodbpositron",key='mapa2')
            
            if not st.session_state.data_manzanas.empty:
                datapaso = st.session_state.data_manzanas[st.session_state.data_manzanas['scacodigo']==st.session_state.scacodigo]
                geojson  = data2geopandas(datapaso)
                folium.GeoJson(geojson,style_function=style_function_geojson).add_to(m2)
                
            if st.session_state.geojson_onclick_manzana is not None:
                folium.GeoJson(st.session_state.geojson_onclick_manzana,style_function=style_function_geojson).add_to(m2)
        
            st_map2 = st_folium(m2,width=mapwidth,height=mapheight)
            
            col1,col2 = st.columns([0.6,0.4])
            if 'last_object_clicked' in st_map2 and st_map2['last_object_clicked']:
                st.session_state.latitud   = st_map2['last_object_clicked']['lat']
                st.session_state.longitud  = st_map2['last_object_clicked']['lng']
                st.session_state.data_consolidacion = pd.DataFrame()
                datacodman = pd.DataFrame()
                with st.spinner('Buscando lotes de la manzana'):
                    datacodman,st.session_state.data_lotes = getmanzanasfromlatlng(st.session_state.latitud,st.session_state.longitud)
                if not datacodman.empty:
                    st.session_state.codigomanzana = datacodman['mancodigo'].iloc[0]
                    datapaso = st.session_state.data_manzanas[st.session_state.data_manzanas['mancodigo']==st.session_state.codigomanzana]
                    st.session_state.geojson_onclick_manzana = data2geopandas(datapaso,color='blue')
                    st.session_state.zoom_start_map2 = 16
                    st.session_state.zoom_start_map3 = 18
                    st.rerun()

            if st.session_state.codigomanzana is not None:
                titulo   = 'Descripción de la manzana'
                html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;background-color: #2B2D31;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #6EA4EE;">&nbsp;</p></section></body></html>"""
                texto    = BeautifulSoup(html, 'html.parser')
                with col1:
                    st.markdown(texto, unsafe_allow_html=True)
                with col1:
                    with st.spinner('Descripción de la manzana'):
                        datagroup       = getconfiguracionmanazana(st.session_state.codigomanzana)
                        datamanzanadesc = getmanzanadescripcion(st.session_state.codigomanzana)
                        html = tabla_resumen_manzana(data=datamanzanadesc,databyuso=datagroup)
                        #texto = BeautifulSoup(html, 'html.parser')
                        #st.markdown(texto, unsafe_allow_html=True)
                        st.components.v1.html(html,height=600,scrolling=True)
                        
        #---------------------------------------------------------------------#
        # Mapa 3: Lotes 
        if not st.session_state.data_lotes.empty:
            titulo   = 'Lotes de la manzana'
            html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;background-color: #2B2D31;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #6EA4EE;">Consolida lotes dibujando un poligono</p></section></body></html>"""
            texto    = BeautifulSoup(html, 'html.parser')
            with col2:
                st.markdown(texto, unsafe_allow_html=True)
            
            m3 = folium.Map(location=[st.session_state.latitud, st.session_state.longitud], zoom_start=st.session_state.zoom_start_map3,tiles="cartodbpositron",key='mapa3')

            if not st.session_state.data_lotes.empty:
                geojson  = data2geopandas(st.session_state.data_lotes,link=True)
                popup   = folium.GeoJsonPopup(
                    fields=["popup"],
                    aliases=[""],
                    localize=True,
                    labels=True,
                )
                folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m3)
                #folium.GeoJson(geojson,style_function=style_function_geojson).add_to(m3)

            with col2:
                st_map3 = st_folium(m3,width=int(mapwidth*0.4),height=mapheight)

    #-------------------------------------------------------------------------#
    # Propietarios
    if not st.session_state.data_lotes.empty:
        titulo   = 'Propietarios'
        html     = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;background-color: #2B2D31;"><h1 style="color: #6EA4EE; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #6EA4EE;"> &nbsp;</p></section></body></html>"""
        texto    = BeautifulSoup(html, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)
        
        barmanpre = list(st.session_state.data_lotes['barmanpre'].unique())
        getpropietarios(chip=None,barmanpre=barmanpre,vartype=None,infilter=False)
    
    
@st.cache_data(show_spinner=False)
def data2geopandas(data,color=None,link=False):
    urlexport = "http://urbex.com.co/Busqueda_avanzada"
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        data.index       = range(len(data))
        
        if link:
            for idd,items in data.iterrows():
                            
                urllink = urlexport+f"?type=predio&code={items['barmanpre']}&vartype=barmanpre&token={st.session_state.token}"
                popup_content =  f'''
                <!DOCTYPE html>
                <html>
                    <body>
                        <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                            <a href="{urllink}" target="_blank" style="color: black;">
                                Ver descripción del lote
                            </a>
                        </div>
                    </body>
                </html>
                '''
                data.loc[idd,'popup'] = popup_content
            
        if isinstance(color, str): data['color'] = color #'#5A189A' #'#003F2D'
        else: data['color'] ='#5A189A'
    return data.to_json()


@st.cache_data(show_spinner=False)
def tabla_resumen_manzana(data=pd.DataFrame(),databyuso=pd.DataFrame()):
    html = ""
    tablacomplementaria = ""
    tablatipologia      = ""
    if not data.empty:
        barrio          = data['prenbarrio'].iloc[0] if 'prenbarrio' in data and isinstance(data['prenbarrio'].iloc[0], str) else "Sin información"
        areaterreno     = f"{round(data['preaterre'].iloc[0],0) :,}"  if 'preaterre' in data and (isinstance(data['preaterre'].iloc[0], float) or isinstance(data['preaterre'].iloc[0], int)) else "Sin información"
        areaconstruida  = f"{round(data['preaconst'].iloc[0],0) :,}"  if 'preaconst' in data and (isinstance(data['preaconst'].iloc[0], float) or isinstance(data['preaconst'].iloc[0], int)) else "Sin información"
        estrato         = int(data['estrato'].iloc[0])    if 'estrato' in data and (isinstance(data['estrato'].iloc[0], float) or isinstance(data['estrato'].iloc[0], int)) else "Sin información"
        predios         = int(data['prechip'].iloc[0]) if 'prechip' in data else "Sin información"
        pisos           = int(data['connpisos'].iloc[0])  if 'connpisos' in data and (isinstance(data['connpisos'].iloc[0], float) or isinstance(data['connpisos'].iloc[0], int)) else "Sin información"
        sotanos         = int(data['connsotano'].iloc[0])   if 'connsotano' in data and (isinstance(data['connsotano'].iloc[0], float) or isinstance(data['connsotano'].iloc[0], int)) else "Sin información"  
        construcciones  = int(data['construcciones'].iloc[0])  if 'construcciones' in data and (isinstance(data['construcciones'].iloc[0], float) or isinstance(data['construcciones'].iloc[0], int)) else "Sin información"   
        avaluocatastral = f"${data['avaluo_catastral'].iloc[0]:,.0f}" if 'avaluo_catastral' in data and (isinstance(data['avaluo_catastral'].iloc[0], float) or isinstance(data['avaluo_catastral'].iloc[0], int)) else "Sin información"
        valormt2transacciones = f"${data['valormt2_transacciones'].iloc[0]:,.0f}" if 'valormt2_transacciones' in data and (isinstance(data['valormt2_transacciones'].iloc[0], float) or isinstance(data['valormt2_transacciones'].iloc[0], int)) else "Sin información"
        transacciones   = int(data['transacciones'].iloc[0]) if 'transacciones' in data and (isinstance(data['transacciones'].iloc[0], float) or isinstance(data['transacciones'].iloc[0], int)) else "Sin información"
        propietarios    = int(data['propietarios'].iloc[0]) if 'propietarios' in data and (isinstance(data['propietarios'].iloc[0], float) or isinstance(data['propietarios'].iloc[0], int)) else "Sin información"

        formato    = {'Barrio:': barrio, 'Área del terreno:': areaterreno, 'Área construida:': areaconstruida, 'Estrato:': estrato,'Número de matrículas:':predios, 'Número máximo de pisos:': pisos, 'Número máximo de sótanos:': sotanos, 'Número de construcciones:': construcciones, 'Avalúo catastral:': avaluocatastral, 'Valor por m² de transacciones:': valormt2transacciones, 'Número de transacciones:': transacciones, 'Número de propietarios:': propietarios}

        html_paso = ""
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
        if html_paso!="":
            tablacomplementaria = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Descripción de la manzana</td></tr>{html_paso}</tbody></table></div>"""
            tablacomplementaria = f"""<div class="col-md-12">{tablacomplementaria}</div>"""
  
    if not databyuso.empty:
        html_paso = ""
        databyuso       = databyuso.sort_values(by='preaconst_precuso',ascending=False)
        databyuso.index = range(len(databyuso))
        for i in range(len(databyuso)):
            usosuelo       = databyuso['usosuelo'].iloc[i] if 'usosuelo' in databyuso and isinstance(databyuso['usosuelo'].iloc[i], str) else ''
            predios        = databyuso['predios_precuso'].iloc[i]
            areaterreno    = f"{round(databyuso['preaterre_precuso'].iloc[i],0) :,}"  if 'preaterre_precuso' in databyuso and (isinstance(databyuso['preaterre_precuso'].iloc[i], int) or isinstance(databyuso['preaterre_precuso'].iloc[i], float)) else ''
            areaconstruida = f"{round(databyuso['preaconst_precuso'].iloc[i],0) :,}"  if 'preaconst_precuso' in databyuso and (isinstance(databyuso['preaconst_precuso'].iloc[i], int) or isinstance(databyuso['preaconst_precuso'].iloc[i], float)) else ''

            html_paso += f"""
            <tr>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{usosuelo}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{predios}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaterreno}</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{areaconstruida}</h6></td>
            </tr>
            """
        if html_paso!="":
            html_paso = f"""
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;"></h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Predios</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área de terreno</h6></td>
                <td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">Área construida</h6></td>
            {html_paso}
            """
            tablatipologia = f"""<div class="css-table"><table class="table align-items-center mb-0"><tbody><tr><td colspan="labelsection" style="margin-bottom: 20px;font-family: 'Inter';">Tipologías de activos</td></tr>{html_paso}</tbody></table></div>"""
            tablatipologia = f"""<div class="col-md-12">{tablatipologia}</div>"""

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
                
            }
            .css-table td {
                text-align: left;
                padding: 0;
            }
            .css-table h6 {
                line-height: 1; 
                font-size: 50px;
                padding: 0;
            }
            .css-table td[colspan="labelsection"] {
              text-align: left;
              font-size: 15px;
              color: #6EA4EE;
              font-weight: bold;
              border: none;
              border-bottom: 2px solid #6EA4EE;
              margin-top: 20px;
              display: block;
              font-family: 'Inter';
            }
            .css-table td[colspan="labelsectionborder"] {
              text-align: left;
              border: none;
              border-bottom: 2px solid blue;
              margin-top: 20px;
              display: block;
              padding: 0;
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
            body {
                background-color: transparent;
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
                        {tablacomplementaria}
                        {tablatipologia}
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
