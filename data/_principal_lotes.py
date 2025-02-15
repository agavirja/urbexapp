import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine 

from functions.read_data import execute_query

@st.cache_data(show_spinner=False)
def datalote(grupo=None):
    user      = st.secrets["user_write_urbex"]
    password  = st.secrets["password_write_urbex"]
    host      = st.secrets["host_read_urbex"]
    schema    = st.secrets["schema_write_urbex"]
    data      = pd.DataFrame()
    variables ='grupo,barmanpre,latitud,longitud,ST_AsText(geometry) as wkt'
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        if len(grupo)>500:
            data = execute_query(grupo, 'bogota_lotes_geometry', variables=variables, chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_lotes_geometry WHERE {query}", engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def dataconstrucciones(barmanpre=None):
    user      = st.secrets["user_write_urbex"]
    password  = st.secrets["password_write_urbex"]
    host      = st.secrets["host_read_urbex"]
    schema    = 'shapefile'
    data      = pd.DataFrame()
    variables ='lotecodigo as barmanpre,connpisos,contsemis,connsotano,conaltura,conelevaci,ST_AsText(geometry) as wkt'
    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    elif isinstance(barmanpre,(float,int)):
        barmanpre = [f'{barmanpre}']
    if isinstance(barmanpre,list) and barmanpre!=[]:
        barmanpre = list(map(str, barmanpre))
        lista     = ",".join(barmanpre)
        query     = f" lotecodigo IN ({lista})"
        engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT {variables} FROM shapefile.bogota_construcciones WHERE {query}", engine)
        engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def lotes_vecinos(grupo=None):
    user       = st.secrets["user_write_urbex"]
    password   = st.secrets["password_write_urbex"]
    host       = st.secrets["host_read_urbex"]
    schema     = 'shapefile'
    data       = datalote(grupo=grupo)
    data_lotes = pd.DataFrame()
    data_construcciones = pd.DataFrame()
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['geometry'] = data['geometry'].apply(lambda x: x.buffer(0.00000001))
        
        query = ''
        for items in data['geometry']:
            query += f' OR ST_INTERSECTS(ST_GEOMFROMTEXT("{items.wkt}"),geometry)'
        
        if isinstance(query,str) and query!='':
            query      = query.strip().strip('OR')
            engine     = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data_lotes = pd.read_sql_query(f"SELECT grupo,barmanpre,ST_AsText(geometry) as wkt FROM bigdata.bogota_lotes_geometry WHERE {query}" , engine)
            engine.dispose()
            
    if not data_lotes.empty:
        barmanprelist       = list(data_lotes['barmanpre'].unique())
        data_construcciones = dataconstrucciones(barmanpre=barmanprelist)
        if not data_construcciones.empty:
            datamerge           = data_lotes.drop_duplicates(subset=['barmanpre'],keep='first')
            data_construcciones = data_construcciones.merge(datamerge[['barmanpre','grupo']],on='barmanpre',how='left',validate='m:1')
            
    return data_lotes,data_construcciones