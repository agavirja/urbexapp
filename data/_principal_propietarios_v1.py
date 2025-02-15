import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from data.filters import main as filters

from functions.read_data import execute_propietarios_query

@st.cache_data(show_spinner=False)
def datapropietarios(identificacion=None,variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(identificacion,str) and identificacion!='':
        identificacion = identificacion.split('|')
    elif isinstance(identificacion,(float,int)):
        identificacion = [f'{identificacion}']
    if isinstance(identificacion,list) and identificacion!=[]:
        identificacion = list(map(str, identificacion))
        if len(identificacion)>500:
            data = execute_propietarios_query(identificacion,'general_propietarios',variables=variables,chunk_size=500)
        else:
            lista  = "','".join(identificacion)
            query  = f" numero IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.general_propietarios WHERE {query}" , engine)
            engine.dispose()
    return data


@st.cache_data(show_spinner=False)
def propietarios_shd_historicos(identificacion=None,variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(identificacion,str) and identificacion!='':
        identificacion = identificacion.split('|')
    elif isinstance(identificacion,(float,int)):
        identificacion = [f'{identificacion}']
    if isinstance(identificacion,list) and identificacion!=[]:
        identificacion = list(map(str, identificacion))
        if len(identificacion)>500:
            data = execute_propietarios_query(identificacion,'bogota_propietarios_shd_historicos',variables=variables,chunk_size=500)
        else:
            lista  = "','".join(identificacion)
            query  = f" numero IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.bogota_propietarios_shd_historicos WHERE {query}" , engine)
            engine.dispose()
    return data