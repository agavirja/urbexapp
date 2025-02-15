import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from shapely.geometry import Point
from datetime import datetime

from functions.circle_polygon import circle_polygon


import numpy as np

def main(data=pd.DataFrame(),latitud=None,longitud=None,polygon=None,metros=500):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(data=data,latitud=latitud,longitud=longitud,polygon=polygon,metros=metros)

    return html_content
    
#@st.cache_data(show_spinner=False)
def gethtml(data=pd.DataFrame(),latitud=None,longitud=None,polygon=None,metros=500):
            
    valormin    = 3000000
    valormax    = 50000000
    if 'valormt2' not in data and 'precio' in data and 'areaconstruida' in data:
        data['valormt2'] = data['precio']/data['areaconstruida'] 
    idd  = (data['tipo'].astype(str).str.lower().str.contains('apt|apartamento')) & ((data['valormt2']<valormin) | (data['valormt2']>valormax))
    data = data[~idd]
        
    #-------------------------------------------------------------------------#
    # Total proyectos
    value             = int(len(data['codproyecto'].unique())) if not data.empty else 0
    numeroproyectos   = "{:,.0f}".format(value)  if value>0 else 'Sin información'
    titlenumproyectos = 'Total proyectos' if value>0 else ''


    value            = int(len(data[data['estado'].isin(['Const', 'Prev'])]['codproyecto'].unique())) if not data.empty and 'estado' in data else 0
    proyectosactivos = "{:,.0f}".format(value)  if value>0 else 'Sin información'
    titleproactivos  = 'Proyectos en construcción o preventa' if value>0 else ''


    #-------------------------------------------------------------------------#
    # Precios
    df = data.copy()
    df = df[df['estado'].isin(['Const', 'Prev'])]

    value         = df['valormt2'].median() if not df.empty and 'valormt2' in df else 0
    pmedian       = '${:,.0f}'.format(value)  if value>0 else 'Sin información'
    titlepmedian  = 'Precio promedio por m2' if value>0 else ''

    value     = df['valormt2'].min() if not df.empty and 'valormt2' in df else 0
    pmin      = '${:,.0f}'.format(value)  if value>0 else 'Sin información'
    titlepmin = 'Precio mínimo por m2' if value>0 else ''
    
    value     = df['valormt2'].max() if not df.empty and 'valormt2' in df else 0
    pmax      = '${:,.0f}'.format(value)  if value>0 else 'Sin información'
    titlepmax = 'Precio máximo por m2' if value>0 else ''
    
    #-------------------------------------------------------------------------#
    # Grafica por estado
    style_chart = ""
    try:    
        df = data.copy()
        df = df.drop_duplicates(subset='codproyecto',keep='last')
        df['id']    = 1
        df          = df.groupby('estado')['id'].count().reset_index()
        df.columns  = ['ejex','ejey']
        df['color'] = df['ejex'].replace(['Term', 'Desist', 'Const', 'Prev'],['#5CE092','#E07C5C','#E0BF5C','#5C9AE0'])
        if not df.empty:
            style_chart += single_axis_chart(df,'byType')
    except: pass
    
    #-------------------------------------------------------------------------#
    # Grafica por ano
    try:
        df                     = data.copy()
        df['year_entrega']     = df['fecha_entrega'].apply(lambda x: x.year)
        df['year_entrega_new'] = df['fecha_inicio'].apply(lambda x: x.year)
        df['year_entrega_new'] = df['year_entrega_new']+2
        idd = (df['year_entrega'].isnull()) & (df['year_entrega_new'].notnull())
        if sum(idd)>0:
            df.loc[idd,'year_entrega'] = df.loc[idd,'year_entrega_new']
        df = df[df['ano']<=df['year_entrega']]
        df = df.groupby(['ano'])['valormt2'].median().reset_index()
        df.columns = ['ejex','ejey']
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += single_axis_chart(df,'byYear')
    except: pass

    #-------------------------------------------------------------------------#
    # Grafica por proyecto
    try:
        df         = data.copy()
        df         = df.groupby('proyecto').agg({'valormt2':'max'}).reset_index()
        df.columns = ['ejex','ejey']
        df         = df.sort_values(by=['ejey'],ascending=False)
        df         = df.iloc[0:4,:]
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += single_axis_chart(df,'byProyecto')
    except: pass

    #-------------------------------------------------------------------------#
    # Grafica por constructora
    try:
        df         = data.copy()
        df         = df.drop_duplicates(subset='codproyecto',keep='last')
        df['id']   = 1
        df         = df.groupby('construye')['id'].count().reset_index()
        df.columns = ['ejex','ejey']
        df         = df.sort_values(by=['ejey'],ascending=False)
        df         = df.iloc[0:4,:]
        df['color'] = '#5C9AE0'
        if not df.empty:
            style_chart += single_axis_chart(df,'byConst')
    except: pass

    #-------------------------------------------------------------------------#
    # Grafica por tipo
    formato = [{'label':'Habitaciones','variable':'habitaciones','id':'byHabitaciones'},
               {'label':'Baños','variable':'banos','id':'byBanos'},
               {'label':'Garajes','variable':'garajes','id':'byGarajes'},
               ]
    for i in formato:
        variable = i['variable']
        lablel   = i['label']
        idhtml   = i['id']
        try:
            df = data[data['estado'].isin(['Const', 'Prev'])]
            if not df.empty:
                df         = df.drop_duplicates(subset='codinmueble',keep='last')
                df['id']   = 1
                df         = df.groupby(variable)['id'].count().reset_index()
                df.columns = ['ejex','ejey']
                df         = df.sort_values(by=['ejey'],ascending=False)
                df['color'] = '#5C9AE0'
                if not df.empty:
                    style_chart += pie_chart(df,idhtml,title=lablel)
        except: pass

    df = data[data['estado'].isin(['Const', 'Prev'])]
    df = df.groupby('codproyecto')['areaconstruida'].max().reset_index()
    df['valor'] = df['areaconstruida'].copy()
    style_chart += boxplot_chart(df,'BoxAreaNuevosProyectos',title='Área construida')

    #df = data[data['estado'].isin(['Const', 'Prev'])]
    #df = df.drop_duplicates(subset='codinmueble',keep='last')
    #style_chart += box_plot(df, 'BoxplotG')
    
    #-------------------------------------------------------------------------#
    # Mapa
    mapscript = map_function(data,latitud, longitud, polygon=polygon, metros=metros)

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
           <div id="leaflet-map-proyectos" style="height: 100%;"></div>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-lg-7">
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {numeroproyectos}
             </p>
             <p id="label_style">
              {titlenumproyectos}
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {proyectosactivos}
             </p>
             <p id="label_style">
              {titleproactivos}
             </p>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
            <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {pmedian}
             </p>
             <p id="label_style">
              {titlepmedian}
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
            <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {pmin}
             </p>
             <p id="label_style">
              {titlepmin}
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
            <div class="urbex-text-center urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {pmax}
             </p>
             <p id="label_style">
              {titlepmax}
             </p>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byType" style="height: 100%;"></canvas>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byYear" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byProyecto"  style="height: 100%;"></canvas>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 350px;">
             <canvas id="byConst" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
         </div>
        </div>
       </div>
      </section>
      
      <section>
       <div class="urbex-container-fluid">
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-3" style="min-height: 350px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
              <canvas id="byHabitaciones" style="height: 100%;"></canvas>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-3" style="min-height: 350px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
              <canvas id="byBanos" style="height: 100%;"></canvas>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-3" style="min-height: 350px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
              <canvas id="byGarajes" style="height: 100%;"></canvas>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-3" style="min-height: 350px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
              <canvas id="BoxAreaNuevosProyectos" style="height: 100%;"></canvas>
          </div>
         </div>
        </div>
       </div>
      </section>
      {style_chart}
      {mapscript}
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
    
    <div style="height: 100%; width: 100%;">
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

