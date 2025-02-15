import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import json
import base64
import urllib.parse
from shapely.geometry import Point
from bs4 import BeautifulSoup

from functions.circle_polygon import circle_polygon
from functions._principal_getdataproyectos import main as dataproyectosnuevos

from display._principal_proyectos_nuevos import main as generar_html_proyectos


def main(data=pd.DataFrame(),latitud=None,longitud=None):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(data=data,latitud=latitud,longitud=longitud)

    return html_content
    
def gethtml(data=pd.DataFrame(),latitud=None,longitud=None):
    
    #-------------------------------------------------------------------------#
    # Mapa
    mapscript = map_function(data, latitud, longitud)

    #-------------------------------------------------------------------------#
    # Inputs
    numerolocacaciones   = len(data)
    titlelocaciones = 'Total locaciones'
    
    numerobarrios = len(data[data['prenbarrio'].notnull()]['prenbarrio'].unique())
    numerobarrios = 'Sin información' if numerobarrios==0 else numerobarrios
    titlebarrios  = '' if numerobarrios=='Sin información' else 'Número de barrios'
    
    #-------------------------------------------------------------------------#
    # Grafica por marcas
    style_chart = ""
    try:    
        df          = data.copy()
        df['id']    = 1
        df          = df.groupby('empresa').agg({'id':'count','marker_color':'first'}).reset_index()
        df.columns  = ['ejex','ejey','color']
        df['ejex']  = df['ejex'].astype(str).str.upper()
        df          = df.sort_values(by=['ejey'],ascending=False)
        if not df.empty:
            style_chart += single_axis_chart(df,'byBrand')
    except: pass

    #-------------------------------------------------------------------------#
    # Tablas 
    #-------------------------------------------------------------------------#
    formato_data = [
        {
            'data': data,
            'columns': ['empresa', 'nombre', 'predirecc', 'prenbarrio', 'mpio_cnmbr'],
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'title': 'Prediales / Avalúos catastrales'
        },
    ]

    tables_html = ""
    for items in formato_data:
        if not items['data'].empty:
            data = items['data']
            
            tables_html += f'''
            <div class="urbex-row">
             <div class="urbex-col" id="box_shadow_default" style="padding: 20px;margin-bottom: 20px;">
              <div class="urbex-table-responsive urbex-text-center" style="max-height: 500px; filter: blur(0px); line-height: 1;margin-bottom: 20px;font-size: 12px;text-align: center;">
               <table class="urbex-table urbex-table-striped urbex-table-sm">
                <thead style="font-size: 16px; position: sticky; top: 0; z-index: 2;">
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
                            <td>
                                <a href="{row['link']}" target="_blank">
                                    <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                </a>
                            </td>
                        '''
                    elif any([x for x in ['cuantia','avaluo_catastral','impuesto_predial'] if col in x]) and not pd.isna(row.get(col)) and isinstance(row.get(col), (int, float)):
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
    
      <section>
       <div class="urbex-container-fluid">
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-lg-5">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 900px;">
           <div id="leaflet-map-marcas" style="height: 100%;"></div>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-lg-7">
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {numerolocacaciones}
             </p>
             <p id="label_style">
              {titlelocaciones}
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-d-flex" id="box_shadow_default">
             <p id="number_style">
              {numerobarrios}
             </p>
             <p id="label_style">
              {titlebarrios}
             </p>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col urbex-p-2" style="min-height: 330px;">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <canvas id="byBrand" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
          {tables_html}
         </div>
        </div>
       </div>
      </section>
      {mapscript}
      {style_chart}
    </body>
    </html>
    """

    return html 

def single_axis_chart(df, name):
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    
    <canvas id="{name}" width="400" height="400"></canvas>
    <script>
    Chart.register(ChartDataLabels);
    var ctx = document.getElementById('{name}').getContext('2d');
    var {name} = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {df['ejex'].tolist()},
            datasets: [{{
                data: {df['ejey'].tolist()},
                backgroundColor: {df['color'].tolist()},
                borderColor: {df['color'].tolist()},
                borderWidth: 1
            }}]
        }},
        options: {{
            plugins: {{
                datalabels: {{
                    color: 'white',
                    anchor: 'center',
                    align: 'center',
                    rotation: -90,
                    font: {{
                        weight: 'bold',
                        size: 10
                    }},
                    formatter: function(value, context) {{
                        return Math.round(value).toLocaleString();
                    }},
                    display: function(context) {{
                        var index = context.dataIndex;
                        var value = context.dataset.data[index];
                        var maxValue = Math.max(...context.dataset.data);
                        return value / maxValue > 0.1;  // Mostrar solo si el valor es más del 10% del máximo
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {{
                        boxWidth: 20,
                        padding: 15,
                    }}
                }}
            }},
            scales: {{
                y: {{
                    type: 'linear',
                    position: 'left',
                    grid: {{ display: false }},
                    title: {{
                        display: false
                    }},
                    ticks: {{
                        callback: function(value, index, values) {{
                            return Math.round(value).toLocaleString();
                        }}
                    }}
                }},
                x: {{
                    grid: {{ display: false }},
                    title: {{
                        display: false
                    }}
                }}
            }},
            responsive: true,
            maintainAspectRatio: false,
            title: {{
                display: true,
                text: 'Gráfico de Valores por Año',
                position: 'bottom',
                align: 'start',
                font: {{
                    size: 16
                }}
            }}
        }}
    }});
    </script>
    """
    
