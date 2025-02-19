import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def barmanpreFromgrupo(grupo=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo  = list(map(str, grupo))
        lista  = ",".join(grupo)
        query  = f" grupo IN ({lista})"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT grupo,barmanpre FROM  bigdata.bogota_radio_barmanpre WHERE {query}" , engine)
        engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def grupoFrombarmanpre(barmanpre=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    elif isinstance(barmanpre,(float,int)):
        barmanpre = [f'{barmanpre}']
    if isinstance(barmanpre,list) and barmanpre!=[]:
        barmanpre  = list(map(str, barmanpre))
        lista  = "','".join(barmanpre)
        query  = f" barmanpre IN ('{lista}')"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT grupo,barmanpre FROM  bigdata.bogota_radio_barmanpre WHERE {query}" , engine)
        engine.dispose()
    return data