def map_function(datageometry,latitud, longitud, polygon=None, metros=500):
    map_leaflet = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        
        #---------------------------------------------------------------------#
        # Punto de la propiedad
        geopoints  =  point2geopandas(datageometry)
        geojson    = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        
        
        if isinstance(polygon,str) and polygon!='':
            #---------------------------------------------------------------------#
            # Polygon
            polygon2geojson = pd.DataFrame([{'geometry':wkt.loads(polygon)}])
            polygon2geojson = gpd.GeoDataFrame(polygon2geojson, geometry='geometry')
            polygon2geojson['color'] = 'blue'
            geojson  = polygon2geojson.to_json()

        else:
            #---------------------------------------------------------------------#
            # Radio
            dataradiopolygon = pd.DataFrame([{'geometry':circle_polygon(metros,latitud,longitud)}])
            dataradiopolygon = gpd.GeoDataFrame(dataradiopolygon, geometry='geometry')
            dataradiopolygon['color'] = '#0095ff'
            geojson     = dataradiopolygon.to_json()

        map_leaflet = mapa_leaflet(latitud, longitud, geopoints, geojson)

    return map_leaflet

def mapa_leaflet(latitud, longitud, geopoints, geojsonradio):
    html_mapa_leaflet = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var geojsonPoints = {geopoints};
            var geojsonRadio = {geojsonradio};  // GeoJSON para radio

            var map_leaflet_proyectos = L.map('leaflet-map-proyectos').setView([{latitud}, {longitud}], 16);
            
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 20
            }}).addTo(map_leaflet_proyectos);
    
            function styleRadio(feature) {{
                return {{
                    color: feature.properties.color || '#ff0000',
                    weight: 1,
                    fillOpacity: 0.05,
                }};
            }}
    
            function onEachFeature(feature, layer) {{
                if (feature.properties && feature.properties.popup) {{
                    layer.bindPopup(feature.properties.popup);
                }}
            }}
    
            // Capa de GeoJSON para radio
            L.geoJSON(geojsonRadio, {{
                style: styleRadio,
                onEachFeature: onEachFeature
            }}).addTo(map_leaflet_proyectos);

            // Crear círculos para cada punto en geopoints
            geojsonPoints.features.forEach(function(feature) {{
                var latlng = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]];  // [lat, lng]
                var color = feature.properties.color || 'blue';  // Obtener el color de las propiedades del punto, con azul como predeterminado
                var circleMarker = L.circle(latlng, {{
                    radius: 20,
                    fill: true,
                    fillOpacity: 1,
                    color: color,  // Usar el color del punto
                    fillColor: color  // Asegurar que el color de relleno coincida
                }}).addTo(map_leaflet_proyectos);

                // Popup para el círculo basado en el atributo "popup"
                circleMarker.bindPopup(feature.properties.popup || 'Información no disponible');
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
        #data['color']    = '#5A189A'
        data['color']    = data['estado'].replace(['Term', 'Desist', 'Const', 'Prev'],['#5CE092','#E07C5C','#E0BF5C','#5C9AE0'])
        data['popup']    = None
        for idd,items in data.iterrows():
            try:    proyecto = f"<b> Proyecto:</b> {items['proyecto']}<br>"
            except: proyecto = "<b> Proyecto:</b> Sin información <br>" 
            try:    estado = f"<b> Estado:</b> {items['estado']}<br>"
            except: estado = "<b> Estado:</b> Sin información <br>" 
            try:    direccion = f"<b> Dirección:</b> {items['direccion']}<br>"
            except: direccion = "<b> Dirección:</b> Sin información <br>"
            try:    construye = f"<b> Construye:</b> {items['construye']}<br>"
            except: construye = "<b> Construye:</b> Sin información <br>"
            try:    vende = f"<b> Vende:</b> {items['vende']}<br>"
            except: vende = "<b> Vende:</b> Sin información <br>"
            try:    estrato = f"<b> Estrato:</b> {items['estrato']}<br>"
            except: estrato = "<b> Estrato:</b> Sin información <br>"
            try:    unidades = f"<b> Unidades:</b> {items['unidades_proyecto']}<br>"
            except: unidades = "<b> Unidades:</b> Sin información <br>" 
            try:    fechainicio = f"<b> Fecha inicio:</b> {items['fecha_inicio'].strftime('%Y-%m')}<br>"
            except: fechainicio = "<b> Fecha inicio:</b> Sin información <br>" 
            try:    fechaentrega = f"<b> Fecha entrega:</b> {items['fecha_entrega'].strftime('%Y-%m')}<br>"
            except: fechaentrega = "<b> Fecha entrega:</b> Sin información <br>" 
            try:    fiduciaria = f"<b> Fiduciaria:</b> {items['fiduciaria']}<br>"
            except: fiduciaria = "<b> Fiduciaria:</b> Sin información <br>"            
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 14px;">
                        <a style="color: black;">
                            {direccion}    
                            {proyecto}
                            {estado}
                            {construye}
                            {vende}
                            {estrato}
                            {unidades}
                            {fechainicio}
                            {fechaentrega}
                            {fiduciaria}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        data    = data[['geometry','popup','color']]
        geojson = data.to_json()
        
    return geojson