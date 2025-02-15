import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

def DataHistoricSearch(token=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(token,str) and token!='':
        query  = f" token='{token}' AND save=1"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data  = pd.read_sql_query(f"SELECT id as id_consulta,seccion,barmanpre,inputvar,fecha_consulta,fecha_update FROM app.tracking WHERE {query}" , engine)
        engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def barmanpre2grupo(barmanpre=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    datadirecciones = pd.DataFrame()
    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    elif isinstance(barmanpre,(float,int)):
        barmanpre = [f'{barmanpre}']
    if isinstance(barmanpre,list) and barmanpre!=[]:
        barmanpre = list(map(str, barmanpre))
        lista  = ",".join(barmanpre)
        query  = f" barmanpre IN ({lista})"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data  = pd.read_sql_query(f"SELECT grupo, barmanpre FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)
        if not data.empty:
            lista  = ",".join(data['grupo'].astype(str).unique())
            query  = f" grupo IN ({lista})"
            data   = pd.read_sql_query(f"SELECT grupo,barmanpre,general_catastro FROM  bigdata.bogota_barmanpre_caracteristicas WHERE {query}" , engine)
        engine.dispose()
        
    if not data.empty and 'general_catastro' in data:
        variable  = 'general_catastro'
        if not data.empty:
            df           = data[data[variable].notnull()]
            df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df           = df[df[variable].notnull()]
            df           = df.explode(variable)
            df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
            df           = pd.DataFrame(df)
            df.columns   = ['formato']
            df           = pd.json_normalize(df['formato'])
            if not df.empty:
                try: datadirecciones = df[['grupo','barmanpre','formato_direccion','prenbarrio']]
                except: pass

    return data,datadirecciones

