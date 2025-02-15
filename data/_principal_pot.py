import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from functions.read_data import execute_query

@st.cache_data(show_spinner=False)
def datapot(grupo=None,variables='*'):
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
        grupo = list(map(str, grupo))
        if len(grupo)>500:
            data = execute_query(grupo,'bogota_barmanpre_POT',variables=variables,chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.bogota_barmanpre_POT WHERE {query}" , engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def data_pot(grupo=None):
    data      = datapot(grupo=grupo,variables='grupo,barmanpre,POT')
    datapaso  = pd.DataFrame(columns=['barmanpre', 'predirecc', 'precuso', 'prechip', 'precedcata', 'preaconst', 'preaterre', 'matriculainmobiliaria', 'grupo', 'prevetustzmin', 'prevetustzmax', 'estrato', 'connpisos', 'preusoph'])
    datafinal = pd.DataFrame(columns=['grupo', 'barmanpre','variable','valor'])
    variable  = 'POT'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df)
        df.columns   = ['formato']
        df           = pd.json_normalize(df['formato'])
        datapaso     = df.copy()
    if not datapaso.empty:
        variables      = [x for x in list(datapaso) if not any([w for w in ['grupo','barmanpre'] if x in w]) ]
        datapaso.index = range(len(datapaso))
        for i in range(len(datapaso)):
            datalong  = datapaso.iloc[[i]]
            resultado = datalong[['grupo','barmanpre']]
            for variable in variables:
                df           = datalong[['grupo','barmanpre',variable]]
                df           = df[df[variable].notnull()]
                df           = df.explode(variable)
                df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
                df           = pd.DataFrame(df,columns= ['formato'])
                df           = pd.json_normalize(df['formato'])
                resultado    = resultado.merge(df,on=['grupo','barmanpre'],how='outer')
            resultado = pd.melt(resultado,id_vars=['grupo', 'barmanpre'], var_name='variable', value_name='valor')
            datafinal = pd.concat([datafinal,resultado])
    return datafinal
