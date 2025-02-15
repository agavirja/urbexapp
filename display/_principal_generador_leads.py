import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from shapely.geometry import Point
from bs4 import BeautifulSoup

from functions.circle_polygon import circle_polygon
from functions._principal_getdataproyectos import main as dataproyectosnuevos

from display._principal_proyectos_nuevos import main as generar_html_proyectos


def main(data=pd.DataFrame() , datageometry=pd.DataFrame(),latitud=None,longitud=None, polygon=None):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(data=data, datageometry=datageometry, latitud=latitud, longitud=longitud, polygon=polygon)

    return html_content
    
def gethtml(data=pd.DataFrame(), datageometry=pd.DataFrame(),latitud=None,longitud=None, polygon=None):
    

    mapscript = map_function(datageometry,latitud, longitud, polygon=polygon)

    numclientes      = len(data['numero'].unique()) if not data.empty and 'numero' in data else 0
    labelnumclientes = 'Propietarios únicos' if isinstance(numclientes,int) and numclientes>0 else ''
    numemails        = ''
    try:
        df          = data.copy()
        df['email'] = df['email'].str.split('|')
        df          = df.explode('email')
        df['email'] = df['email'].str.strip()
        numemails   = len(df['email'].unique()) if not df.empty and 'email' in df else 0
    except: pass
    labelnumemails = 'Emails unicos' if isinstance(numemails,int) and numemails>0 else ''
    
    numcreditos       = data['credito'].sum() if not data.empty and 'credito' in data else 0
    labelnumcreditos  = 'Personas con créditos o leasing (a partir de 2019 a la fecha)' if isinstance(numcreditos,int) and numcreditos>0 else ''
    labelnumcreditos2 = '(a partir de 2019 a la fecha)' if isinstance(numcreditos,int) and numcreditos>0 else ''
    
    #-------------------------------------------------------------------------#
    # Grafica por tipo de propietario
    style_chart = ""
    try:
        df = data.copy()
        if not df.empty:
            df['id']   = 1
            df         = df.groupby('tipoPropietario')['id'].count().reset_index()
            df.columns = ['ejex','ejey']
            df         = df.sort_values(by=['ejey'],ascending=False)
            df['color'] = '#5C9AE0'
            if not df.empty:
                style_chart += pie_chart(df,'tipoPropietario',title='Tipo de propietario')
    except: pass

    #-------------------------------------------------------------------------#
    # Grafica por tipo de propietario

    try:    
        df = data.copy()
        df['id']    = 1
        df          = df.groupby('propiedades')['id'].count().reset_index()
        df['propiedades'] = df['propiedades'].where(df['propiedades']<=5, '6 o más propiedades')
        df          = df.groupby('propiedades')['id'].sum().reset_index()
        df.columns  = ['ejex','ejey']
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += single_axis_chart(df,'byPropietades')
    except: pass

    #-------------------------------------------------------------------------#
    # Grafica por valor
    try:    
        df     = data.copy()
        bins   = [-float('inf'), 180_000_000, 250_000_000, 500_000_000, 800_000_000, 1_500_000_000, float('inf')]
        labels = [
            'Menos de 180 millones',
            'Menos de 250 millones',
            'Menos de 500 millones',
            'Menos de 800 millones',
            'Menos de 1500 millones',
            '1500 millones o más'
        ]
        df['rango_valor'] = pd.cut(df['valor'], bins=bins, labels=labels, right=False)
        df['id']    = 1
        df          = df.groupby('rango_valor')['id'].count().reset_index()
        df.columns = ['ejex','ejey']
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += single_axis_chart(df,'byValor')
    except: pass


    #-------------------------------------------------------------------------#
    # Grafica por edad
    try:
        df     = data.copy()
        df     = df[df['tipoPropietario'].astype(str).str.lower().str.contains('natural')]
        df     = df[['edad']]
        df.rename(columns={'edad':'valor'},inplace=True)
        style_chart += boxplot_chart(df,'byEdad',title='Edad')
    except: pass
    

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
           <div id="leaflet-map-generador-leads" style="height: 100%;"></div>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-lg-7">
            <div class="urbex-row">
             <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
              <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
               <p id="number_style">
                {numclientes}
               </p>
               <p id="label_style">
                {labelnumclientes}
               </p>
              </div>
             </div>
             <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
              <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
               <p id="number_style">
                {numemails}
               </p>
               <p id="label_style">
                {labelnumemails}
               </p>
              </div>
             </div>
             <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
              <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
               <p id="number_style">
                {numcreditos}
               </p>
               <p id="label_style">
                {labelnumcreditos}
               </p>
               <p id="label_style">
                {labelnumcreditos2}
               </p>
              </div>
             </div>
            </div>

          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="tipoPropietario" style="height: 100%;"></canvas>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byPropietades" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byValor"  style="height: 100%;"></canvas>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byEdad" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
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

