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


def main(grupo,formato,datageometry=pd.DataFrame(),latitud=None,longitud=None,polygon=None,metros=500, data_caracteristicas=pd.DataFrame()):    
    #-------------------------------------------------------------------------#
    # Informacion General
    #-------------------------------------------------------------------------#
    html_content = gethtml(grupo,formato,datageometry=datageometry,latitud=latitud,longitud=longitud,polygon=str(polygon),metros=metros, data_caracteristicas=data_caracteristicas)

    return html_content
    
def gethtml(grupo,inputs,datageometry=pd.DataFrame(),latitud=None,longitud=None,polygon=None,metros=500, data_caracteristicas=pd.DataFrame()):
    
    
    #-------------------------------------------------------------------------#
    # Transacciones
    numerotransacciones = "{:,.0f}".format(inputs['numerotransacciones']['value'])  if 'numerotransacciones' in inputs and 'value' in inputs['numerotransacciones'] and isinstance(inputs['numerotransacciones']['value'],(int,float)) else 'Sin información'
    titlenumerotrans    = inputs['numerotransacciones']['label'] if 'numerotransacciones' in inputs and 'label' in inputs['numerotransacciones'] and isinstance(inputs['numerotransacciones']['label'],str) else ''
    
    valortransacciones  = "${:,.0f}".format(inputs['valortransacciones']['value']) if 'valortransacciones' in inputs and 'value' in inputs['valortransacciones'] and isinstance(inputs['valortransacciones']['value'],(int,float)) else 'Sin información'
    titlevalortrans     = inputs['valortransacciones']['label'] if 'valortransacciones' in inputs and 'label' in inputs['valortransacciones'] and isinstance(inputs['valortransacciones']['label'],str) else ''
    
    style_chart = ""
    try:    
        df = pd.DataFrame(inputs['transaccionesyear']['value']) if 'transaccionesyear' in inputs and 'value' in inputs['transaccionesyear'] else pd.DataFrame()
        if not df.empty:
            df.rename(columns={'cuantiamt2':'valor1','transacciones':'valor2'},inplace=True)
            style_chart += double_axis_chart(df,'TransChartEstudioMercado')
    except: pass

    lotestrans = pd.DataFrame(inputs['lotescontransacciones']['value']) if 'lotescontransacciones' in inputs and 'value' in inputs['lotescontransacciones'] and isinstance(inputs['lotescontransacciones']['value'],list) else pd.DataFrame()

    if not datageometry.empty and not lotestrans.empty:
        datamerge    = lotestrans.sort_values(by=['grupo','cuantiamt2'],ascending=True).drop_duplicates(subset='grupo',keep='first')
        datageometry = datageometry.merge(datamerge,on='grupo',how='left',validate='m:1')
      
    #-------------------------------------------------------------------------#
    # Prediales
    avaluocatastralmt2   = "${:,.0f}".format(inputs['avaluocatastralmt2']['value'])  if 'avaluocatastralmt2' in inputs and 'value' in inputs['avaluocatastralmt2'] and isinstance(inputs['avaluocatastralmt2']['value'],(int,float)) else 'Sin información'
    titleavaluocatastral = inputs['avaluocatastralmt2']['label'] if 'avaluocatastralmt2' in inputs and 'label' in inputs['avaluocatastralmt2'] and isinstance(inputs['numerotransacciones']['label'],str) else ''
    
    predialmt2           = "${:,.0f}".format(inputs['predialmt2']['value']) if 'predialmt2' in inputs and 'value' in inputs['predialmt2'] and isinstance(inputs['predialmt2']['value'],(int,float)) else 'Sin información'
    titlepredialmt2      = inputs['predialmt2']['label'] if 'predialmt2' in inputs and 'label' in inputs['predialmt2'] and isinstance(inputs['predialmt2']['label'],str) else ''
    
    try:    
        df = pd.DataFrame(inputs['predialesyear']['value']) if 'predialesyear' in inputs and 'value' in inputs['predialesyear'] else pd.DataFrame()
        if not df.empty:
            df.rename(columns={'avaluomt2':'valor1','predialmt2':'valor2'},inplace=True)
            style_chart += double_axis_chart(df,'PredialChartEstudioMercado')
    except: pass
    
    #-------------------------------------------------------------------------#
    # Predios totales
    numerofolios      = "{:,.0f}".format(inputs['numerofolios']['value'])  if 'numerofolios' in inputs and 'value' in inputs['numerofolios'] and isinstance(inputs['numerofolios']['value'],(int,float)) else 'Sin información'
    titlenumerofolios = inputs['numerofolios']['label'] if 'numerofolios' in inputs and 'label' in inputs['numerofolios'] and isinstance(inputs['numerotransacciones']['label'],str) else ''
    
    numeropredios      = "{:,.0f}".format(inputs['numeropredios']['value']) if 'numeropredios' in inputs and 'value' in inputs['numeropredios'] and isinstance(inputs['numeropredios']['value'],(int,float)) else 'Sin información'
    titlenumeropredios = inputs['numeropredios']['label'] if 'numeropredios' in inputs and 'label' in inputs['numeropredios'] and isinstance(inputs['numeropredios']['label'],str) else ''
    
    mapscript = map_function(datageometry,latitud, longitud, polygon=polygon,metros=metros, data_caracteristicas=data_caracteristicas)


    #-------------------------------------------------------------------------#
    # Box plot
    
    if 'distribucionantiguedad' in inputs and 'value' in inputs['distribucionantiguedad']: 
        if len(inputs['distribucionantiguedad']['value'])>0:
            if inputs['distribucionantiguedad']['value'][0]['min']==0:
                inputs['distribucionantiguedad']['value'][0]['min'] = inputs['distribucionantiguedad']['value'][0]['q1']-10
        
    style_chart += boxplot_chart(inputs['distribucionarea']['value'],'BoxArea',title='Área construida')
    style_chart += boxplot_chart(inputs['distribucionantiguedad']['value'],'BoxAntiguedad',title='Antigüedad')
        
    #-------------------------------------------------------------------------#
    # Proyectos nuevos 
    data_precios   = dataproyectosnuevos(grupo=grupo, polygon=polygon)
    html_proyectos = ""
    if not data_precios.empty:
        html_proyectos = generar_html_proyectos(data=data_precios.copy(), latitud=latitud, longitud=longitud, polygon=polygon, metros=metros)
        soup           = BeautifulSoup(html_proyectos, 'html.parser')
        html_proyectos = soup.body
        
        html_proyectos = f"""
        <section style="padding-top: 100px;">
         <div class="urbex-row urbex-p-2">
          <div class="urbex-col">
           <h1 id="seccion_title">
            Proyectos nuevos
           </h1>
          </div>
         </div>
        </section>
        {html_proyectos}
        """
        
    html = f"""
    <!DOCTYPE html>
    <html data-bs-theme="light" lang="en">
     <head>
      <meta charset="utf-8"/>
      <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
      <title>
       urbex_estudio_mercado_esqueleto_general
      </title>
      <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
      <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
     </head>
     <body>
      <section>
       <div class="urbex-container-fluid">
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-lg-5">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 900px;">
           <div id="leaflet-map-transacciones" style="height: 100%;"></div>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-lg-7">
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
             <p id="number_style">
              {numerofolios}
             </p>
             <p id="label_style">
              {titlenumerofolios}
             </p>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-d-flex" id="box_shadow_default">
             <p id="number_style">
              {numeropredios}
             </p>
             <p id="label_style">
              {titlenumeropredios}
             </p>
            </div>
           </div>
          </div>
          <div class="urbex-row" style="min-height: 350px;">
           <div class="urbex-col-12 urbex-col-md-3">
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div class="urbex-text-center" id="box_shadow_default" style="min-height: 170px;">
               <p id="number_style">
                {numerotransacciones}
               </p>
               <p id="label_style">
                {titlenumerotrans}
               </p>
              </div>
             </div>
            </div>
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div class="urbex-text-center" id="box_shadow_default" style="min-height: 170px;">
               <p id="number_style">
                {valortransacciones}
               </p>
               <p id="label_style">
                {titlevalortrans}
               </p>
              </div>
             </div>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-9">
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div id="box_shadow_default" style="height: 100%;min-height: 350px;">
               <canvas id="TransChartEstudioMercado" style="height: 100%;"></canvas>
              </div>
             </div>
            </div>
           </div>
          </div>
          <div class="urbex-row" style="min-height: 350px;">
           <div class="urbex-col-12 urbex-col-md-3">
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div class="urbex-text-center" id="box_shadow_default" style="min-height: 170px;">
               <p id="number_style">
                {avaluocatastralmt2}
               </p>
               <p id="label_style">
                {titleavaluocatastral}
               </p>
              </div>
             </div>
            </div>
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div class="urbex-text-center" id="box_shadow_default" style="min-height: 170px;">
               <p id="number_style">
                {predialmt2}
               </p>
               <p id="label_style">
                {titlepredialmt2}
               </p>
              </div>
             </div>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-9">
            <div class="urbex-row">
             <div class="urbex-col urbex-p-2">
              <div id="box_shadow_default" style="height: 100%;min-height: 350px;">
               <canvas id="PredialChartEstudioMercado" style="height: 100%;"></canvas>
              </div>
             </div>
            </div>
           </div>
          </div>
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-md-6 urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="height: 100%;min-height: 250px;">
                <canvas id="BoxArea" style="height: 100%;"></canvas>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-md-6 urbex-text-center urbex-p-2">
            <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="height: 100%;min-height: 250px;">
             <canvas id="BoxAntiguedad" style="height: 100%;"></canvas>
            </div>
           </div>
          </div>
         </div>
        </div>
       </div>
      </section>
      {html_proyectos}
      {style_chart}
      {mapscript}
     </body>
    </html>
    """

    return html 

