import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from functions.read_data import execute_query
from data.filters import main as filters
from data._principal_lotes_radio import data_lotes_radio

# grupo = [610954, 360528]
# grupo = ['610954', '360528']
# grupo = 610954
# grupo = '610954'
# grupo = '610954|360528'

@st.cache_data(show_spinner=False)
def datatransacciones(grupo=None, variables='*'):
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
            data = execute_query(grupo, 'bogota_barmanpre_transacciones', variables=variables, chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_transacciones WHERE {query}", engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def data_anotaciones(grupo=None):
    variables  = 'grupo,barmanpre,anotaciones'
    data       = datatransacciones(grupo=grupo, variables=variables)
    resultado  = pd.DataFrame()
    variable   = 'anotaciones'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
    return resultado

@st.cache_data(show_spinner=False)
def data_transacciones(grupo=None):
    variables  = 'grupo,barmanpre,transacciones_barmanpre'
    data       = datatransacciones(grupo=grupo, variables=variables)
    resultado  = pd.DataFrame()
    variable   = 'transacciones_barmanpre'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
    return resultado 

    
@st.cache_data(show_spinner=False)
def estadisticas_transacciones(data=pd.DataFrame(), data_geometry=pd.DataFrame(),inputvar={}):
    output  = {
         'numerotransacciones':{'label': 'Número de transacciones (últimos 12 meses)','value': None},
         'valortransacciones':{'label': 'Valor promedio de transacciones por mt2 (últimos 12 meses)','value': None},
         'lotescontransacciones':{'label': '','value': None},
         'transaccionesyear':{'label': 'Histórico transacciones','value': None},
         }
    
    data = filters(data=data, datageometry=pd.DataFrame(), inputvar=inputvar)
    if not data.empty:
        df               = data.copy()
        df['fecha']      = pd.to_datetime(df['fecha_documento_publico'], unit='ms')
        df['year']       = df['fecha'].apply(lambda x: x.year)
        df['preaconst']  = pd.to_numeric(df['preaconst'],errors='coerce') if 'preaconst' in df else None
        df['cuantia']    = pd.to_numeric(df['cuantia'],errors='coerce') if 'cuantia' in df else None
        df['cuantiamt2'] = None
        idd              = (df['cuantia']>0) & (df['preaconst']>0)
        df.loc[idd,'cuantiamt2'] = df.loc[idd,'cuantia']/df.loc[idd,'preaconst'] 
        df               = df[(df['cuantiamt2']>1000000)]
        if not df.empty:
            filtro_fecha = pd.Timestamp.today() - pd.DateOffset(months=12)
            datalast12m  = df[df['fecha'].between(filtro_fecha, pd.Timestamp.today())]
            if not datalast12m.empty:
                output.update({'numerotransacciones':{'label':'Número de transacciones (últimos 12 meses)','value':len(datalast12m)}})
                output.update({'valortransacciones':{'label':'Valor promedio de transacciones por mt2 (últimos 12 meses)','value':datalast12m['cuantiamt2'].median()}})
                
                w = datalast12m.groupby('grupo').agg({'cuantiamt2':['median','count']}).reset_index()
                w.columns = ['grupo','cuantiamt2','transacciones']
                output.update({'lotescontransacciones':{'label':'','value':w.to_dict(orient='records')}})
                
            datagroup = df.copy()
            datagroup = datagroup[datagroup['year']>2020]
            datagroup = datagroup.groupby('year').agg({'cuantiamt2':['median','count']}).reset_index()
            datagroup.columns = ['year','cuantiamt2','transacciones']
            datagroup = datagroup.to_dict(orient='records')
            output.update({'transaccionesyear':{'label':'Histórico transacciones','value':datagroup}})
    return output

def transformjson(x):
    result = []
    try:
        data_dict = json.loads(x)
        
        for tipo, transacciones in data_dict.items():
            for transaccion in transacciones:
                transaccion['tipo'] = tipo  # Añadir el campo 'tipo'
                result.append(transaccion)
    except: result = None
    return result