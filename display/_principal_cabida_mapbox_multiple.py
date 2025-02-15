import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import random

from shapely.geometry import Polygon, MultiPolygon
import shapely.wkt as wkt

def main(altura_pisos, latitud, longitud, geopandas_lotes, geopandas_edificios, geopandas_nuevos_edificios, numero_pisos=None):
    
    
    geopandas_lotes = geopandas_lotes[geopandas_lotes['lote']==True] if 'lote' in geopandas_lotes and not geopandas_lotes.empty else pd.DataFrame()
    
    # Generar el geojson para las superficies de los lotes
    lotes_geojson = []
    for idx, row in geopandas_lotes.iterrows():
        geom         = row.geometry
        es_destacado = row['lote']  # Obtener el valor de la columna 'lote'
        lote_geojson = polygon_to_geojson(geom)
        lotes_geojson.append((idx, lote_geojson, es_destacado))
    
    # Generar el geojson de los edificios existentes con sus respectivos pisos
    edificios_geojson = []
    if not geopandas_edificios.empty:
        for idx, row in geopandas_edificios.iterrows():
            geom             = row.geometry
            connpisos        = row['connpisos']
            edificio_geojson = polygon_to_geojson(geom)
            edificios_geojson.append((idx, edificio_geojson, connpisos))

    # Generar el geojson de los nuevos edificios
    nuevos_edificios_geojson = []
    if not geopandas_nuevos_edificios.empty:
        for idx, row in geopandas_nuevos_edificios.iterrows():
            geom = row.geometry
            geojson_superficie = polygon_to_geojson(geom)
            # Si no se especifica un número de pisos, usar el parámetro por defecto
            pisos = numero_pisos if numero_pisos is not None else row.get('numero_pisos', 1)
            nuevos_edificios_geojson.append((idx, geojson_superficie, pisos))

    # Mapbox access token (replace with your token)
    access_token = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'

    html_map = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Edificios 3D en Mapbox</title>
        <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
        <link href="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.css" rel="stylesheet">
        <script src="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.js"></script>
        <style>
            body {{ margin: 0; padding: 0; }}
            #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            mapboxgl.accessToken = '{access_token}';
            const map = new mapboxgl.Map({{
                style: 'mapbox://styles/mapbox/light-v11',
                center: [{longitud}, {latitud}],
                zoom: 18,
                pitch: 45,
                bearing: -17.6,
                container: 'map',
                antialias: true
            }});

            map.on('style.load', () => {{

                // Añadir fuente y capa para los lotes
                {''.join([generate_lot_layers(idx, geojson, es_destacado) for idx, geojson, es_destacado in lotes_geojson])}

                // Añadir cada edificio existente como una fuente y capas 3D
                {''.join([generate_building_layers(idx, geojson, connpisos, altura_pisos) for idx, geojson, connpisos in edificios_geojson])}

                // Añadir los nuevos edificios como fuentes y capas 3D
                {''.join([generate_additional_building_layers(idx, geojson, pisos, altura_pisos) for idx, geojson, pisos in nuevos_edificios_geojson])}
                
            }});
        </script>
    </body>
    </html>
    """
    return html_map

def polygon_to_geojson(geom):
    if isinstance(geom, Polygon):
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[coord[0], coord[1]] for coord in geom.exterior.coords]]
            }
        }
    elif isinstance(geom, MultiPolygon):
        return {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[coord[0], coord[1]] for coord in poly.exterior.coords]]
                    }
                }
                for poly in geom.geoms
            ]
        }
    else:
        raise ValueError("Input must be a Polygon or MultiPolygon")

def generate_random_color():
    return f'#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}'

def interpolate_color(color1, color2, factor):
    """Interpolate between two colors."""
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    
    r = int(r1 + factor * (r2 - r1))
    g = int(g1 + factor * (g2 - g1))
    b = int(b1 + factor * (b2 - b1))
    
    return f'#{r:02x}{g:02x}{b:02x}'

def generate_color_function(num_pisos, color_option='gama'):
    # Color generation based on the number of floors
    if num_pisos == 0:
        return "'fill-extrusion-color': '#FFFFFF',"
    
    # For single floor or existing buildings, use a fixed gray
    if num_pisos == 1 or color_option == 'fix':
        return "'fill-extrusion-color': '#CDCDCD',"

    # For the additional building with multiple floors
    if color_option == 'random':
        colors = [generate_random_color() for _ in range(num_pisos)]
    elif color_option == 'gama':
        start_color = "#77CFF3"
        end_color = "#DFD3FD"
        colors = [interpolate_color(start_color, end_color, i / (num_pisos - 1)) for i in range(num_pisos)]
    
    # Generate color function for Mapbox
    color_function = "'fill-extrusion-color': "
    for i, color in enumerate(colors):
        if i == 0:
            color_function += f"i === {i} ? '{color}'"
        else:
            color_function += f" : i === {i} ? '{color}'"
    color_function += " : '#FFFFFF',"
    
    return color_function

def generate_lot_layers(idx, geojson, es_destacado):
    color = '#87cefa' if es_destacado else '#CDCDCD'  # Azul si es destacado, gris en caso contrario
    layers = f"""
    map.addSource('lote-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson)}
    }});

    map.addLayer({{
        'id': 'lote-{idx}',
        'type': 'fill',
        'source': 'lote-{idx}',
        'paint': {{
            'fill-color': '{color}',
            'fill-opacity': 0.5
        }}
    }});
    """
    return layers

def generate_building_layers(idx, geojson, connpisos, altura_pisos):
    # Use a fixed gray color for existing buildings, including single-floor buildings
    color_function = generate_color_function(connpisos, color_option='fix')

    layers = f"""
    map.addSource('edificio-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson)}
    }});

    for (let i = 0; i < {connpisos}; i++) {{
        map.addLayer({{
            'id': `edificio-{idx}-piso-${{i}}`,
            'type': 'fill-extrusion',
            'source': 'edificio-{idx}',
            'paint': {{
                {color_function}
                'fill-extrusion-height': (i + 1) * {altura_pisos},
                'fill-extrusion-base': i * {altura_pisos},
                'fill-extrusion-opacity': 0.7
            }}
        }});
    }}
    """
    return layers

def generate_additional_building_layers(idx, geojson_superficie, numero_pisos, altura_pisos):
    color_function = generate_color_function(numero_pisos)

    layers = f"""
    // Añadir fuente y capa para la superficie del nuevo edificio
    map.addSource('superficie-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson_superficie)}
    }});

    map.addLayer({{
        'id': 'superficie-{idx}',
        'type': 'fill',
        'source': 'superficie-{idx}',
        'paint': {{
            'fill-color': '#CDCDCD',
            'fill-opacity': 0.5
        }}
    }});

    // Añadir fuente para el nuevo edificio
    map.addSource('edificio-nuevo-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson_superficie)}
    }});

    // Añadir capas 3D para cada piso del nuevo edificio
    for (let i = 0; i < {numero_pisos}; i++) {{
        map.addLayer({{
            'id': `edificio-nuevo-{idx}-piso-${{i}}`,
            'type': 'fill-extrusion',
            'source': 'edificio-nuevo-{idx}',
            'paint': {{
                {color_function}
                'fill-extrusion-height': (i + 1) * {altura_pisos},
                'fill-extrusion-base': i * {altura_pisos},
                'fill-extrusion-opacity': 0.7
            }}
        }});
    }}
    """
    return layers
