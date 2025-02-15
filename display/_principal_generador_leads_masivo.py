import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
from shapely.geometry import Point
from bs4 import BeautifulSoup
from datetime import datetime

from functions.getuso_destino import usosuelo_class 

def main(dataupload=pd.DataFrame(), dataresult=pd.DataFrame(), data_predios=pd.DataFrame(), data_transacciones=pd.DataFrame()):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(dataupload=dataupload, dataresult=dataresult, data_predios=data_predios, data_transacciones=data_transacciones)

    return html_content
    
def gethtml(dataupload=pd.DataFrame(), dataresult=pd.DataFrame(), data_predios=pd.DataFrame(), data_transacciones=pd.DataFrame()):
    

    mapscript = ""

    #-------------------------------------------------------------------------#
    # Inmuebles activos
    #-------------------------------------------------------------------------#
    html_general = ""
    # Mapa: 
    if not data_predios.empty and 'wkt' in data_predios:
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
            
            html_general += """
             <div class="urbex-col-12 urbex-col-lg-5">
              <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
               <div id="mapaactivos" style="height: 100%;"></div>
              </div>
             </div>
            """
                
        if html_general=="":
                html_general += """
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
                  </div>
                 </div>
                """
    # Cifras:
    reg_vehiculos = len(dataresult[dataresult['vehiculos'].notnull()]) if not dataresult.empty and 'vehiculos' in dataresult else 0
    reg_predios   = len(dataresult[dataresult['predios'].notnull()]) if not dataresult.empty and 'predios' in dataresult else 0
    
    html_general += f"""
     <div class="urbex-col-12 urbex-col-lg-7">
     <div class="urbex-row">
      <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
       <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
        <p id="number_style">
         {len(dataupload)}
        </p>
        <p id="label_style">
         Total registros
        </p>
       </div>
      </div>
      <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
       <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
        <p id="number_style">
         {reg_predios}
        </p>
        <p id="label_style">
         Registros con inmuebles activos
        </p>
       </div>
      </div>
      <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
       <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
        <p id="number_style">
         {reg_vehiculos}
        </p>
        <p id="label_style">
         Registros con vehículos
        </p>
       </div>
      </div>
     </div>
    """
    
    
    if not dataresult.empty:
        predios        = dataresult['predios'].sum() if 'predios' in dataresult else 0
        df             = dataresult.copy()
        df['promedio'] = df['predios']*df['valorpromedio']/predios if 'valorpromedio' in df and predios>0 else 0
        valorpromedio  = df['promedio'].sum() if 'promedio' in df else 0
        
        transacciones      = int(df['transacciones'].sum()) if 'transacciones' in df else 0
        valortransacciones = df['valortotaltransacciones'].sum()/transacciones if 'valortotaltransacciones' in df and transacciones>0 else 0
        
        html_general += f"""
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <p id="number_style">
            {predios}
           </p>
           <p id="label_style">
            Total predios activos a nombre propio
           </p>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <p id="number_style">
               {"${:,.0f}".format(valorpromedio)}
           </p>
           <p id="label_style">
            Valor promedio de los inmuebles
           </p>
          </div>
         </div>
        </div>
        
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <p id="number_style">
            {transacciones}
           </p>
           <p id="label_style">
            Registro de transacciones
           </p>
           <p id="label_style">
            (desde 2019 a la fecha, a nivel nacional)
           </p>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <p id="number_style">
           {"${:,.0f}".format(valortransacciones)}
           </p>
           <p id="label_style">
            Valor promedio de las transacciones
           </p>
           <p id="label_style">
            (desde 2019 a la fecha, a nivel nacional)
           </p>
          </div>
         </div>
        </div>
        """
    
    #-------------------------------------------------------------------------#
    # Grafica por tipo
    style_chart = ""


    if not data_predios.empty:
        html_graph = ""
        # Estrato
        df         = data_predios.copy()
        df['id']   = 1
        df         = df.groupby('estrato')['id'].count().reset_index()
        df.columns = ['ejex','ejey']
        df         = df.sort_values(by=['ejey'],ascending=False)
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += pie_chart(df,'byEstrato',title='Estrato')
            
        html_graph += """
         <div class="urbex-col-12 urbex-col-md-6 urbex-p-2" style="min-height: 350px;">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <canvas id="byEstrato" style="height: 100%;"></canvas>
          </div>
         </div>
        """
 
    
        # Area
        df          = data_predios.copy()
        df['valor'] = df['preaconst'].copy() if 'preaconst' in df else None
        df          = df[['valor']]
        style_chart += boxplot_chart(df,'BoxArea',title='Área')
        
        html_graph += """
         <div class="urbex-col-12 urbex-col-md-6 urbex-p-2" style="min-height: 350px;">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <canvas id="BoxArea" style="height: 100%;"></canvas>
          </div>
         </div>
        """
        
        html_general = f"""
        {html_general}
        <div class="urbex-row">
            {html_graph}
        </div>
        """
        
        html_graph = ""
        # Antiguedad
        df              = data_predios.copy()
        df['categoria'] = df['prevetustzmin'].apply(categorize_age) if 'prevetustzmin' in df else None
        df['id']   = 1
        df         = df.groupby('categoria')['id'].count().reset_index()
        df.columns = ['ejex','ejey']
        df         = df.sort_values(by=['ejey'],ascending=False)
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += pie_chart(df,'byAntiguedad',title='Antigüedad')
            
        html_graph += """
         <div class="urbex-col-12 urbex-col-md-6 urbex-p-2" style="min-height: 350px;">
          <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
           <canvas id="byAntiguedad" style="height: 100%;"></canvas>
          </div>
         </div>
        """
        
        # Edad
        df = dataresult.copy() if not dataresult.empty else pd.DataFrame(columns=['edad'])
        df = df[df['edad'].notnull()] if not df.empty and 'edad' in df else pd.DataFrame(columns=['edad'])
        if not df.empty:
            df['valor'] = df['edad'].copy() 
            df          = df[['valor']]
            style_chart += boxplot_chart(df,'BoxEdad',title='Edad')
            
            html_graph += """
             <div class="urbex-col-12 urbex-col-md-6 urbex-p-2" style="min-height: 350px;">
              <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
               <canvas id="BoxEdad" style="height: 100%;"></canvas>
              </div>
             </div>
            """
        
        html_general = f"""
        {html_general}
        <div class="urbex-row">
            {html_graph}
        </div>
        """
        
        # Uso
        html_graph = ""
        datauso    = usosuelo_class()
        datauso    = datauso.drop_duplicates(subset='precuso',keep='first')
        df         = data_predios.copy()
        if 'precuso' in df:
            df  = df.merge(datauso[['precuso','clasificacion']],on='precuso',how='left',validate='m:1')
            
        if 'clasificacion' in df: 
            df['id']   = 1
            df         = df.groupby('clasificacion')['id'].count().reset_index()
            df.columns = ['ejex','ejey']
            df         = df.sort_values(by=['ejey'],ascending=False)
            df['color'] = '#5C9AE0'
            if not df.empty and len(df)>1:
                style_chart += single_axis_chart(df,'byUso')
                
                html_graph += """
                 <div class="urbex-col-12 urbex-col-md-12 urbex-p-2" style="min-height: 350px;">
                  <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                   <canvas id="byUso" style="height: 100%;"></canvas>
                  </div>
                 </div>
                """
        if isinstance(html_graph,str) and html_graph!='':
            html_general = f"""
            {html_general}
            <div class="urbex-row">
                {html_graph}
            </div>
            """
        
    if isinstance(html_general,str) and html_general!="":
        html_general = f"""
          <section style="margin-bottom: 50px;">
           <div class="urbex-container-fluid">
            <div class="urbex-row">
                {html_general}
                </div>
            </div>
           </div>
          </section>
        """
        
     
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
         {html_general}
         {mapscript}
         {style_chart}
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
    
def categorize_age(year):
    current_year = datetime.now().year
    age = current_year - year
    if age < 5:
        return 'Menor a 5 años'
    elif 5 <= age <= 10:
        return 'Entre 5 y 10 años'
    elif 10 < age <= 20:
        return 'Entre 10 y 20 años'
    elif 20 < age <= 30:
        return 'Entre 20 y 30 años'
    else:
        return 'Mayor a 30 años'
    