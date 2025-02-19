import streamlit as st
import pandas as pd
import re
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def chip2direccion(chip):
    result = None
    if isinstance(chip,str) and chip!="":
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        query    = f"prechip='{chip}'"
        data     = pd.read_sql_query(f"SELECT predirecc FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66') LIMIT 1" , engine)
        if not data.empty:
            result = data['predirecc'].iloc[0]
        engine.dispose()
    return result

@st.cache_data(show_spinner=False)
def matricula2direccion(matricula):
    result = None
    #matricula = '050N20616596'
    if matricula is not None and matricula!="" and isinstance(matricula,str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
        try:
            matricula    = re.sub(r"[^0-9A-Za-z]",'',matricula).upper()
            coincidencia = re.search(r"[A-Za-z]", matricula)
            parte1       = matricula[:coincidencia.start()]
            parte2       = matricula[coincidencia.start()+1:]
            letra        = re.sub('[^a-zA-Z]','',matricula)
            
            matriculas = [matricula, 
                          f'{parte1}{letra}{parte2}',
                          f'{parte1.lstrip("0")}{letra}{parte2}',
                          f'{parte1}{letra}0{parte2}',
                          f'{parte1.lstrip("0")}{letra}0{parte2}',
                          f'{parte1.lstrip("0")}{letra}{parte2.lstrip("0")}',
                          f'0{parte1.lstrip("0")}{letra}{parte2}',
                          f'0{parte1.lstrip("0")}{letra}{parte2.lstrip("0")}',
                          f'0{parte1.lstrip("0")}{letra}0{parte2.lstrip("0")}',
                          f'{parte1}{letra}0{parte2.lstrip("0")}',   
                          f'{parte1.lstrip("0")}{letra}0{parte2.lstrip("0")}',  
                          f'{parte1}{letra}{parte2.lstrip("0")}',
                          f'0{parte1.lstrip("0")}{letra}00{parte2.lstrip("0")}',
                          f'0{parte1.lstrip("0")}{letra}{parte2.lstrip("0")}',
                          f'{parte1}{letra}00{parte2.lstrip("0")}',
                          f'{parte1.lstrip("0")}{letra}00{parte2.lstrip("0")}',
                          ]
            lista = "','".join(list(set(matriculas)))
            query = f" matriculainmobiliaria IN ('{lista}')"
            data  = pd.read_sql_query(f"SELECT direccion FROM  bigdata.data_bogota_shd_2025_objeto_predial WHERE {query} " , engine)
            if not data.empty:
                data = pd.read_sql_query(f"SELECT direccion FROM  bigdata.data_bogota_shd_objetocontrato WHERE {query} " , engine)
            if not data.empty:
                result = data['direccion'].iloc[0]
        except: pass
        engine.dispose()
    return result

@st.cache_data(show_spinner=False)
def buildinglist():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query("SELECT nombre_conjunto,formato_direccion as direccion FROM  bigdata.bogota_nombre_conjuntos " , engine)
    engine.dispose()
    if not data.empty:
        data = data[~data['nombre_conjunto'].str.contains(r'^\d+$')]
    if not data.empty:
        idd  = data['nombre_conjunto'].isin(['CASA','EDIFICIO'])
        data = data[~idd]
    data = pd.concat([pd.DataFrame([{'nombre_conjunto':'','direccion':''}]),data])
    return data 
