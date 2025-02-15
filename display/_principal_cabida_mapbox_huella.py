import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import random

from shapely.geometry import Polygon, MultiPolygon
import shapely.wkt as wkt

def main(latitud, longitud, geopandas_lotes):
    # Generar el geojson para las superficies de los lotes
    lotes_geojson = geopandas_lotes.to_json()
        
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
        <div id="lotem"></div>
        <script>
            mapboxgl.accessToken = '{access_token}';
            const lotem = new mapboxgl.Map({{
                style: 'mapbox://styles/mapbox/light-v11',
                center: [{longitud}, {latitud}],
                zoom: 17,
                pitch: 0,
                bearing: 0,
                container: 'lotem',
                antialias: true
            }});
    
            lotem.on('style.load', () => {{
                // Añadir capa para los lotes
                lotem.addSource('lotes', {{
                    'type': 'geojson',
                    'data': {lotes_geojson}
                }});
    
                lotem.addLayer({{
                    'id': 'lotes-fill',
                    'type': 'fill',
                    'source': 'lotes',
                    'paint': {{
                        'fill-color': ['get', 'color'], // Usa la propiedad 'color' para el color de relleno
                        'fill-opacity': 0.5
                    }}
                }});
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

def generate_lot_layers(idx, geojson, color):
    layers = f"""
    lotem.addSource('lote-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson)}
    }});

    lotem.addLayer({{
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
