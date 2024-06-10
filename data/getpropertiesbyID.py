import streamlit as st
import re
import pandas as pd
from unidecode import unidecode
from sqlalchemy import create_engine 

from data.getuso_destino import getuso_destino

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    datasnr,dataproceso = getSNRbyID(inputvar)
    datashd = getSHDbyID(inputvar)
    data    = pd.DataFrame()
    
    if not datasnr.empty and not datashd.empty:
        datasnr['fuente'] = 'snr'
        datashd['fuente'] = 'shd'
        data = pd.concat([datasnr,datashd])
    elif datasnr.empty and not datashd.empty:
        datashd['fuente'] = 'shd'
        data = datashd.copy()
    elif not datasnr.empty and datashd.empty:
        datasnr['fuente'] = 'snr'
        data = datasnr.copy()

    if not data.empty:
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        dataprecdestin.rename(columns={'codigo':'precdestin','tipo':'actividad','descripcion':'desc_actividad'},inplace=True)
        data = data.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        data = data.merge(dataprecdestin,on='precdestin',how='left',validate='m:1')

    return data,dataproceso

@st.cache_data(show_spinner=False)
def getSNRbyID(inputvar):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    #-------------------------------------------------------------------------#
    # Data transacciones SNR
    
    tipodocumento  = inputvar['tipodocumento'] if 'tipodocumento' in inputvar and inputvar['tipodocumento'] is not None and inputvar['tipodocumento'] != '' else None
    identificacion = inputvar['identificacion'] if 'identificacion' in inputvar and inputvar['identificacion'] is not None and inputvar['identificacion'] != '' else None
    titular        = inputvar['titular'] if 'titular' in inputvar and inputvar['titular'] is not None and inputvar['titular'] != '' else None
    dataid1        = pd.DataFrame()
    dataid2        = pd.DataFrame()
    datatitular    = pd.DataFrame()
    dataproceso    = pd.DataFrame()
    
    if identificacion is not None and identificacion!='':
        identificacion = [re.sub('[^0-9]', '', str(x)) for x in identificacion.split(',') if len(re.sub('[^0-9]', '', str(x))) >= 6]
        if identificacion:
            query      = "','".join(identificacion)
            dataid1    = pd.read_sql_query(f"SELECT * FROM {schema}.snr_id2docid WHERE nroIdentificacion IN ('{query}')" , engine)
            query      = " OR ".join([f"nroIdentificacion LIKE '%{id}%'" for id in identificacion])
            dataid2    = pd.read_sql_query(f"SELECT * FROM {schema}.snr_id2docid WHERE {query}" , engine)
    if titular is not None and titular!='':
        titular = titular.split(',')
        query   = " OR ".join([
                    "(" + " AND ".join([
                        f"LOWER(titular) LIKE '%{word}%'" 
                        for word in re.sub(r'\s+', ' ', unidecode(t).strip().lower()).split()
                    ]) + ")"
                    for t in titular
                ])
        datatitular = pd.read_sql_query(f"SELECT * FROM {schema}.snr_id2docid WHERE {query}" , engine) 
    data = pd.concat([dataid1,dataid2,datatitular])
    if not data.empty and 'tipoDocumento' in data and tipodocumento is not None and tipodocumento != '':
        data = data[data['tipoDocumento']==tipodocumento]
    
    if not data.empty:
        data        = data.drop_duplicates()
        query       = "','".join(data[data['docid'].notnull()]['docid'].astype(str).unique())
        query       = f" docid IN ('{query}')"  
        dataproceso = pd.read_sql_query(f"SELECT docid,codigo,nombre,tarifa,cuantia  FROM  {schema}.snr_tabla_procesos WHERE {query}" , engine)
        datamerge   = pd.read_sql_query(f"SELECT docid,entidad,fecha_documento_publico  FROM  {schema}.snr_data_completa WHERE {query}" , engine)         
        datamerge   = datamerge.drop_duplicates(subset='docid',keep='first')
        data        = data.merge(datamerge,on='docid',how='left',validate='m:1')
        
    databogota = pd.DataFrame()
    if not data.empty and 'oficina' in data:
        idd        = (data['oficina'].astype(str).str.lower().str.contains('bogota')) & (data['entidad'].astype(str).str.lower().str.contains('bogota'))
        databogota = data[idd]
        data       = data[~idd]
    
    if not databogota.empty:
        if 'docid' in databogota and databogota[databogota['docid'].notnull()].empty is False:
            query         = "','".join(databogota[databogota['docid'].notnull()]['docid'].astype(str).unique())
            query         = f" docid IN ('{query}')"        
            datamatricula = pd.read_sql_query(f"SELECT docid,value,variable FROM  {schema}.snr_data_matricula WHERE {query}" , engine)
            databogota    = datamatricula.merge(databogota,on='docid',how='left',validate='m:1')    
            #dataproceso   = pd.read_sql_query(f"SELECT docid,codigo,nombre,tarifa,cuantia  FROM  {schema}.snr_tabla_procesos WHERE {query}" , engine)         
            
        if 'value' in databogota and databogota[databogota['value'].notnull()].empty is False:
            query         = "','".join(databogota[databogota['value'].notnull()]['value'].astype(str).unique())
            query         = f" numeroMatriculaInmobiliaria IN ('{query}')"        
            datachip      = pd.read_sql_query(f"SELECT numeroMatriculaInmobiliaria as value,numeroChip as prechip FROM  {schema}.data_bogota_catastro_predio WHERE {query}" , engine)
        
            if datachip.empty is False and datachip[datachip['prechip'].notnull()].empty is False: 
                query         = "','".join(datachip[datachip['prechip'].notnull()]['prechip'].astype(str).unique())
                query         = f" prechip IN ('{query}')"        
                datacatastro  = pd.read_sql_query(f"SELECT prechip,predirecc,prenbarrio,preaterre,preaconst,precdestin,precuso,barmanpre,latitud,longitud  FROM  {schema}.data_bogota_catastro WHERE {query}" , engine)
                if not datacatastro.empty:
                    datachip   = datachip.merge(datacatastro,on='prechip',how='left',validate='m:1')
                    datachip   = datachip.drop_duplicates(subset='value',keep='first')
                    databogota = databogota.merge(datachip,on='value',how='left',validate='m:1')
        
        if 'barmanpre' in databogota and databogota[databogota['barmanpre'].notnull()].empty is False:
            query      = "','".join(databogota[databogota['barmanpre'].notnull()]['barmanpre'].unique())
            query      = f" lotcodigo IN ('{query}')"        
            datalote   = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  {schema}.data_bogota_lotes WHERE {query}" , engine)
            databogota = databogota.merge(datalote,on='barmanpre',how='left',validate='m:1')
    engine.dispose()
    
    data = pd.concat([databogota,data])
    if 'wkt' in data:
        data = data[data['wkt'].notnull()]
    
    variables = [x for x in ['fecha','email','variable','id'] if x in data]
    if variables!=[]:
        data.drop(columns=variables,inplace=True)
        
    return data,dataproceso
    
    