def pie_chart(df, name, title=''):

    colors = ['#4A148C', '#7B1FA2', '#9C27B0', '#BA68C8', '#E1BEE7',
              '#006837', '#66BD63', '#D9EF8B', '#00ACC1', '#4DD0E1', '#B2EBF2']
    
    #colors = ['#77CFF3', '#86cff4', '#96d0f6', '#a6d0f7', '#b6d1f9', 
    #          '#c5d2fa', '#dad2fc', '#D2EEFF', '#DFF3FF', '#DFD3FD']
    
    while len(colors) < len(df):
        colors.extend(colors)

    df = df.copy()
    df['color'] = colors[:len(df)]
    df = df.sort_values(by='ejey').copy()
    
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    
    <div style="height: 400px; width: 100%;">
        <canvas id="{name}"></canvas>
    </div>
    
    <script>
    (function() {{
        Chart.register(ChartDataLabels);
        
        new Chart(document.getElementById('{name}'), {{
            type: 'pie',
            data: {{
                labels: {df['ejex'].tolist()},
                datasets: [{{
                    data: {df['ejey'].tolist()},
                    backgroundColor: {df['color'].tolist()},
                    borderColor: 'white',
                    borderWidth: 1
                }}]
            }},
            options: {{
                plugins: {{
                    datalabels: {{
                        color: 'white',
                        font: {{ size: 12, weight: 'bold' }},
                        formatter: function(value, context) {{
                            var total = context.dataset.data.reduce((a, b) => a + b, 0);
                            var percentage = Math.round((value / total) * 100);
                            return context.chart.data.labels[context.dataIndex] + '\\n(' + percentage + '%)';
                        }}
                    }},
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{ size: 12 }}
                        }}
                    }},
                    title: {{
                        display: true,
                        text: '{title}',
                        font: {{ size: 16, weight: 'bold' }},
                        padding: 20
                    }}
                }},
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
    }})();
    </script>
    """
    
def map_function(data, latitud, longitud):
    map_leaflet = ""
    if isinstance(latitud, (float,int)) and isinstance(longitud, (float,int)):
        #---------------------------------------------------------------------#
        # Puntos de las marcas
        geopoints = point2geopandas(data)        
        map_leaflet = mapa_leaflet(latitud, longitud, geopoints)

    return map_leaflet

def mapa_leaflet(latitud, longitud, geopoints):
    html_mapa_leaflet = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonPoints = {geopoints};

            var map_leaflet_proyectos = L.map('leaflet-map-marcas').setView([{latitud}, {longitud}], 12);
            
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 22
            }}).addTo(map_leaflet_proyectos);
    
            // Crear marcadores personalizados para cada punto en geopoints
            geojsonPoints.features.forEach(function(feature) {{
                var latlng = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]];  // [lat, lng]
                var iconUrl = feature.properties.marker;  // URL del icono del marcador
                
                var customIcon = L.icon({{
                    iconUrl: iconUrl,
                    iconSize: [30, 30],  // Ajusta el tamaño del icono según sea necesario
                    iconAnchor: [15, 30],  // Ajusta el punto de anclaje del icono
                }});
                
                var marker = L.marker(latlng, {{ icon: customIcon }}).addTo(map_leaflet_proyectos);
                
                // Popup para el marcador basado en el atributo "popup"
                marker.bindPopup(feature.properties.popup || 'Información no disponible');
            }});
        </script>
    """
    return html_mapa_leaflet

