import streamlit as st
import pandas as pd
import shapely.wkt as wkt
from bs4 import BeautifulSoup

from functions._principal_getdatareporte import main as getadatareporte
from functions._principal_getunidades import main as getadataunidades
from functions._principal_getdatanalisis import main as getradio

from display._principal_reporte_general import main as generar_html_detalle_building
from display._principal_detalle_unidad import main as generar_html_detalle_unidad
from display._principal_estudio_mercado import main as generar_html_estudio_mercado


def main(grupo=None,chip_referencia=None,metros=500):

    #---------------------------------------------------------------------#
    # Detalle general
    #---------------------------------------------------------------------#
    formato_outputs, data_lote, data_predios, data_transacciones, data_listings, datactl, datalicencias, formato_estadisticas, data_transacciones_historicas, data_construcciones = getadatareporte(grupo)

    try:
        datageometry = data_lote.copy()
        latitud      = datageometry['latitud'].iloc[0] if 'latitud' in datageometry and isinstance(datageometry['latitud'].iloc[0],(float,int)) else None
        longitud     = datageometry['longitud'].iloc[0] if 'longitud' in datageometry and isinstance(datageometry['longitud'].iloc[0],(float,int)) else None
        polygon      = wkt.loads(datageometry['wkt'].iloc[0])
    except: 
        latitud  = None
        longitud = None
        polygon  = None
        
    html_detalle_general = generar_html_detalle_building(formato_outputs,data_predios,data_transacciones,data_listings,latitud, longitud, polygon, grupo=grupo)
    soup                 = BeautifulSoup(html_detalle_general, 'html.parser')
    html_detalle_general = soup.body.decode_contents() if soup.body else ''
    
    #---------------------------------------------------------------------#
    # Detalle unidad
    #---------------------------------------------------------------------#
    data_predios, data_usosuelopredios, data_prediales, data_anotaciones, datapropietarios  = getadataunidades(grupo=grupo)

    data_predios         = pd.DataFrame(data_predios)
    data_prediales       = pd.DataFrame(data_prediales)
    data_usosuelopredios = pd.DataFrame(data_usosuelopredios)
    data_anotaciones     = pd.DataFrame(data_anotaciones)
        
    arealote = int(data_usosuelopredios['preaterre_precuso'].sum()) if not data_usosuelopredios.empty and 'preaterre_precuso' in data_usosuelopredios else 2500

    if isinstance(chip_referencia,str) and chip_referencia!='':
        data_predios     = data_predios[data_predios['prechip']==chip_referencia]      if not data_predios.empty and 'prechip' in data_predios else pd.DataFrame(columns=['barmanpre', 'predirecc', 'precuso', 'prechip', 'precedcata', 'preaconst', 'preaterre', 'matriculainmobiliaria', 'usosuelo'])
        data_prediales   = data_prediales[data_prediales['chip']==chip_referencia]     if not data_prediales.empty and 'chip' in data_prediales else pd.DataFrame(columns=['chip', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'impuesto_total', 'preaconst', 'preaterre', 'precuso', 'barmanpre', 'indPago', 'fechaPresentacion', 'nomBanco'])
        data_anotaciones = data_anotaciones[data_anotaciones['chip']==chip_referencia] if not data_anotaciones.empty and 'chip' in data_anotaciones else pd.DataFrame(columns=['docid', 'chip', 'codigo', 'cuantia', 'entidad', 'fecha_documento_publico', 'nombre', 'numero_documento_publico', 'oficina', 'preaconst', 'preaterre', 'precuso', 'predirecc', 'tipo_documento_publico', 'titular', 'email', 'tipo', 'nrodocumento', 'grupo', 'barmanpre'])
        data_usosuelopredios = data_usosuelopredios[data_usosuelopredios['precuso'].isin(data_predios['precuso'])] if not data_usosuelopredios.empty and 'precuso' in data_usosuelopredios else pd.DataFrame(columns=['formato_direccion', 'precuso', 'predios_precuso', 'preaconst_precuso', 'preaconst_precusomin', 'preaconst_precusomax', 'preaterre_precuso', 'preaterre_precusomin', 'preaterre_precusomax', 'barmanpre', 'usosuelo'])
        
    html_detalle_unidad = generar_html_detalle_unidad(data_predio=data_predios, data_prediales=data_prediales, data_transacciones=data_anotaciones, data_usosuelopredios=data_usosuelopredios)
    soup                = BeautifulSoup(html_detalle_unidad, 'html.parser')
    html_detalle_unidad = soup.body.decode_contents() if soup.body else ''

    #-------------------------------------------------------------------------#
    # Estudio de mercado
    #-------------------------------------------------------------------------#
    output,data_lote,data_geometry = getradio(grupo=grupo,inputvar={})
    
    try:
        datageometry = data_lote.copy()
        latitud      = datageometry['latitud'].iloc[0] if 'latitud' in datageometry and isinstance(datageometry['latitud'].iloc[0],(float,int)) else None
        longitud     = datageometry['longitud'].iloc[0] if 'longitud' in datageometry and isinstance(datageometry['longitud'].iloc[0],(float,int)) else None
        polygon      = wkt.loads(datageometry['wkt'].iloc[0])
    except: 
        latitud  = None
        longitud = None
        polygon  = None
        
    if not data_geometry.empty and 'distancia' in data_geometry: 
        data_geometry = data_geometry[data_geometry['distancia']<=metros]
    
    html_estudio_mercado = generar_html_estudio_mercado(grupo,output[metros],datageometry=data_geometry,latitud=latitud,longitud=longitud,polygon=polygon,metros=metros)
    soup                 = BeautifulSoup(html_estudio_mercado, 'html.parser')
    html_estudio_mercado = soup.body.decode_contents() if soup.body else ''


    #-------------------------------------------------------------------------#
    # Estudio de mercado
    #-------------------------------------------------------------------------#
    html = f"""
    <!DOCTYPE html>
    <html data-bs-theme="light" lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/prefixed_styles.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_unidad/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_unidad/prefixed_styles.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_estudio_mercado/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <style>
        .urbex-table th, .urbex-table td {{
            white-space: nowrap;
            min-width: fit-content;
            padding: 0.5rem !important;
        }}
        
        .urbex-table-wrapper {{
            overflow-x: auto;
            width: 100%;
        }}
    
        .urbex-table thead {{
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        
        body {{
            background-color: #fff;
        }}
            
        .urbex-panel {{
                     background-color: white;
                     box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                     border-radius: 8px;
                     height: 100%;
                     padding: 15px;
                 }}
    
         .value {{
             font-size: 1.6em;
             font-weight: bold;
             text-align: center;
         }}
         
         .subtext {{
             font-size: 0.9em;
             color: #666;
             text-align: center;
         }}
         
         #seccion_title {{
           color: #A16CFF;
           text-align: center;
           font-size: 25px;
           margin-bottom: 20px;
           font-weight: bold;
         }}
    </style>
 
    </head>
    <body>
        {html_detalle_general}
        {html_detalle_unidad}
        {html_estudio_mercado}
        <script src="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/bootstrap.min.js"></script>
    </body>
    </html>
    """    
    return html
