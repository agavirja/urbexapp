import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

from functions.read_data import execute_query
from data._principal_lotes import datalote
from data._principal_caracteristicas import dataprecdestin

@st.cache_data(show_spinner=False)
def data_lotes_radio(grupo=None, variables='*',inputvar={}):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    resultado = pd.DataFrame()
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        if len(grupo)>500:
            data = execute_query(grupo, 'bogota_radio_barmanpre', variables=variables, chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_radio_barmanpre WHERE {query}", engine)
            engine.dispose()
            
    listagroup = grupo
    if not data.empty:
        for _,items in data.iterrows():
            try: 
                listagroup += items['grupo_radio'].split('|')
            except: pass
        listagroup = list(set(listagroup))
    
    if isinstance(listagroup,list) and listagroup!=[]:
        resultado = datalote(grupo=listagroup)
        
    if not resultado.empty:
        listagrupo = list(resultado['grupo'].astype(str).unique())
        datafilter = dataprecdestin(grupo=listagrupo) # Filtro por precdesting <> 65,66
        resultado  = resultado[resultado['grupo'].isin(datafilter['grupo'])]

    return resultado