@st.cache_data(show_spinner=False)
def point2geopandas(data):
    
    geojson = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty and 'latitud' in data and 'longitud' in data:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = None
        urlexport        = "http://localhost:8501/Reporte"

        for idd,items in data.iterrows():

            try:    empresa = f"<b> Empresa:</b> {items['empresa']}<br>" if isinstance(items['empresa'],str) and items['empresa']!='' else 'Sin información'
            except: empresa = "<b> Empresa:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>" if isinstance(items['direccion'],str) and items['direccion']!='' else 'Sin información'
            except: direccion = "<b> Dirección:</b> Sin información <br>" 
            try:    nombre = f"<b> Nombre:</b> {items['nombre']}<br>" if isinstance(items['nombre'],str) and items['nombre']!='' else 'Sin información'
            except: nombre = "<b> Nombre:</b> Sin información <br>" 
            try:    barrio = f"<b> Barrio:</b> {items['prenbarrio']}<br>" if isinstance(items['prenbarrio'],str) and items['prenbarrio']!='' else 'Sin información'
            except: barrio = "<b> Barrio:</b> Sin información <br>"      
            
            popup_content = ""
            if 'barmanpre' in items and isinstance(items['barmanpre'],str) and items['barmanpre']!='':
                params       = {'type':'predio','grupo':int(items['grupo']) if 'grupo' in items and not pd.isna(items['grupo']) and isinstance(items['grupo'],(int,float)) else None,'barmanpre':items['barmanpre'],'token':st.session_state.token}
                params       = json.dumps(params)
                params       = base64.urlsafe_b64encode(params.encode()).decode()
                params       = urllib.parse.urlencode({'token': params})
                urllink      = f"{urlexport}?{params}"
                
                popup_content =  f'''
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                    <h5 style="text-align: center; margin-bottom: 10px;">Detalle del predio:</h5>
                    <a href="{urllink}" target="_blank" style="color: black;">
                        {empresa}
                        {direccion}
                        {nombre}
                        {barrio}
                    </a>
                </div>
                '''
            
            if 'radio' in items and isinstance(items['radio'],str) and items['radio']!='':
                urllink = f"http://localhost:8501/Busqueda_avanzada?type=marcaradio&code={items['id']}&vartype=id&token={st.session_state.token}"
                popup_content +=  f'''
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                    <h5 style="text-align: center; margin-bottom: 10px;">Análisis de radio:</h5>
                    <a href="{urllink}" target="_blank" style="color: black;">
                        <b> Empresa:</b> {items['empresa']}<br>
                        <b> Nombre:</b> {items['nombre']}<br>
                        <b> Dirección:</b> {items['direccion']}<br>
                    </a>
                </div>
                '''
            if popup_content=='':
                popup_content =  f'''
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:250px;font-size: 12px;">
                    {empresa}
                    {direccion}
                    {nombre}
                    {barrio}
                </div>
                '''
                
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    {popup_content}
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        data    = data[['geometry','popup','marker']]
        geojson = data.to_json()
        
    return geojson