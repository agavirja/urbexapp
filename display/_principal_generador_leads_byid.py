import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
from shapely.geometry import Point
from bs4 import BeautifulSoup

from functions.circle_polygon import circle_polygon
from functions._principal_getdataproyectos import main as dataproyectosnuevos

from display._principal_proyectos_nuevos import main as generar_html_proyectos


def main(dataresult=pd.DataFrame(), data_predios=pd.DataFrame(), data_transacciones=pd.DataFrame(), data_transacciones_nal=pd.DataFrame(), data_shd_historico=pd.DataFrame(), data_vehiculos=pd.DataFrame()):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(dataresult=dataresult, data_predios=data_predios, data_transacciones=data_transacciones, data_transacciones_nal=data_transacciones_nal, data_shd_historico=data_shd_historico, data_vehiculos=data_vehiculos)

    return html_content
    
def gethtml(dataresult=pd.DataFrame(), data_predios=pd.DataFrame(), data_transacciones=pd.DataFrame(), data_transacciones_nal=pd.DataFrame(), data_shd_historico=pd.DataFrame(), data_vehiculos=pd.DataFrame()):
    

    mapscript = ""


    #-------------------------------------------------------------------------#
    # Inmuebles activos
    #-------------------------------------------------------------------------#
    html_data_predios = ""
    if not data_predios.empty:
        
        # Mapa: 
        if 'wkt' in data_predios:
            df = data_predios[data_predios['wkt'].notnull()]
            if not df.empty:
                
                df         = df.groupby(['scacodigo']).agg({'grupo':'count','wkt':'first'}).reset_index()
                df.columns = ['scacodigo','count','wkt']
                
                df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt'])
                df             = gpd.GeoDataFrame(df, geometry='geometry')
                
                df['rank']  = df['count'].rank(method='min')
                df['rank']  = (df['rank'] - df['rank'].min()) / (df['rank'].max() - df['rank'].min())
                cmap        = plt.cm.RdYlGn_r
                df['color'] = df['rank'].apply(lambda x: mcolors.to_hex(cmap(x)))

                geojson     = df[['geometry','color']].to_json()
                
                latitud  = 4.687152
                longitud = -74.056829

                mapscript += mapa_leaflet(latitud, longitud, geojson, 'mapaactivos',12)
                
                html_data_predios += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                   <div id="mapaactivos" style="height: 100%;"></div>
                  </div>
                 </div>
                """
                
        if html_data_predios=="":
                html_data_predios += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                  </div>
                 </div>
                """
                
        # Cifras:
        html_data_predios += f"""
         <div class="urbex-col-12 urbex-col-lg-7">
         <div class="urbex-row">
             <div class="urbex-col">
               <div>
                 <h1 id="seccion_title_tabla">Inmuebles actuales en Bogotá</h1>
               </div>
             </div>
         </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {len(data_predios)}
             </p>
             <p id="label_style">
              Inmuebles activos
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-d-flex" id="box_shadow_default">
             <p id="number_style">
              {"${:,.0f}".format(data_predios['avaluo_catastral'].sum())}
             </p>
             <p id="label_style">
              Valor total de los inmuebles
             </p>
             <p id="label_style">
             (avalúo catastral)
             </p>
            </div>
           </div>
          </div>
        """
        
        # Tabla
        formato_data = [
            {
                'data': data_predios,
                'columns': ['direccion', 'chip', 'matriculainmobiliaria','avaluo_catastral', 'impuesto_predial', 'preaconst'],
                'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
                'title': 'Inmuebles actuales'
            },
        ]
        html_data_predios += getatble(formato_data)
        
    if isinstance(html_data_predios,str) and html_data_predios!="":
        html_data_predios = f"""
          <section style="margin-bottom: 50px;">
           <div class="urbex-container-fluid">
            <div class="urbex-row">
                {html_data_predios}
                </div>
            </div>
           </div>
          </section>
        """
                
            
    #-------------------------------------------------------------------------#
    # Transaccion de inmuebles
    #-------------------------------------------------------------------------#
    html_data_transacciones = ""
    if not data_transacciones.empty:
        
        # Mapa: 
        if 'wkt' in data_transacciones:
            df = data_transacciones[data_transacciones['wkt'].notnull()]
            if not df.empty:
                
                df = df.groupby(['scacodigo']).agg({'grupo':'count','wkt':'first'}).reset_index()
                df.columns = ['scacodigo','count','wkt']
                
                df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt'])
                df             = gpd.GeoDataFrame(df, geometry='geometry')
                
                df['rank']  = df['count'].rank(method='min')
                df['rank']  = (df['rank'] - df['rank'].min()) / (df['rank'].max() - df['rank'].min())
                cmap        = plt.cm.RdYlGn_r
                df['color'] = df['rank'].apply(lambda x: mcolors.to_hex(cmap(x)))

                geojson     = df[['geometry','color']].to_json()
                latitud     = 4.687152
                longitud    = -74.056829
                mapscript += mapa_leaflet(latitud, longitud, geojson, 'mapatransacciones',12)
                
                html_data_transacciones += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                   <div id="mapatransacciones" style="height: 100%;"></div>
                  </div>
                 </div>
                """
                
        if html_data_transacciones=="":
                html_data_transacciones += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                  </div>
                 </div>
                """
                
        # Cifras:
        df = data_transacciones[data_transacciones['codigo'].isin(['125','126','164','168','169','0125','0126','0164','0168','0169'])]
        

        if not df.empty:
            df = df.groupby(['docid']).agg({'cuantia':['count','max']}).reset_index()
            df.columns = ['docid','conteo','cuantia']
        
            html_data_transacciones += f"""
             <div class="urbex-col-12 urbex-col-lg-7">
                <div class="urbex-row">
                    <div class="urbex-col">
                      <div>
                        <h1 id="seccion_title_tabla">Transacciones en Bogotá</h1>
                      </div>
                    </div>
                </div>
              <div class="urbex-row">
               <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
                <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                 <p id="number_style">
                  {len(df)}
                 </p>
                 <p id="label_style">
                  Transacciones
                 </p>
                 <p id="label_style">
                  (desde el 2019 a la fecha)
                 </p>
                </div>
               </div>
               <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
                <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-d-flex" id="box_shadow_default">
                 <p id="number_style">
                  {"${:,.0f}".format(df['cuantia'].sum())}
                 </p>
                 <p id="label_style">
                  Valor total de las transacciones
                 </p>
                </div>
               </div>
              </div>
            """
        else: 
            html_data_transacciones += """
             <div class="urbex-col-12 urbex-col-lg-7">
                <div class="urbex-row">
                    <div class="urbex-col">
                      <div>
                        <h1 id="seccion_title_tabla">Transacciones en Bogotá</h1>
                      </div>
                    </div>
                </div>
            </div>
            """
            
        # Tabla
        data_transacciones['link'] = data_transacciones['docid'].apply(
            lambda x: f"https://radicacion.supernotariado.gov.co/app/static/ServletFilesViewer?docId={x}"
        ) if 'docid' in data_transacciones else ''
        
        formato_data = [
            {
                'data': data_transacciones,
                'columns': ['Link', 'predirecc', 'codigo', 'nombre', 'cuantia', 'preaconst','matriculainmobiliaria', 'fecha_documento_publico','tipo_documento_publico','oficina','entidad','numero_documento_publico'],
                'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
                'title': 'Inmuebles actuales'
            },
        ]
        html_data_transacciones += getatble(formato_data)
        
    if isinstance(html_data_transacciones,str) and html_data_transacciones!="":
        html_data_transacciones = f"""
          <section style="margin-bottom: 50px;">
           <div class="urbex-container-fluid">
            <div class="urbex-row">
                {html_data_transacciones}
                </div>
            </div>
           </div>
          </section>
        """
            
    #-------------------------------------------------------------------------#
    # Historico inmuebles SHD
    #-------------------------------------------------------------------------#
    html_data_shd_historico = ""
    if not data_shd_historico.empty:
        
        # Mapa: 
        if 'wkt' in data_shd_historico:
            df = data_shd_historico[data_shd_historico['wkt'].notnull()]
            if not df.empty:
                df         = df.groupby(['scacodigo']).agg({'grupo':'count','wkt':'first'}).reset_index()
                df.columns = ['scacodigo','count','wkt']
                
                df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt'])
                df             = gpd.GeoDataFrame(df, geometry='geometry')
                
                df['rank']  = df['count'].rank(method='min')
                df['rank']  = (df['rank'] - df['rank'].min()) / (df['rank'].max() - df['rank'].min())
                cmap        = plt.cm.RdYlGn_r
                df['color'] = df['rank'].apply(lambda x: mcolors.to_hex(cmap(x)))

                geojson     = df[['geometry','color']].to_json()
                latitud     = 4.687152
                longitud    = -74.056829
                mapscript += mapa_leaflet(latitud, longitud, geojson, 'mapashdhistorico',12)
                
                html_data_shd_historico += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                   <div id="mapashdhistorico" style="height: 100%;"></div>
                  </div>
                 </div>
                """
        if html_data_shd_historico=="":
                html_data_shd_historico += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                  </div>
                 </div>
                """
                
        # Cifras:
        df = data_shd_historico.copy()
        if 'chip' in df and 'vigencia' in df:
            df = df.sort_values(by=['vigencia','chip'],ascending=False).drop_duplicates(subset=['chip'],keep='first')
            
        html_data_shd_historico += f"""
         <div class="urbex-col-12 urbex-col-lg-7">
         <div class="urbex-row">
             <div class="urbex-col">
               <div>
                 <h1 id="seccion_title_tabla">Inmuebles históricos en Bogotá</h1>
               </div>
             </div>
         </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {len(df)}
             </p>
             <p id="label_style">
              Total inmuebles
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-d-flex" id="box_shadow_default">
             <p id="number_style">
                 {"${:,.0f}".format(df['valorAutoavaluo'].sum())}
             </p>
             <p id="label_style">
              Valor total catastral
             </p>
             <p id="label_style">
              Últimos avalúos
             </p>
            </div>
           </div>
          </div>
        """
        
        # Tabla
        formato_data = [
            {
                'data': data_shd_historico,
                'columns': ['direccionPredio','vigencia','chip','valorAutoavaluo','valorImpuesto','indPago'],
                'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
                'title': 'Inmuebles actuales'
            },
        ]
        html_data_shd_historico += getatble(formato_data)
        
    if isinstance(html_data_shd_historico,str) and html_data_shd_historico!="":
        html_data_shd_historico = f"""
          <section style="margin-bottom: 50px;">
           <div class="urbex-container-fluid">
            <div class="urbex-row">
                {html_data_shd_historico}
                </div>
            </div>
           </div>
          </section>
        """

    #-------------------------------------------------------------------------#
    # Total transacciones
    #-------------------------------------------------------------------------#
    tables_html = ""
    if not data_transacciones_nal.empty:
        
        df   = data_transacciones_nal.copy()
        item = 'procesos'
        if item in df:
            df         = df[['docid',item]]
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'docid': x['docid']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                
                df['nombre'] = df['nombre'].astype(str)
                df['codigo'] = df['codigo'].astype(str)
                df = df.groupby('docid').agg({'nombre': lambda x: ' | '.join(x),'codigo': lambda x: ' | '.join(x),'cuantia': 'max'}).reset_index()
                df.rename(columns={'nombre':'proceso'},inplace=True)
                data_transacciones_nal = data_transacciones_nal.merge(df,on='docid',how='left',validate='m:1')
        
        for i in ['proceso', 'codigo', 'cuantia']:
            if i not in data_transacciones_nal: data_transacciones_nal[i] = None
            
        fulltable = 'style="max-height: 500px; filter: blur(0px); line-height: 1;"'
        
        data_transacciones_nal['link'] = data_transacciones_nal['docid'].apply(
            lambda x: f"https://radicacion.supernotariado.gov.co/app/static/ServletFilesViewer?docId={x}"
        ) if 'docid' in data_transacciones_nal else ''
    
        formato_data = [
            {
                'data': data_transacciones_nal,
                'columns': ['Link', 'fecha', 'codigo','proceso', 'cuantia', 'tipo_documento_publico', 'numero_documento_publico','oficina','entidad'],
                'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
                'filtercolumn': 'fecha',
                'title': '<p>Total Transacciones</p><p>[desde 2019 a la fecha]</p>'
            },
        ]
        for items in formato_data:
            if not items['data'].empty:
                data = items['data'].sort_values(by=items['filtercolumn'], ascending=True)
                
                tables_html += f'''
                <section>
                    <div class="urbex-container">
                        <div class="urbex-row urbex-p-3">
                            <div class="urbex-col" style="font-size: 14px;">
                                <h1 id="seccion_title">{items['title']}</h1>
                                <div class="urbex-table-responsive urbex-text-center urbex-shadow" {fulltable}>
                                    <table class="urbex-table urbex-table-striped urbex-table-sm urbex-table-bordered">
                                        <thead class="urbex-bg-primary urbex-text-white" style="font-size: 16px;; position: sticky; top: 0; z-index: 2;">
                                            <tr>
                                                {''.join(f'<th id="table-header-style">{col}</th>' for col in items['columns'])}
                                            </tr>
                                        </thead>
                                        <tbody>
                '''
                
                for _, row in data.iterrows():
                    tables_html += "<tr>"
                    for col in items['columns']:
                        if col == 'Link':
                            tables_html += f'''
                                <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    <a href="{row['link']}" target="_blank">
                                        <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                    </a>
                                </td>
                            '''
                        elif col == 'cuantia' and isinstance(row.get(col), (int, float)):
                            tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${row[col]:,.0f}</td>'''
                        elif not pd.isna(row.get(col)):
                            tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row.get(col, '')}</td>'''
                        else:
                            tables_html += '''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"></td>'''
                    tables_html += "</tr>"
                
                tables_html += '''
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                '''

    #-------------------------------------------------------------------------#
    # Vehiculos
    #-------------------------------------------------------------------------#
    tables_html_vehiculos = ""
    if not data_vehiculos.empty:
       
        fulltable = 'style="max-height: 500px; filter: blur(0px); line-height: 1;"'

        formato_data = [
            {
                'data': data_vehiculos,
                'columns': ['marca','linea','modelo', 'placa', 'carroceria','clase','capcacidadCarga','porcentajeRespon','responsable','tipoServicio'],
                'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
                'title': 'Vehículos'
            },
        ]
        for items in formato_data:
            if not items['data'].empty:
                data = items['data'].copy()
                tables_html_vehiculos += f'''
                <section>
                    <div class="urbex-container">
                        <div class="urbex-row urbex-p-3">
                            <div class="urbex-col" style="font-size: 14px;">
                                <h1 id="seccion_title">{items['title']}</h1>
                                <div class="urbex-table-responsive urbex-text-center urbex-shadow" {fulltable}>
                                    <table class="urbex-table urbex-table-striped urbex-table-sm urbex-table-bordered">
                                        <thead class="urbex-bg-primary urbex-text-white" style="font-size: 16px;; position: sticky; top: 0; z-index: 2;">
                                            <tr>
                                                {''.join(f'<th id="table-header-style">{col}</th>' for col in items['columns'])}
                                            </tr>
                                        </thead>
                                        <tbody>
                '''
                
                for _, row in data.iterrows():
                    tables_html_vehiculos += "<tr>"
                    for col in items['columns']:
                        if col == 'Link':
                            tables_html_vehiculos += f'''
                                <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    <a href="{row['link']}" target="_blank">
                                        <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                    </a>
                                </td>
                            '''
                        elif col == 'cuantia' and isinstance(row.get(col), (int, float)):
                            tables_html_vehiculos += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${row[col]:,.0f}</td>'''
                        elif not pd.isna(row.get(col)):
                            tables_html_vehiculos += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row.get(col, '')}</td>'''
                        else:
                            tables_html_vehiculos += '''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"></td>'''
                    tables_html_vehiculos += "</tr>"
                
                tables_html_vehiculos += '''
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                '''
                
    html = f"""
    <!DOCTYPE html>
    <html data-bs-theme="light" lang="en">
     <head>
      <meta charset="utf-8"/>
      <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
      <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
      <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
     </head>
     <body>
     
         {html_data_predios}
         {html_data_shd_historico}
         {html_data_transacciones}
         {tables_html}
         {tables_html_vehiculos}
         {mapscript}
     </body>
    </html>
    """

    return html 