@st.cache_data(show_spinner=False)
def getSHDbyID(inputvar):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    #-------------------------------------------------------------------------#
    # Data prediales Bogota
    tipodocumento  = inputvar['tipodocumento'] if 'tipodocumento' in inputvar and inputvar['tipodocumento'] is not None and inputvar['tipodocumento'] != '' else None
    identificacion = inputvar['identificacion'] if 'identificacion' in inputvar and inputvar['identificacion'] is not None and inputvar['identificacion'] != '' else None
    titular        = inputvar['titular'] if 'titular' in inputvar and inputvar['titular'] is not None and inputvar['titular'] != '' else None
    dataid1        = pd.DataFrame()
    dataid2        = pd.DataFrame()
    datatitular    = pd.DataFrame()
    
    if identificacion is not None and identificacion!='':
        identificacion = [re.sub('[^0-9]', '', str(x)) for x in identificacion.split(',') if len(re.sub('[^0-9]', '', str(x))) >= 6]
        if identificacion:
            query      = "','".join(identificacion)
            dataid1    = pd.read_sql_query(f"SELECT chip as prechip,matriculainmobiliaria as value,tipo as tipoDocumento,identificacion as nroIdentificacion,nombre as titular FROM {schema}.data_bogota_shd_2024 WHERE identificacion IN ('{query}')" , engine)
            query      = " OR ".join([f"identificacion LIKE '%{id}%'" for id in identificacion])
            dataid2    = pd.read_sql_query(f"SELECT chip as prechip,matriculainmobiliaria as value,tipo as tipoDocumento,identificacion as nroIdentificacion,nombre as titular FROM {schema}.data_bogota_shd_2024 WHERE {query}" , engine)
    if titular is not None and titular!='':
        titular = titular.split(',')
        query   = " OR ".join([
                    "(" + " AND ".join([
                        f"LOWER(nombre) LIKE '%{word}%'" 
                        for word in re.sub(r'\s+', ' ', unidecode(t).strip().lower()).split()
                    ]) + ")"
                    for t in titular
                ])
        datatitular = pd.read_sql_query(f"SELECT chip as prechip,matriculainmobiliaria as value,tipo as tipoDocumento,identificacion as nroIdentificacion,nombre as titular FROM {schema}.data_bogota_shd_2024 WHERE {query}" , engine) 
    data = pd.concat([dataid1,dataid2,datatitular])
    if not data.empty and 'tipoDocumento' in data and tipodocumento is not None and tipodocumento != '':
        data          = data.drop_duplicates()
        data          = data[data['tipoDocumento'].apply(lambda x: re.sub('[^a-zA-Z]','',x))==re.sub('[^a-zA-Z]','',tipodocumento)]
        query         = "','".join(data[data['prechip'].notnull()]['prechip'].astype(str).unique())
        query         = f" prechip IN ('{query}')"        
        datacatastro  = pd.read_sql_query(f"SELECT prechip,predirecc,prenbarrio,preaterre,preaconst,precdestin,precuso,barmanpre,latitud,longitud  FROM  {schema}.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            datacatastro = datacatastro.drop_duplicates(subset='prechip',keep='first')
            data         = data.merge(datacatastro,on='prechip',how='left',validate='m:1')

    if 'barmanpre' in data and data[data['barmanpre'].notnull()].empty is False:
        query    = "','".join(data[data['barmanpre'].notnull()]['barmanpre'].unique())
        query    = f" lotcodigo IN ('{query}')"        
        datalote = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  {schema}.data_bogota_lotes WHERE {query}" , engine)
        data     = data.merge(datalote,on='barmanpre',how='left',validate='m:1')
    return data