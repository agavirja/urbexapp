import streamlit as st
import pandas as pd
import json
import concurrent.futures
from sqlalchemy import create_engine 

from data._principal_caracteristicas import datacaracteristicas

from functions.read_data import execute_query

@st.cache_data(show_spinner=False)
def localidad(locnombre=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    table        = 'bogota_localidades_simplify'
    datageometry = pd.DataFrame()
    if isinstance(locnombre,str) and locnombre!='':
        locnombre = locnombre.split('|')
    elif isinstance(locnombre,(float,int)):
        locnombre = [f'{locnombre}']
    if isinstance(locnombre,list) and locnombre!=[]:
        locnombre    = list(map(str, locnombre))
        lista        = "','".join(locnombre)
        query        = f" locnombre IN ('{lista}')"
        datageometry = pd.read_sql_query(f"SELECT locnombre,loccodigo, ST_AsText(geometry) as wkt FROM  shapefile.{table} WHERE {query}" , engine)
    dataoptions = pd.read_sql_query(f"SELECT locnombre,loccodigo FROM  shapefile.{table}" , engine)
    engine.dispose()
    return datageometry,dataoptions


@st.cache_data(show_spinner=False)
def getscacodigo(grupo=None):
    
    data_general  = pd.DataFrame()
    dataresultado = pd.DataFrame(columns=['grupo', 'scacodigo','wkt'])
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_caracteristicas = executor.submit(datacaracteristicas, grupo=grupo, variables='grupo,general_catastro')
        data_general           = future_caracteristicas.result()
    
    if not data_general.empty:
        data = data_general.copy()
        item = 'general_catastro'
        if item in data:
            df         = data[['grupo',item]]
            df         = df[df[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'grupo': x['grupo']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                dataresultado = df[['grupo','precbarrio']]
                dataresultado.rename(columns={'precbarrio':'scacodigo'},inplace=True)

    if not dataresultado.empty and 'scacodigo' in dataresultado:    
        user     = st.secrets["user_write_urbex"]
        password = st.secrets["password_write_urbex"]
        host     = st.secrets["host_read_urbex"]
        schema   = st.secrets["schema_write_urbex"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

        lista      = "','".join(dataresultado['scacodigo'].unique())
        query      = f" scacodigo IN ('{lista}')"
        databarrio = pd.read_sql_query(f"SELECT scacodigo,ST_AsText(geometry) as wkt FROM  shapefile.bogota_barriocatastro_simplify WHERE {query}" , engine)
        engine.dispose()
            
        if not databarrio.empty:
            databarrio    = databarrio.drop_duplicates(subset='scacodigo',keep='first') 
            dataresultado = dataresultado.merge(databarrio,on='scacodigo',how='left',validate='m:1')
            
    return dataresultado
