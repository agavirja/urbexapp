import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 
from multiprocessing.dummy import Pool
    
user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata_lectura"]
schema   = st.secrets["schema_bigdata"]

@st.cache_data(show_spinner=False)
def main(chip):
    
    datavigencia     = pd.DataFrame()
    datashd2024      = pd.DataFrame()
    datapropietarios = pd.DataFrame()

    if isinstance(chip, list):
        
        pool    = Pool(10)
        batches = [chip[i:i + 1000] for i in range(0, len(chip), 1000)]
        futures = [] 
        for batch in batches: 
            query = "','".join(batch)
            query = f" chip IN ('{query}')"
            query = f"SELECT chip,vigencia,nroIdentificacion,valorAutoavaluo,valorImpuesto,indPago,idSoporteTributario  FROM  {schema}.data_bogota_catastro_vigencia WHERE {query}"
            futures.append(pool.apply_async(downloadData,args = (query, )))
            
        for future in futures:
            datavigencia = pd.concat([datavigencia,future.get()])
        
        futures = [] 
        for batch in batches: 
            query = "','".join(batch)
            query = f" chip IN ('{query}')"
            query = f"SELECT chip,year as vigencia,identificacion as nroIdentificacion,avaluo_catastral as valorAutoavaluo,impuesto_ajustado as valorImpuesto,copropiedad  FROM  {schema}.data_bogota_shd_2024 WHERE {query}"
            futures.append(pool.apply_async(downloadData,args = (query, )))
            
        for future in futures:
            datashd2024 = pd.concat([datashd2024,future.get()])      
        
    elif isinstance(chip, str):
        query         =  f" chip='{chip}'"
        engine        = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        datavigencia  = pd.read_sql_query(f"SELECT chip,vigencia,nroIdentificacion,valorAutoavaluo,valorImpuesto,indPago,idSoporteTributario  FROM  {schema}.data_bogota_catastro_vigencia WHERE {query}" , engine)
        datashd2024   = pd.read_sql_query(f"SELECT chip,year as vigencia,identificacion as nroIdentificacion,avaluo_catastral as valorAutoavaluo,impuesto_ajustado as valorImpuesto,copropiedad  FROM  {schema}.data_bogota_shd_2024 WHERE {query}" , engine)
        engine.dispose()
    
    if not datashd2024.empty and not datavigencia.empty:
        datashd2024  = datashd2024.drop_duplicates()
        datavigencia = pd.concat([datashd2024,datavigencia])
    elif not datashd2024.empty and datavigencia.empty:
        datavigencia = datashd2024.copy()
        
    if not datavigencia.empty:
        listaid = datavigencia[datavigencia['nroIdentificacion'].notnull()]['nroIdentificacion'].astype(str).unique()
        batches = [listaid[i:i + 1000] for i in range(0, len(listaid), 1000)]
        futures = [] 
        for batch in batches: 
            query = "','".join(batch)
            query = f" nroIdentificacion IN ('{query}')"
            query = f"SELECT nroIdentificacion,tipoPropietario,tipoDocumento,primerNombre,segundoNombre,primerApellido,segundoApellido,email,telefonos FROM  {schema}.data_bogota_catastro_propietario WHERE {query}"
            futures.append(pool.apply_async(downloadData,args = (query, )))
            
        for future in futures:
            datapropietarios = pd.concat([datapropietarios,future.get()])

    if not datapropietarios.empty:
        for i in [1,2,3,4,5]:
            datapropietarios[f'telefono{i}'] = datapropietarios['telefonos'].apply(lambda x: getparam(x,'numero',i-1))
        for i in [1,2,3]:
            datapropietarios[f'email{i}'] = datapropietarios['email'].apply(lambda x: getparam(x,'direccion',i-1))
        datapropietarios.drop(columns=['telefonos','email'],inplace=True)
        datapropietarios = datapropietarios.drop_duplicates(subset='nroIdentificacion',keep='first')
    
    if not datavigencia.empty and not datapropietarios.empty and 'nroIdentificacion' in datavigencia and 'nroIdentificacion' in datapropietarios:
        datavigencia = datavigencia.merge(datapropietarios,on='nroIdentificacion',how='left',validate='m:1')
    
    if not datavigencia.empty and 'idSoporteTributario' not in datavigencia:
        datavigencia['idSoporteTributario'] = None
        
    return datavigencia

def downloadData(query):
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"{query}" , engine)
    engine.dispose()
    return data

def getparam(x,tipo,pos):
    try: return json.loads(x)[pos][tipo]
    except: return None
