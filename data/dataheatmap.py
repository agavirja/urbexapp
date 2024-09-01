import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(year=2024,formato='grid'):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    query = ""
    if year is not None and (isinstance(year, float) or isinstance(year, int)):
        query += f" AND year = {year}"

    if isinstance(formato, str):
        query += f" AND type ='{formato}'"
     
    if query!="":
        query = query.strip().strip('AND')
        query = f" WHERE {query}"

    data  = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_heatmap_transacciones {query}" , engine)
    
    if not data.empty:
        lista = "','".join(data['id_map'].astype(int).astype(str).unique())
        query = f" id_map IN ('{lista}') AND type ='{formato}'"
        datashape  = pd.read_sql_query(f"SELECT id_map, ST_AsText(geometry) as wkt FROM  bigdata.bogota_heatmap_shape WHERE {query}" , engine)
        if not datashape.empty:
            datamerge = datashape.drop_duplicates(subset='id_map',keep='first')
            data      = data.merge(datamerge,on='id_map',how='left',validate='m:1')
            
    engine.dispose()
    return data
    
@st.cache_data(show_spinner=False)
def selectpolygon(polygon=None,formato='grid'):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    result = []
    query  = ""
    if isinstance(polygon, str) and not 'none' in polygon.lower() and isinstance(formato, str):
        query += f' type="{formato}" AND (ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), geometry) OR ST_INTERSECTS(ST_GEOMFROMTEXT("{polygon}"), geometry) OR ST_TOUCHES(ST_GEOMFROMTEXT("{polygon}"), geometry))'
    if query!='':
        data = pd.read_sql_query(f"SELECT distinct(id_map) as id_map FROM  bigdata.bogota_heatmap_shape WHERE {query}" , engine)
        if not data.empty:
            result = list(data['id_map'].unique())
    engine.dispose()
    return result