def mapa_leaflet(latitud, longitud, geojson, idname, zoom):
    html_mapa_leaflet = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonData = {geojson};
    
            var map_leaflet = L.map('{idname}').setView([{latitud}, {longitud}], {zoom});
            
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 20
            }}).addTo(map_leaflet);
    
            function style(feature) {{
                return {{
                    color: feature.properties.color || '#3388ff',  // Usa el color definido en las propiedades del GeoJSON
                    weight: 1,
                    fillOpacity: 0.4,
                }};
            }}
    
            function onEachFeature(feature, layer) {{
                if (feature.properties && feature.properties.popup) {{
                    layer.bindPopup(feature.properties.popup);
                }}
            }}
    
            L.geoJSON(geojsonData, {{
                style: style,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet);
        </script>
    """
    return html_mapa_leaflet


def getatble(formato_data):
    
    fulltable  = 'style="max-height: 400px;filter: blur(0px);line-height: 1;margin-bottom: 20px;font-size: 12px;text-align: center;"'
    pdfversion = False
    if pdfversion: fulltable = ''

    tables_html = ""
    for items in formato_data:
        if not items['data'].empty:

            # Contenedor de la tabla
            tables_html += '''
            <div class="urbex-row">
                <div class="urbex-col" id="box_shadow_default" style="padding: 20px;margin-bottom: 20px;">
                    <div class="urbex-table-responsive urbex-text-center" style="max-height: 400px; overflow-y: auto; margin-bottom: 20px; font-size: 12px; text-align: center;">
                        <table class="urbex-table urbex-table-striped urbex-table-sm" style="border-collapse: collapse; width: 100%;">
                            <thead style="position: sticky; top: 0; background: white; z-index: 2;">
                                <tr>
            '''
            
            # Encabezados de la tabla
            tables_html += ''.join(f'<th id="table-header-style">{col}</th>' for col in items['columns'])
            
            tables_html += '''
                                </tr>
                            </thead>
                            <tbody>
            '''
            
            # Filas de datos
            data = items['data']
            for _, row in data.iterrows():
                tables_html += "<tr>"
                for col in items['columns']:
                    if col == 'Link':
                        tables_html += f'''
                            <td>
                                <a href="{row['link']}" target="_blank">
                                    <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                </a>
                            </td>
                        '''
                    elif any([x for x in ['cuantia','avaluo_catastral','impuesto_predial','valorAutoavaluo','valorImpuesto'] if col in x]) and not pd.isna(row.get(col)) and isinstance(row.get(col), (int, float)):
                        tables_html += f"<td>${row[col]:,.0f}</td>"
                    else:
                        value = row.get(col, '')
                        value = '' if pd.isna(value) else value
                        tables_html += f"<td>{value}</td>"
                tables_html += "</tr>"
            
            tables_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''
    return tables_html