def map_function(datageometry,latitud, longitud, polygon=None,metros=500):
    map_leaflet = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        
        #---------------------------------------------------------------------#
        # Poligono de la propiedad
        geojson      = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        geopoints    = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        geojsonradio = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'

        #---------------------------------------------------------------------#
        # Radio
        if isinstance(polygon,str) and polygon!='' and not 'none' in polygon.lower() :
            #---------------------------------------------------------------------#
            # Polygon
            polygon2geojson = pd.DataFrame([{'geometry':wkt.loads(polygon)}])
            polygon2geojson = gpd.GeoDataFrame(polygon2geojson, geometry='geometry')
            polygon2geojson['color'] = '#ADD8E6' #'green'
            geojson  = polygon2geojson.to_json()
            
        #---------------------------------------------------------------------#
        # Poligono de las otras propiedades
        geojsonlotes         = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        geojsontransacciones = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        if not datageometry.empty and 'wkt' in datageometry:
            datageometry             = datageometry[datageometry['wkt'].notnull()]
            datageometry['geometry'] = gpd.GeoSeries.from_wkt(datageometry['wkt'])
            datageometry             = gpd.GeoDataFrame(datageometry, geometry='geometry')
            geojsonlotes             = datageometry.to_json()

        map_leaflet = mapa_leaflet(latitud, longitud, geojson, geopoints, geojsonradio, geojsonlotes, geojsontransacciones)

    return map_leaflet

def mapa_leaflet(latitud, longitud, geojson, geopoints, geojsonradio, geojsonlotes, geojsontransacciones):
    html_mapa_leaflet = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonData = {geojson};
            var geojsonPoints = {geopoints};
            var geojsonRadio = {geojsonradio};  // GeoJSON para radio
            var geojsonLotes = {geojsonlotes};  // GeoJSON para lotes
            var geojsonTransacciones = {geojsontransacciones};  // Nuevo GeoJSON para transacciones
    
            var map_leaflet_transacciones = L.map('leaflet-map-generador-leads').setView([{latitud}, {longitud}], 16);
            
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 20
            }}).addTo(map_leaflet_transacciones);
    
            function style(feature) {{
                return {{
                    color: feature.properties.color || '#3388ff',
                    weight: 1,
                }};
            }}
    
            function styleRadio(feature) {{
                return {{
                    color: feature.properties.color || '#ff0000',
                    weight: 1,
                    fillOpacity: 0.05,
                }};
            }}
    
            function styleLotes(feature) {{
                return {{
                    color: feature.properties.color || '#00ff00',
                    weight: 1,
                    fillOpacity: 0.4,
                }};
            }}
    
            function styleTransacciones(feature) {{
                return {{
                    color: feature.properties.color || '#0000ff',
                    weight: 1,
                    fillOpacity: 0.2,
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
            }}).addTo(map_leaflet_transacciones);
    
            L.geoJSON(geojsonRadio, {{
                style: styleRadio,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet_transacciones);
    
            L.geoJSON(geojsonLotes, {{
                style: styleLotes,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet_transacciones);
    
            L.geoJSON(geojsonTransacciones, {{
                style: styleTransacciones,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet_transacciones);
    
            function pointToLayer(feature, latlng) {{
                return L.circleMarker(latlng, {{
                    radius: 0,
                    weight: 0,
                }});
            }}
    
            L.geoJSON(geojsonPoints, {{
                pointToLayer: pointToLayer,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet_transacciones);
        </script>
    """
    return html_mapa_leaflet


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
    
def boxplot_chart(df, name, title=''):
    # Asignar colores si hay múltiples categorías
    colors = ['#4A148C', '#7B1FA2', '#9C27B0', '#BA68C8', '#E1BEE7',
              '#006837', '#66BD63', '#D9EF8B', '#00ACC1', '#4DD0E1', '#B2EBF2']

    while len(colors) < len(df):
        colors.extend(colors)

    # Preparar datos del boxplot: Chart.js requiere mínimos, máximos, cuartiles y medianas
    dataset = {
        'label': title,
        'data': [{
            'min': df['valor'].min(),
            'q1': df['valor'].quantile(0.25),
            'median': df['valor'].median(),
            'q3': df['valor'].quantile(0.75),
            'max': df['valor'].max()
        }],
        'backgroundColor': colors[0],
        'borderColor': colors[0],
        'borderWidth': 1
    }

    # Construir y retornar el HTML y el script JavaScript
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@sgratzl/chartjs-chart-boxplot"></script>
    
    <div style="height: 400px; width: 100%;">
        <canvas id="{name}"></canvas>
    </div>
    
    <script>
    (function() {{
        new Chart(document.getElementById('{name}'), {{
            type: 'boxplot',
            data: {{
                labels: ['{title}'],
                datasets: [{dataset}]
            }},
            options: {{
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: '{title}',
                        font: {{ size: 16, weight: 'bold' }},
                        padding: 20
                    }}
                }},
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: false,
                        min: {df['valor'].min()},
                        max: {df['valor'].max()},
                        grid: {{
                            display: false // Elimina líneas horizontales
                        }},
                        ticks: {{
                            precision: 0
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false // Elimina líneas verticales
                        }}
                    }}
                }}
            }}
        }});
    }})();
    </script>
    """
