import streamlit as st
import geopandas as gpd
import pandas as pd
import geojson
import numpy as np
from shapely import wkt
from area import area as areapolygon
from sqlalchemy import create_engine 

from functions.circle_polygon import circle_polygon

@st.cache_data(show_spinner=False)
def main(polygon_wkt):
    
    poligono_lote = wkt.loads(polygon_wkt)
    arealote      = getareapolygon(poligono_lote)
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    poly     = circle_polygon(np.sqrt(arealote)*5,poligono_lote.centroid.y,poligono_lote.centroid.x)
    esquinero = False
    
    query        = f' ST_INTERSECTS(ST_GEOMFROMTEXT("{poly.wkt}"),geometry)'
    data_andenes = pd.read_sql_query(f"SELECT id,ST_AsText(geometry) as wkt FROM shapefile.bogota_andenes WHERE {query}" , engine)
    data_vias    = pd.read_sql_query(f"SELECT id,calancho,callongitu,caltsuperf,ST_AsText(geometry) as wkt FROM shapefile.bogota_calzada WHERE {query}" , engine)
    engine.dispose()
    
    if not data_andenes.empty:
        data_andenes['geometry'] = gpd.GeoSeries.from_wkt(data_andenes['wkt'])
        data_andenes             = gpd.GeoDataFrame(data_andenes, geometry='geometry')

        coords       = [circle_polygon(5,y,x) for x,y in list(poligono_lote.exterior.coords)]
        dataradio    = gpd.GeoDataFrame(geometry=coords)
        result       = gpd.sjoin(data_andenes, dataradio, how='inner')
        data_andenes = data_andenes[data_andenes['id'].isin(result['id'])]
        
    if not data_andenes.empty and not data_vias.empty:
        dataradio             = data_andenes.copy()
        dataradio['latitud']  = dataradio['geometry'].apply(lambda x: x.centroid.y)
        dataradio['longitud'] = dataradio['geometry'].apply(lambda x: x.centroid.x)
        dataradio['geometry'] = dataradio.apply(lambda x: circle_polygon(5,x['latitud'],x['longitud']),axis=1)
        dataradio             = gpd.GeoDataFrame(dataradio, geometry='geometry')
        dataradio             = dataradio[['geometry']]
        data_vias['geometry'] = gpd.GeoSeries.from_wkt(data_vias['wkt'])
        data_vias             = gpd.GeoDataFrame(data_vias, geometry='geometry')
        result                = gpd.sjoin(data_vias, dataradio, how='inner')
        data_vias             = data_vias[data_vias['id'].isin(result['id'])]
        
    dataunion = gpd.GeoDataFrame()
    if not data_andenes.empty and not data_vias.empty:
        dataunion = gpd.sjoin(data_andenes[['geometry']], data_vias[['calancho', 'callongitu', 'caltsuperf', 'geometry']], how='inner')
    elif not data_andenes.empty and data_vias.empty:
        dataunion = data_andenes.copy()
    elif  data_andenes.empty and not data_vias.empty:
        dataunion = data_vias.copy()
        
    for ddbb in [data_andenes,data_vias,dataunion]:
        if not ddbb.empty:
            variables = [x for x in ['index_right', 'isin'] if x in ddbb]
            if variables!=[]:
                ddbb.drop(columns=variables,inplace=True)
            
    if not data_andenes.empty and len(data_andenes)>1: esquinero = True
        
    
    return data_andenes,data_vias,dataunion,esquinero

def getareapolygon(polygon):
    try:
        geojson_polygon = geojson.dumps(polygon)
        return areapolygon(geojson_polygon)
    except: return None