def map_function(datageometry,latitud, longitud, polygon=None,metros=500, data_caracteristicas=pd.DataFrame()):
    map_leaflet = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        
        #---------------------------------------------------------------------#
        # Poligono de la propiedad
        geojson   = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        geopoints = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        
        if isinstance(polygon,str) and polygon!='':
            data2geojson = pd.DataFrame([{'geometry':wkt.loads(polygon)}])
            data2geojson = gpd.GeoDataFrame(data2geojson, geometry='geometry')
            data2geojson['color'] = 'blue'
            geojson      = data2geojson.to_json()

        #---------------------------------------------------------------------#
        # Punto de la propiedad
        data2geopoints          = pd.DataFrame([{'geometry':Point(longitud,latitud)}])
        data2geopoints          = gpd.GeoDataFrame(data2geopoints, geometry='geometry')
        data2geopoints['color'] = 'blue'
        geopoints               =  data2geopoints.to_json()
        
        #---------------------------------------------------------------------#
        # Radio
        dataradiopolygon = pd.DataFrame([{'geometry':circle_polygon(metros,latitud,longitud)}])
        dataradiopolygon = gpd.GeoDataFrame(dataradiopolygon, geometry='geometry')
        dataradiopolygon['color'] = '#0095ff'
        geojsonradio     = dataradiopolygon.to_json()

        #---------------------------------------------------------------------#
        # Poligono de las otras propiedades
        geojsonlotes         = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        geojsontransacciones = '{"type": "FeatureCollection", "features": [{"id": "0", "type": "Feature", "properties": {"color": "blue"}, "geometry": {"type": "Polygon", "coordinates": []}}]}'
        
        if not datageometry.empty and 'wkt' in datageometry:
            datageometry             = datageometry[datageometry['wkt'].notnull()]
            datageometry['geometry'] = gpd.GeoSeries.from_wkt(datageometry['wkt'])
            datageometry             = gpd.GeoDataFrame(datageometry, geometry='geometry')
            datageometry['color']    = '#5A189A'
            urlexport                = "http://localhost:8501/Reporte"

            if not data_caracteristicas.empty:
                datamerge = data_caracteristicas.drop_duplicates(subset=['grupo','barmanpre'],keep='first')
                variables = [x for x in datamerge if x not in datageometry]
                variables += ['grupo','barmanpre']
                datageometry = datageometry.merge(datamerge[variables],on=['grupo','barmanpre'],how='left',validate='m:1')
                
            for idd, items in datageometry.iterrows():
                
                params       = {'type':'predio','grupo':items['grupo'],'barmanpre':items['barmanpre'],'token':st.session_state.token}
                params       = json.dumps(params)
                params       = base64.urlsafe_b64encode(params.encode()).decode()
                params       = urllib.parse.urlencode({'token': params})
                urllink      = f"{urlexport}?{params}"

                buildinfinfo = ""
        
                try:    buildinfinfo += f"""<b> Dirección:</b> {items['formato_direccion']}<br>""" if isinstance(items['formato_direccion'],str) else ''
                except: pass
                try:    buildinfinfo += f"""<b> Nombre Edificio:</b> {items['nombre_conjunto']}<br>""" if isinstance(items['nombre_conjunto'],str) else ''
                except: pass     
                try:    buildinfinfo += f"""<b> Barrio:</b> {items['prenbarrio']}<br>  """ if isinstance(items['prenbarrio'],str) else ''
                except: pass
                try:    buildinfinfo += f"""<b> Estrato:</b> {int(items['estrato'])}<br>  """ if isinstance(items['estrato'],(float,int)) and items['estrato']>0 else ''
                except: pass
                try:    buildinfinfo += f"""<b> Área construida total:</b> {items['preaconst']:.2f}<br>""" if isinstance(items['preaconst'],(float,int)) else ''
                except: pass
                try:    buildinfinfo += f"""<b> Área de terreno total:</b> {items['preaterre']:.2f}<br>""" if isinstance(items['preaterre'],(float,int)) else ''
                except: pass
                try:    buildinfinfo += f"""<b> Antiguedad:</b> {int(items['prevetustzmin'])}<br>""" if isinstance(items['prevetustzmin'],(float,int)) else ''
                except: pass                              
                try:    buildinfinfo += f"""<b> Pisos:</b> {int(items['connpisos'])}<br> """
                except: pass    
                try:  buildinfinfo += f"""<b> Número transacciones:</b> {int(items['transacciones'])}<br>""" if isinstance(items['transacciones'], (float, int)) else ''
                except: pass
                try:  buildinfinfo += f"""<b> Valor transacciones mt2:</b> ${items['cuantiamt2']:.2f}<br>""" if not pd.isna(items['cuantiamt2']) and isinstance(items['cuantiamt2'], (float, int)) else ''
                except:  pass
        
                popup_content = f'''
                <!DOCTYPE html>
                <html>
                    <body>
                        <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                            <a href="{urllink}" target="_blank" style="color: black;">
                                {buildinfinfo}
                            </a>
                        </div>
                    </body>
                </html>
                '''
                datageometry.loc[idd, 'popup'] = popup_content
            
            geojsonlotes = datageometry.to_json()
        
            if 'transacciones' in datageometry:
                datapaso = datageometry[datageometry['transacciones'] > 0]
                if not datapaso.empty:
                    datapaso['color']    = '#B20256'
                    geojsontransacciones = datapaso.to_json()
                    
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
    
            var map_leaflet_transacciones = L.map('leaflet-map-transacciones').setView([{latitud}, {longitud}], 16);
            
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

