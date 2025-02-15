import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def getlicencias(barmanpre=None):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.DataFrame()

    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    elif isinstance(barmanpre,(float,int)):
        barmanpre = [f'{barmanpre}']
    if isinstance(barmanpre,list) and barmanpre!=[]:
        barmanpre = list(map(str, barmanpre))
        query = ' OR '.join([f'barmanpre LIKE "%{item}%"' for item in barmanpre])
        data  = pd.read_sql_query(f"SELECT * FROM  {schema}.data_bogota_licencias WHERE {query}" , engine)
    engine.dispose()
    
    return data
    
    