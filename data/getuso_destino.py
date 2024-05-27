import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def getuso_destino():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    
    engine         = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    dataprecuso    = pd.read_sql_query(f"SELECT * FROM  {schema}.bogota_catastro_precuso" , engine)
    dataprecdestin = pd.read_sql_query(f"SELECT * FROM  {schema}.bogota_catastro_precdestin" , engine)
    engine.dispose()
    return dataprecuso,dataprecdestin


@st.cache_data(show_spinner=False)
def usobydestino():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data   = pd.read_sql_query(f"SELECT * FROM  {schema}.data_bogota_destinouso" , engine)
    engine.dispose()
    return data
