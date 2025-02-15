import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 
from multiprocessing.dummy import Pool
    
@st.cache_data(show_spinner=False)
def main(numid=None):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    data     = pd.DataFrame(columns=['nroIdentificacion','tipoPropietario','tipoDocumento','primerNombre','segundoNombre','primerApellido','segundoApellido','email','telefonos'])
   
    if isinstance(numid,str) and numid!='':
        numid = numid.split('|')
    elif isinstance(numid,(float,int)):
        numid = [f'{numid}']
    if isinstance(numid,list) and numid!=[]:
        numid = list(map(str, numid))

        if len(numid)>500:
            batches = [numid[i:i + 1000] for i in range(0, len(numid), 1000)]
            futures = [] 
            pool    = Pool(10)
            for batch in batches: 
                query = "','".join(batch)
                query = f" nroIdentificacion IN ('{query}')"
                query = f"SELECT nroIdentificacion,tipoPropietario,tipoDocumento,primerNombre,segundoNombre,primerApellido,segundoApellido,email,telefonos FROM  bigdata.data_bogota_catastro_propietario WHERE {query}"
                futures.append(pool.apply_async(downloadData,args = (query, )))
            for future in futures:
                data = pd.concat([data,future.get()])

        else:
            lista  = "','".join(numid)
            query  = f" nroIdentificacion IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT nroIdentificacion,tipoPropietario,tipoDocumento,primerNombre,segundoNombre,primerApellido,segundoApellido,email,telefonos  FROM  bigdata.data_bogota_catastro_propietario WHERE {query}" , engine)
            engine.dispose()
         
    #-------------------------------------------------------------------------#
    # Correos de la snr 
    datacomplemento = _snr_intervinientes(numid=numid)    
    data            = data.merge(datacomplemento,on='nroIdentificacion',how='outer')
    #-------------------------------------------------------------------------#
    
    if not data.empty:
        for i in [1,2,3,4,5]:
            data[f'telefono{i}'] = data['telefonos'].apply(lambda x: getparam(x,'numero',i-1))
        for i in [1,2,3]:
            data[f'email{i}'] = data['email'].apply(lambda x: getparam(x,'direccion',i-1))
        data.drop(columns=['telefonos','email'],inplace=True)
        
        vartel = [x for x in list(data) if 'telefono' in x]
        if isinstance(vartel,list) and vartel!=[]:
            data['telefonos'] = data[vartel].apply(lambda row: ' | '.join(pd.Series([str(num).split('.0')[0] for num in row if not pd.isna(num)]).unique()), axis=1)
        else: data['telefonos'] = None
        
        varmail = [x for x in list(data) if 'email' in x]
        if isinstance(varmail,list) and varmail!=[]:
            data['email'] = data[varmail].apply(lambda row: ' | '.join(pd.Series([str(num).lower() for num in row if pd.notnull(num)]).unique()) , axis=1)
        else: data['email'] = None

        varname = [x for x in ['primerNombre','segundoNombre','primerApellido','segundoApellido'] if x in data]
        if isinstance(varname,list) and varname!=[]:
            data['nombre'] = data[varname].apply(lambda row: ' '.join([str(num) for num in row if not pd.isna(num)]), axis=1)
        else: data['nombre'] = None
            
        data = data.drop_duplicates(subset='nroIdentificacion',keep='first')
        
        if 'nombre' in data and 'nombre_snr' in data:
            idd = (data['nombre'].isnull()) & (data['nombre_snr'].notnull())
            data.loc[idd,'nombre'] = data.loc[idd,'nombre_snr']
            data.drop(columns=['nombre_snr'],inplace=True)   
    return data


@st.cache_data(show_spinner=False)
def _snr_intervinientes(numid=None):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    data     = pd.DataFrame(columns=['nroIdentificacion','nombre_snr','email_snr'])
   
    if isinstance(numid,str) and numid!='':
        numid = numid.split('|')
    elif isinstance(numid,(float,int)):
        numid = [f'{numid}']
    if isinstance(numid,list) and numid!=[]:
        numid = list(map(str, numid))

        if len(numid)>500:
            batches = [numid[i:i + 1000] for i in range(0, len(numid), 1000)]
            futures = [] 
            pool    = Pool(10)
            for batch in batches: 
                query = "','".join(batch)
                query = f" documento IN ('{query}')"
                query = f"SELECT documento as nroIdentificacion , nombre as nombre_snr, email as email_snr FROM  bigdata.snr_intervinientes WHERE {query}"
                futures.append(pool.apply_async(downloadData,args = (query, )))
            for future in futures:
                data = pd.concat([data,future.get()])

        else:
            lista  = "','".join(numid)
            query  = f" documento IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data  = pd.read_sql_query(f"SELECT documento as nroIdentificacion ,nombre as nombre_snr, email as email_snr FROM  bigdata.snr_intervinientes WHERE {query}" , engine)
            engine.dispose()
    return data

def downloadData(query):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"{query}" , engine)
    engine.dispose()
    return data

def getparam(x,tipo,pos):
    try: return json.loads(x)[pos][tipo]
    except: return None