def double_axis_chart(df,name):
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
            labels: {df['year'].tolist()},
            datasets: [{{
                label: 'Valor de las transacciones',
                data: {df['valor1'].tolist()},
                yAxisID: 'A',
                backgroundColor: 'rgba(0, 123, 255, 0.8)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1
            }}, {{
                label: 'Número de transacciones',
                data: {df['valor2'].tolist()},
                yAxisID: 'B',
                backgroundColor: 'rgba(153, 102, 255, 0.8)',
                borderColor: 'rgba(153, 102, 255, 1)',
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
                A: {{
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
                B: {{
                    type: 'linear',
                    position: 'right',
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
                text: 'Gráfico de Transacciones y Valores por Año',
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
    
def boxplot_chart(inputs, name, title=''):
    # Asignar colores si hay múltiples categorías
    colors = ['#4A148C', '#7B1FA2', '#9C27B0', '#BA68C8', '#E1BEE7',
              '#006837', '#66BD63', '#D9EF8B', '#00ACC1', '#4DD0E1', '#B2EBF2']

    global_min          = min(item['min'] for item in inputs)
    adjusted_max_values = []
    for item in inputs:
        max_val = item['max']
        if max_val > item['q3'] * 3:
            max_val = item['q3'] * 3
        adjusted_max_values.append(max_val)
    global_max_adjusted = max(adjusted_max_values)

    padding = (global_max_adjusted - global_min) * 0.1
    y_max   = global_max_adjusted + padding
    inputs[0]['max'] = int(y_max)

    # Preparar datos del boxplot: Chart.js requiere mínimos, máximos, cuartiles y medianas
    dataset = {
        'label': title,
        'data': inputs,
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
                        min: {inputs[0]['min']},
                        max: {inputs[0]['max']},
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