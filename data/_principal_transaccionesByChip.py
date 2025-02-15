import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 
from multiprocessing.dummy import Pool
    
@st.cache_data(show_spinner=False)
def main(chip=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame(columns=['id', 'docid', 'response', 'fecha_consulta', 'codigo', 'nombre', 'tarifa', 'aper', 'inscrip', 'cuantia', 'valor', 'tipo_documento_publico', 'numero_documento_publico', 'fecha_documento_publico', 'numero', 'referencia', 'nir', 'oficina', 'entidad', 'fecha', 'datos_solicitante', 'datos_documento', 'titular', 'email', 'tipo', 'identificacion', 'oficina2code', 'variable', 'value', 'chip', 'value_new', 'matriculainmobiliaria', 'barmanpre', 'precbarrio', 'predirecc', 'preaconst', 'preaterre', 'precuso', 'precdestin', 'prevetustz', 'grupo'])
   
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    elif isinstance(chip,(float,int)):
        chip = [f'{chip}']
    if isinstance(chip,list) and chip!=[]:
        chip = list(map(str, chip))

        if len(chip)>500:
            batches = [chip[i:i + 1000] for i in range(0, len(chip), 1000)]
            futures = [] 
            pool    = Pool(10)
            for batch in batches: 
                query = "','".join(batch)
                query = f" chip IN ('{query}')"
                query = f"SELECT chip,transacciones FROM  bigdata.bogota_chip_transacciones WHERE {query}"
                futures.append(pool.apply_async(downloadData,args = (query, )))
            for future in futures:
                data = pd.concat([data,future.get()])

        else:
            lista  = "','".join(chip)
            query  = f" chip IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT chip,transacciones FROM  bigdata.bogota_chip_transacciones WHERE {query}" , engine)
            engine.dispose()
         
    if not data.empty:
        variable  = 'transacciones'
        if not data.empty:
            df           = data[data[variable].notnull()]
            df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df           = df[df[variable].notnull()]
            df           = df.explode(variable)
            df           = df.apply(lambda x: {**(x[variable]), 'chip': x['chip']}, axis=1)
            df           = pd.DataFrame(df)
            df.columns   = ['formato']
            df           = pd.json_normalize(df['formato'])
            data         = df.copy()
            
        if "fecha_documento_publico" in data:
            data['fecha_documento_publico'] = pd.to_datetime(data['fecha_documento_publico'], unit='ms')

    return data

def downloadData(query):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"{query}" , engine)
    engine.dispose()
    return data
