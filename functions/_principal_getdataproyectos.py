import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from shapely.geometry import Point

from data._principal_proyectos import datacompletaproyectos

from functions._principal_getdatalotes import main as getdatalotes

@st.cache_data(show_spinner=False)
def main(grupo=None,polygon=None): 
    
    data_precios = pd.DataFrame(columns=['codinmueble', 'codproyecto', 'precio', 'construye'])
    
    #-------------------------------------------------------------------------#
    # Grupo: trae el radio para un lote en particular o lista de lotes
    if grupo is not None:
        data_precios = datacompletaproyectos(grupo=grupo)
        
    #-------------------------------------------------------------------------#
    # Polygon: Cuando la consulta es sobre un poligono particular
    elif polygon is not None and isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        data_getlotes = getdatalotes(inputvar={'polygon':polygon})
        grupo         = list(data_getlotes['grupo'].unique()) if not data_getlotes.empty and 'grupo' in data_getlotes else []
        data_precios  = datacompletaproyectos(grupo=grupo)
        
        if not data_precios.empty:
            data_precios = data_precios.drop_duplicates()
            
            data_precios['geometry'] = data_precios.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
            data_precios             = gpd.GeoDataFrame(data_precios, geometry='geometry')

            polygonref   = wkt.loads(polygon)
            idd          = data_precios['geometry'].apply(lambda x: polygonref.contains(x))
            data_precios = data_precios[idd]
            
            data_precios.drop(columns=['geometry'],inplace=True)
            data_precios = pd.DataFrame(data_precios)
            
    return data_precios
