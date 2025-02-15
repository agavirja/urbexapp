import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import random

from shapely.geometry import Polygon, MultiPolygon
import shapely.wkt as wkt

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

def main(numero_pisos, altura_pisos, latitud, longitud, polygon, newpolygon):
    
    geojson_superficie = polygon_to_geojson(polygon)
    geojson_edificio   = polygon_to_geojson(newpolygon)

    # Generar función de colores aleatorios
    color_function = generate_color_function(numero_pisos)

    access_token = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'

    html_map = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Edificio 3D en Mapbox</title>
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
                // Añadir fuente y capa para la superficie
                map.addSource('superficie', {{
                    'type': 'geojson',
                    'data': {json.dumps(geojson_superficie)}
                }});

                map.addLayer({{
                    'id': 'superficie',
                    'type': 'fill',
                    'source': 'superficie',
                    'paint': {{
                        'fill-color': '#888888',
                        'fill-opacity': 0.5
                    }}
                }});

                // Añadir fuente para el edificio
                map.addSource('edificio', {{
                    'type': 'geojson',
                    'data': {json.dumps(geojson_edificio)}
                }});

                // Añadir capas 3D para cada piso
                for (let i = 0; i < {numero_pisos}; i++) {{
                    map.addLayer({{
                        'id': `edificio-piso-${{i}}`,
                        'type': 'fill-extrusion',
                        'source': 'edificio',
                        'paint': {{
                            {color_function}
                            'fill-extrusion-height': (i + 1) * {altura_pisos},
                            'fill-extrusion-base': i * {altura_pisos},
                            'fill-extrusion-opacity': 0.7
                        }}
                    }});
                }}
            }});
        </script>
    </body>
    </html>
    """

    return html_map

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

def generate_color_function(num_pisos):
    options = 'gama' # 'fix' | 'gama' | 'random' 

    # Random
    if 'random' in options:
        colors = [generate_random_color() for _ in range(num_pisos)]
        
    if 'gama' in options:
        start_color = "#77CFF3" #  #CCC0EA
        end_color   = "#DFD3FD"
        colors      = [interpolate_color(start_color, end_color, i / (num_pisos - 1)) for i in range(num_pisos)]

    if 'fix' in options:
        colors = ['#CCC0EA']*num_pisos
        
    color_function = "'fill-extrusion-color': "
    for i, color in enumerate(colors):
        if i == 0:
            color_function += f"i === {i} ? '{color}'"
        else:
            color_function += f" : i === {i} ? '{color}'"
    color_function += " : '#FFFFFF',"
        
    return color_function
