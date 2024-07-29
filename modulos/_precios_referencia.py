import streamlit as st
import pandas as pd
from streamlit_js_eval import streamlit_js_eval
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from data.getlatlng import getlatlng
from data.forecastModels import main as forecast
from data.datacomplemento import main as datacomplemento
from data.getdatabuilding import main as getdatabuilding
from data.getuso_destino import getuso_destino
from data.inmuebleANDusosuelo import inmueble2usosuelo

from modulos._busqueda_avanzada_default import direccion2barmanpre

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
               'reporte_forecast':False
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1, col2 = st.columns(2)
    with col1:
        ciudad = st.selectbox('Ciudad:',options=['Bogotá'])
    with col2:
        direccion = st.text_input('Dirección:',value="")
    with col1:
        tipoinmueble = st.selectbox('Tipo de inmueble:',options=['','Apartamento', 'Bodega', 'Casa','Local','Oficina'])
    with col2:
        areaconstruida = st.number_input('Área construida:',min_value=0,value=0)
        
    habitaciones,banos,garajes = [None]*3
    if any([x for x in ['apartamento','casa'] if x in tipoinmueble.lower()]):
        with col1:
            habitaciones = st.selectbox('Habitaciones:',options=[1,2,3,4,5,6])
        with col2:
            banos = st.selectbox('Baños:',options=[1,2,3,4,5,6])
        with col1:
            garajes = st.selectbox('Garajes:',options=[0,1,2,3,4,5,6])
            
    scacodigo = None
    barmanpre = None
    if isinstance(direccion, str) and direccion!="":
        barmanpre         = direccion2barmanpre(direccion)
        latitud, longitud = [None]*2
        
        if barmanpre is not None:
            scacodigo = barmanpre[0:6]
        else:
            latitud, longitud = getlatlng(f'{direccion},{ciudad},colombia')
            scacodigo         = getscacodigo(latitud=latitud,longitud=longitud)
            
    result = {}
    with col1:
        if st.button('Calcular valores de referencia'):
            with st.spinner('Calculando valores de referencia'):
                
                inputvarventa = {'forecast_xg':0,
                                 'forecast_transacciones':0,
                                 'forecast_listings_activos':0,
                                 'forecast_listings_historicos':0
                                 }
                
                inputvarrenta = {'forecast_xg':0,
                                 'forecast_transacciones':0,
                                 'forecast_listings_activos':0,
                                 'forecast_listings_historicos':0
                                 }
                
                #-------------------------------------------------------------#
                # Listings activos e historicos
                input_complemento =  datacomplemento(barmanpre=barmanpre,latitud=latitud,longitud=longitud,direccion=direccion,polygon=None,precuso=None)
                if 'market_venta' in input_complemento:
                    for i in input_complemento['market_venta']:
                        if 'index' in i and 'valor' in i['index']:
                            if 'activos' in i and i['activos']>0:
                                inputvarventa['forecast_listings_activos'] = i['activos']*areaconstruida
                            if 'historico' in i and i['historico']>0:
                                inputvarventa['forecast_listings_historicos'] = i['historico']*areaconstruida
                if 'market_arriendo' in input_complemento:
                    for i in input_complemento['market_arriendo']:
                        if 'index' in i and 'valor' in i['index']:
                            if 'activos' in i and i['activos']>0:
                                inputvarrenta['forecast_listings_activos'] = i['activos']*areaconstruida
                            if 'historico' in i and i['historico']>0:
                                inputvarrenta['forecast_listings_historicos'] = i['historico']*areaconstruida
 
                #-------------------------------------------------------------#
                # Modelo
                inputvar = {'tipoinmueble': tipoinmueble,'areaconstruida': areaconstruida,'scacodigo':scacodigo,'habitaciones':habitaciones,'banos':banos,'garajes':garajes}
                result   = forecast(inputvar)
                
                if 'xg_forecast_venta' in result: 
                    inputvarventa['forecast_xg'] = result['xg_forecast_venta']
                if 'xg_forecast_venta' in result: 
                    inputvarrenta['forecast_xg'] = result['xg_forecast_arriendo']
                    
                #-------------------------------------------------------------#
                # Cifras generales
                datacatastro,datausosuelo,datalote,datavigencia,datatransacciones = [pd.DataFrame()]*5
                if barmanpre is not None:
                    datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
                
                if not datatransacciones.empty:
                    datapaso = datatransacciones[datatransacciones['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
                    dataprecuso,dataprecdestin = getuso_destino()
                    dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
                    datapaso = datapaso.merge(dataprecuso,on='precuso',how='left',validate='m:1')
                    
                    precuso  = inmueble2usosuelo(tipoinmueble)
                    datapaso = datapaso[datapaso['precuso'].isin(precuso)]
                    datapaso['fecha_documento_publico'] = pd.to_datetime(datapaso['fecha_documento_publico'])
                    
                    filtrofecha = datetime.now() - timedelta(days=365)
                    datapaso    = datapaso[datapaso['fecha_documento_publico']>=filtrofecha]
                    datapaso    = datapaso.sort_values(by='fecha_documento_publico',ascending=False)
                    datapaso    = datapaso.drop_duplicates(subset='docid',keep='first')
                    
                    if not datapaso.empty:
                        datapaso['valormt2']   = datapaso['cuantia']/(datapaso['preaconst']*1.06)
                        valortransaccionesmt2  = datapaso['valormt2'].median()
                        inputvarventa['forecast_transacciones'] = valortransaccionesmt2*areaconstruida

    if result!={}:
        st.write('')
        st.write('')
        html = principal_table(result=result,input_complemento=input_complemento)
        st.components.v1.html(html,height=300,scrolling=True)
        
        if barmanpre is not None:
            col1,col2 = st.columns([0.3,0.7])
            with col1:
                style_button_dir = """
                <style>
                .custom-button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #68c8ed; /* Cambia el color de fondo según tu preferencia */
                    color: #ffffff; 
                    font-weight: bold;
                    text-decoration: none;
                    border-radius: 10px;
                    width: 100%;
                    border: 2px solid #68c8ed; /* Añade el borde como en el estilo de Streamlit */
                    cursor: pointer;
                    text-align: center;
                    letter-spacing: 1px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    margin-bottom: 20px;
                }
                .custom-button:hover {
                    background-color: #21D375; /* Cambia el color de fondo al pasar el ratón */
                    color: black;
                    border: 2px solid #21D375; /* Cambia el color del borde al pasar el ratón */
                }
                </style>
                """
                
                nombre = 'Ir al reporte'
                html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}" class="custom-button" target="_blank">{nombre}</a></body></html>"""
                html = BeautifulSoup(html, 'html.parser')
                st.markdown(html, unsafe_allow_html=True)
                
@st.cache_data(show_spinner=False)
def principal_table(result={},input_complemento={}):
            
    #-------------------------------------------------------------------------#
    # Modulo descriptivo
    #-------------------------------------------------------------------------#

    tablaforecast        = ""
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
    
    #---------------------------------------------------------------------#
    # Seccion forecast
    forecast_venta        = f"${result['xg_forecast_venta']:,.0f}" if 'xg_forecast_venta' in result and (isinstance(result['xg_forecast_venta'], float) or isinstance(result['xg_forecast_venta'], int)) else None
    forecast_venta_mt2    = f"${result['xg_forecast_venta_mt2']:,.0f} m² "  if 'xg_forecast_venta_mt2' in result and (isinstance(result['xg_forecast_venta_mt2'], float) or isinstance(result['xg_forecast_venta_mt2'], int)) else None
    forecast_arriendo     = f"${result['xg_forecast_arriendo']:,.0f}" if 'xg_forecast_arriendo' in result and (isinstance(result['xg_forecast_arriendo'], float) or isinstance(result['xg_forecast_arriendo'], int)) else None
    forecast_arriendo_mt2 = f"${result['xg_forecast_arriendo_mt2']:,.0f} m²" if 'xg_forecast_arriendo_mt2' in result and (isinstance(result['xg_forecast_arriendo_mt2'], float) or isinstance(result['xg_forecast_arriendo_mt2'], int)) else None
    
    #forecast_venta        = result['ann_forecast_venta'] if forecast_venta is None and 'ann_forecast_venta' in result and (isinstance(result['ann_forecast_venta'], float) or isinstance(result['ann_forecast_venta'], int)) else None
    #forecast_venta_mt2    = result['ann_forecast_venta_mt2'] if forecast_venta_mt2 is None and 'ann_forecast_venta_mt2' in result and (isinstance(result['ann_forecast_venta_mt2'], float) or isinstance(result['ann_forecast_venta_mt2'], int)) else None
    #forecast_arriendo     = result['ann_forecast_arriendo'] if forecast_arriendo is None and 'ann_forecast_arriendo' in result and (isinstance(result['ann_forecast_arriendo'], float) or isinstance(result['ann_forecast_arriendo'], int)) else None
    #forecast_arriendo_mt2 = result['ann_forecast_arriendo_mt2'] if forecast_arriendo_mt2 is None and 'ann_forecast_arriendo_mt2' in result and (isinstance(result['ann_forecast_arriendo_mt2'], float) or isinstance(result['ann_forecast_arriendo_mt2'], int)) else None

    formato   = {'Precio de referencia de venta:':forecast_venta,'Precio de referencia de venta por m²:':forecast_venta_mt2,'Precio de referencia de arriendo:':forecast_arriendo,'Precio de referencia de arriendo por m²:':forecast_arriendo_mt2}
    html_paso = ""
    for key,value in formato.items():
        if value is not None:
            html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr><tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>"""
    if html_paso!="":
        labeltable = "Precio de referencia"
        tablaforecast  = f"""
        <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        {html_paso}
        <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
        """
        tablaforecast = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablaforecast}</tbody></table></div></div>"""
        
        
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
                    {tablaforecast}
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
    return html

@st.cache_data(show_spinner=False)
def getscacodigo(latitud=None,longitud=None):
    user      = st.secrets["user_bigdata"]
    password  = st.secrets["password_bigdata"]
    host      = st.secrets["host_bigdata_lectura"]
    schema    = st.secrets["schema_bigdata"]
    engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    scacodigo = None
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        databarrio = pd.read_sql_query(f"SELECT scacodigo,scanombre FROM  bigdata.data_bogota_barriocatastro WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        if not databarrio.empty:
            scacodigo = databarrio['scacodigo'].iloc[0]
    engine.dispose()
    return scacodigo

if __name__ == "__main__":
    main()
