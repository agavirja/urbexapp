import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from data.filters import main as filters

from functions.read_data import execute_query

@st.cache_data(show_spinner=False)
def datacaracteristicas(grupo=None,variables='*'):
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
            data = execute_query(grupo,'bogota_barmanpre_caracteristicas',variables=variables,chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.bogota_barmanpre_caracteristicas WHERE {query}" , engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def datapredios(grupo=None):
    data      = datacaracteristicas(grupo=grupo,variables='grupo,barmanpre,catastro_predios,general_catastro')
    resultado = pd.DataFrame(columns=['barmanpre', 'predirecc', 'precuso', 'prechip', 'precedcata', 'preaconst', 'preaterre', 'matriculainmobiliaria', 'grupo', 'prevetustzmin', 'prevetustzmax', 'estrato', 'connpisos', 'preusoph'])
    variable  = 'catastro_predios'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df)
        df.columns   = ['formato']
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
        
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
            df        = df.groupby(['grupo','barmanpre']).agg({'prevetustzmin':'min','prevetustzmax':'max','estrato':'max','connpisos':'max','preusoph':'first'}).reset_index()
            resultado = resultado.merge(df,on=['grupo','barmanpre'],how='left',validate='m:1')
    return resultado
        

@st.cache_data(show_spinner=False)
def dataprecdestin(grupo=None):
    data_precdestin = datacaracteristicas(grupo=grupo,variables='grupo,barmanpre,catastro_precdestin')
    response       = pd.DataFrame(columns=['precuso', 'precdestin', 'predios', 'grupo'])
    if not data_precdestin.empty:
        try:
            df         = data_precdestin[['grupo','catastro_precdestin']]
            df         = df[df['catastro_precdestin'].notnull()]
            df['catastro_precdestin']   = df['catastro_precdestin'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df['catastro_precdestin'].notnull()]
            df         = df.explode('catastro_precdestin')
            df         = df.apply(lambda x: {**(x['catastro_precdestin']),'grupo':x['grupo']}, axis=1)
            df         = pd.DataFrame(df)
            df.columns = ['formato']
            df         = pd.json_normalize(df['formato'])
            idd        = df['precdestin'].isin(['65','66'])
            df         = df[~idd]
            response   = df.copy()
        except: pass
    return response

@st.cache_data(show_spinner=False)
def datadane(scacodigo=None,variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    data = pd.DataFrame()
    if isinstance(scacodigo,str):
        query = f'scacodigo = "{scacodigo}"'
        data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.bogota_barrio_dane WHERE {query}" , engine)
    engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def estadisticas_predios(data=pd.DataFrame(), data_geometry=pd.DataFrame(),inputvar={}):
    output  = {
         'numerofolios':{'label': 'Número de folios de matrícula','value': None},
         'numeropredios':{'label': 'Número de matrículas únicas','value': None},
         'distribucionarea':{'label': '','value': None},
         'distribucionantiguedad':{'label': '','value': None},
         }
    
    data = filters(data=data, datageometry=data_geometry, inputvar=inputvar)
    if not data.empty:
        output['numerofolios']['value'] = len(data['grupo'].unique()) if 'grupo' in data else None
        output['numeropredios']['value'] = len(data['prechip'].unique()) if 'prechip' in data else None
        
        if 'preaconst' in data:
            output['distribucionarea']['label'] = 'Distribución por área privada'
            output['distribucionarea']['value'] = [{
                'min': data['preaconst'].min(),
                'q1': data['preaconst'].quantile(0.25),
                'median': data['preaconst'].median(),
                'q3': data['preaconst'].quantile(0.75),
                'max': data['preaconst'].max()
            }]
            
        if 'prevetustzmin' in data:
            output['distribucionantiguedad']['label'] = 'Distribución por antigüedad'
            output['distribucionantiguedad']['value'] = [{
                'min': data['prevetustzmin'].min(),
                'q1': data['prevetustzmin'].quantile(0.25),
                'median': data['prevetustzmin'].median(),
                'q3': data['prevetustzmin'].quantile(0.75),
                'max': data['prevetustzmin'].max()
            }]
    return output

@st.cache_data(show_spinner=False)
def barmanpre2grupo(barmanpre=None):
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
        barmanpre = list(map(str, barmanpre))
        lista  = ",".join(barmanpre)
        query  = f" barmanpre IN ({lista})"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data  = pd.read_sql_query(f"SELECT grupo,barmanpre FROM  bigdata.bogota_barmanpre_caracteristicas WHERE {query}" , engine)
        engine.dispose()
    return data
