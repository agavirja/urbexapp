import streamlit as st
import re
import json
import pandas as pd
from unidecode import unidecode
from sqlalchemy import create_engine 
from datetime import datetime

from data.getuso_destino import getuso_destino
from data.lastTransacciones import main as lastTransacciones,getEXACTfecha

@st.cache_data(show_spinner=False)
def main(inputvar):

    datasnr = getSNRbyID(inputvar)
    datashd = getSHDbyID(inputvar)
    
    if datasnr.empty:
        datasnr = pd.DataFrame(columns=['prechip'])
    if datashd.empty:
        datashd = pd.DataFrame(columns=['prechip'])
        
    #-------------------------------------------------------------------------#
    # Ultima vigencia en datashd
    #-------------------------------------------------------------------------#
    if not datasnr.empty and not datashd.empty:
        datamerge         = datashd.groupby('prechip')['vigencia'].max().reset_index()
        datamerge.columns = ['prechip','maxvigencia']
        datasnr           = datasnr.merge(datamerge,on='prechip',how='left',validate='m:1')
    
    #-------------------------------------------------------------------------#
    # Completar la informacion de shd
    #-------------------------------------------------------------------------#
    if not datashd.empty:
        idd = datashd['prechip'].isin(datasnr['prechip'])
        if sum(~idd)>0:
            datamerge = datashd[~idd]
            datamerge.rename(columns={'vigencia':'maxvigencia'},inplace=True)
            datasnr   = pd.concat([datasnr,datamerge])
            
    #-------------------------------------------------------------------------#
    # Inmuebles activos
    #-------------------------------------------------------------------------#
    listachips = list(datasnr['prechip'].unique())
    datasnr_last_transactions,datasnr_last_transactions_id  = [pd.DataFrame()]*2
    if isinstance(listachips,list) and listachips!=[]:
        identificacion            = inputvar['identificacion'] if 'identificacion' in inputvar and inputvar['identificacion'] is not None and inputvar['identificacion'] != '' else None
        datasnr_last_transactions,datasnr_last_transactions_id = lastTransacciones(chip=listachips,identificacion=identificacion)
        
    if not datasnr.empty and not datasnr_last_transactions_id.empty:
        idd = datasnr_last_transactions_id['docid'].isin(datasnr['docid'])
        if sum(~idd)>0:
            datamerge = datasnr_last_transactions_id[~idd]
            if not datamerge.empty:
                variables = [x for x in list(datamerge) if x in list(datasnr)]
                datamerge = datamerge[variables]
                datasnr   = pd.concat([datasnr,datamerge])
        
        datamerge           = datasnr_last_transactions_id[['docid']]
        datamerge           = datamerge.drop_duplicates(subset='docid',keep='first')
        datamerge['active'] = 1
        datasnr             = datasnr.merge(datamerge,on='docid',how='left',validate='m:1')
        idd                 = datasnr['active'].isnull()
        datasnr.loc[idd,'active'] = 0
        
    if not datasnr.empty and 'active' not in datasnr and 'maxvigencia' in datasnr:
        datasnr = datasnr.sort_values(by='maxvigencia',ascending=False).drop_duplicates(subset='prechip',keep='first')
        datasnr['active'] = 0
        idd     = datasnr['maxvigencia']==datetime.now().year
        datasnr.loc[idd,'active'] = 1
    
    #-------------------------------------------------------------------------#
    # Completar informacion
    #-------------------------------------------------------------------------#
    datacompeltar = completeInfo(listachips)

    if not datacompeltar.empty:
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        dataprecdestin.rename(columns={'codigo':'precdestin','tipo':'actividad','descripcion':'desc_actividad'},inplace=True)
        datacompeltar = datacompeltar.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        datacompeltar = datacompeltar.merge(dataprecdestin,on='precdestin',how='left',validate='m:1')

    if not datacompeltar.empty:
        datamerge = datacompeltar.drop_duplicates(subset='prechip',keep='first')
        datasnr   = datasnr.merge(datamerge,on='prechip',how='left',validate='m:1')

        # Chip a matricula
        datasnr = chip2matricula(datasnr)
    
    if not datasnr.empty and 'fecha_documento_publico' in datasnr and 'maxvigencia' in datasnr:
        idd = datasnr['maxvigencia'].isnull()
        datasnr.loc[idd,'maxvigencia'] = 0
        
        datasnr['year'] = pd.to_datetime(datasnr['fecha_documento_publico'])
        datasnr['year'] = datasnr['year'].apply( lambda x: x.year)
        idd             = datasnr['year'].isnull()
        datasnr.loc[idd,'year'] = 0
        datasnr['year'] = datasnr.apply( lambda x: max(x['year'],x['maxvigencia']),axis=1)
        
    if not datasnr.empty and 'year' not in datasnr and 'maxvigencia' in datasnr: 
        datasnr.rename(columns={'maxvigencia':'year'},inplace=True)
        
    variables = [x for x in ['docid', 'value', 'maxvigencia'] if x in datasnr]
    if variables!=[]: datasnr.drop(columns=variables,inplace=True)

    #-------------------------------------------------------------------------#
    # Avaluos catastrales y prediales
    #-------------------------------------------------------------------------#
    if not datasnr.empty and 'prechip' in datasnr:
        chip      = list(datasnr['prechip'].unique())
        datavaluo = completeInfoAvaluo(chip)
        if not datavaluo.empty:
            datamerge = datavaluo.groupby('prechip').agg({'avaluo_catastral':'max','impuesto_ajustado':'max'}).reset_index()
            datamerge.columns = ['prechip','avaluo_catastral','impuesto_ajustado']
            datasnr = datasnr.merge(datamerge,on='prechip',how='left',validate='m:1')
            
    return datasnr
    

@st.cache_data(show_spinner=False)
def getSNRbyID(inputvar):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    identificacion = inputvar['identificacion'] if 'identificacion' in inputvar and inputvar['identificacion'] is not None and inputvar['identificacion'] != '' else None
    dataid1        = pd.DataFrame()
    dataid2        = pd.DataFrame()

    if isinstance(identificacion,str) and identificacion!='':
        identificacion = [re.sub('[^0-9]', '', str(x)) for x in identificacion.split(',') if len(re.sub('[^0-9]', '', str(x))) >= 6]
        if isinstance(identificacion,list) and identificacion!=[]:
            query      = "','".join(identificacion)
            dataid1    = pd.read_sql_query(f"SELECT * FROM {schema}.snr_id2docid WHERE nroIdentificacion IN ('{query}')" , engine)
            query      = " OR ".join([f"nroIdentificacion LIKE '%{id}%'" for id in identificacion])
            dataid2    = pd.read_sql_query(f"SELECT * FROM {schema}.snr_id2docid WHERE {query}" , engine)
   
    data = pd.concat([dataid1,dataid2])
    
    if not data.empty:
        data        = data.drop_duplicates()
        query       = "','".join(data[data['docid'].notnull()]['docid'].astype(str).unique())
        query       = f" docid IN ('{query}')"  
        datamerge   = pd.read_sql_query(f"SELECT docid,entidad,fecha_documento_publico,documento_json  FROM  {schema}.snr_data_completa WHERE {query}" , engine)         
        if not datamerge.empty:
            datamerge   = datamerge.drop_duplicates(subset='docid',keep='first')
            data        = data.merge(datamerge,on='docid',how='left',validate='m:1')
        
            if 'documento_json' in data:
                data['fechanotnull'] = data['documento_json'].apply(lambda x: getEXACTfecha(x))
                formato_fecha = '%d-%m-%Y'
                data['fechanotnull'] = pd.to_datetime(data['fechanotnull'],format=formato_fecha,errors='coerce')
    
                idd = (data['fecha_documento_publico'].isnull()) & (data['fechanotnull'].notnull())
                if sum(idd)>0:
                    data.loc[idd,'fecha_documento_publico'] = data.loc[idd,'fechanotnull']
                idd = (data['fecha_documento_publico'].isnull()) & (data['fecha'].notnull())
                if sum(idd)>0:
                    data.loc[idd,'fecha_documento_publico'] = data.loc[idd,'fecha']
                data.drop(columns=['fechanotnull','documento_json','fecha'],inplace=True)

    databogota = pd.DataFrame()
    if not data.empty and 'oficina' in data:
        idd        = (data['oficina'].astype(str).str.lower().str.contains('bogota')) & (data['entidad'].astype(str).str.lower().str.contains('bogota'))
        databogota = data[idd]
        data       = data[~idd]
        
    if not databogota.empty:
        if 'docid' in databogota and databogota[databogota['docid'].notnull()].empty is False:
            query         = "','".join(databogota[databogota['docid'].notnull()]['docid'].astype(str).unique())
            query         = f" docid IN ('{query}')"        
            datamatricula = pd.read_sql_query(f"SELECT docid,value FROM  {schema}.snr_data_matricula WHERE {query}" , engine)
            databogota    = datamatricula.merge(databogota,on='docid',how='left',validate='m:1')    
            
        if 'value' in databogota and databogota[databogota['value'].notnull()].empty is False:
            lista         = list(databogota[databogota['value'].notnull()]['value'].astype(str).unique())
            lnew1         = [x.lstrip('0') for x in lista]
            lnew2         = [f'0{x}' for x in lista]
            lista         = lista+lnew1+lnew2
            lista         = list(set(lista))
            query         = "','".join(lista)
            query         = f" numeroMatriculaInmobiliaria IN ('{query}')"
            datachip      = pd.read_sql_query(f"SELECT numeroMatriculaInmobiliaria as value,numeroChip as prechip FROM  {schema}.data_bogota_catastro_predio WHERE {query}" , engine)
        
            if not datachip.empty:
                query     = "','".join(datachip['prechip'].unique())
                query     = f" chip IN ('{query}')"
                datamerge = pd.read_sql_query(f"SELECT matriculainmobiliaria as matricula,chip as prechip FROM  {schema}.data_bogota_shd_objetocontrato WHERE {query}" , engine)
                if not datamerge.empty:
                    datamerge = datamerge.drop_duplicates(subset='prechip',keep='first')
                    datamerge['numoficina'] = None
                    for j in ['50N','50C','50S']:
                        idd = datamerge['matricula'].astype(str).str.contains(j)
                        if sum(idd)>0:
                            datamerge.loc[idd,'numoficina'] = j
                    datachip  = datachip.merge(datamerge,on='prechip',how='left',validate='m:1')
            
            if not datachip.empty:
                datamerge  = datachip.drop_duplicates(subset='value',keep='first')
                databogota = databogota.merge(datamerge,on='value',how='left',validate='m:1')
                databogota = databogota[databogota['prechip'].notnull()]
                databogota['oficina2code'] = databogota['oficina'].replace(['bogota zona norte','bogota zona centro','bogota zona sur'],['50N','50C','50S'])
                databogota = databogota[databogota['oficina2code']==databogota['numoficina']]

    engine.dispose()
    
    data      = pd.concat([databogota,data])
    variables = [x for x in ['numoficina','oficina2code','fecha','email','variable','id','fechanotnull'] if x in data]
    if variables!=[]: data.drop(columns=variables,inplace=True)

    return data
    
@st.cache_data(show_spinner=False)
def getSHDbyID(inputvar):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    #-------------------------------------------------------------------------#
    # Data prediales Bogota
    identificacion = inputvar['identificacion'] if 'identificacion' in inputvar and inputvar['identificacion'] is not None and inputvar['identificacion'] != '' else None
    data           = pd.DataFrame()
    
    if isinstance(identificacion,str) and identificacion!='':
        identificacion = [re.sub('[^0-9]', '', str(x)) for x in identificacion.split(',') if len(re.sub('[^0-9]', '', str(x))) >= 6]
        if isinstance(identificacion,list) and identificacion!=[]:
            #-----------------------------------------------------------------#
            # Vigencia: 2024
            query    = "','".join(identificacion)
            dataid1  = pd.read_sql_query(f"SELECT chip as prechip,identificacion as nroIdentificacion FROM {schema}.data_bogota_shd_2024 WHERE identificacion IN ('{query}')" , engine)
            query    = " OR ".join([f"identificacion LIKE '%{id}%'" for id in identificacion])
            dataid2  = pd.read_sql_query(f"SELECT chip as prechip,identificacion as nroIdentificacion  FROM {schema}.data_bogota_shd_2024 WHERE {query}" , engine)
            data2024 = pd.concat([dataid1,dataid2])
            if not data2024.empty: 
                data2024 = data2024.drop_duplicates()
                data2024['vigencia'] = 2024 
            
            #-----------------------------------------------------------------#
            # Vigencia: Antes-2022
            query          = "','".join(identificacion)
            dataid1        = pd.read_sql_query(f"SELECT chip as prechip, nroIdentificacion, vigencia  FROM {schema}.data_bogota_catastro_vigencia WHERE nroIdentificacion IN ('{query}')" , engine)
            dataid2        = pd.DataFrame()
            identificacion = [x[:-1] for x in identificacion if isinstance(x,str)]
            if isinstance(identificacion,list) and identificacion!=[]:
                query   = "','".join(identificacion)
                dataid2 = pd.read_sql_query(f"SELECT chip as prechip, nroIdentificacion, vigencia  FROM {schema}.data_bogota_catastro_vigencia WHERE nroIdentificacion IN ('{query}')" , engine)

            datavigencia = pd.concat([dataid1,dataid2])
            data         = pd.concat([data2024,datavigencia])
    engine.dispose()
    
    if not data.empty:
        data = data.drop_duplicates()
        
    return data
        
@st.cache_data(show_spinner=False)
def completeInfo(chip):
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data        = pd.DataFrame()
    
    if isinstance(chip,list) and chip!=[]:
        chip = [x for x in chip if not pd.isna(x)]
        
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    if isinstance(chip,list) and chip!=[]:
        query = "','".join(chip)
        query = f" prechip IN ('{query}')"        
        data  = pd.read_sql_query(f"SELECT prechip,predirecc,prenbarrio,preaterre,preaconst,precdestin,precuso,barmanpre,latitud,longitud,prevetustz  FROM  {schema}.data_bogota_catastro WHERE {query}" , engine)

        if not data.empty:
            query      = "','".join(data['barmanpre'].unique())
            query      = f" lotcodigo IN ('{query}')"        
            datalote   = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  {schema}.data_bogota_lotes WHERE {query}" , engine)
            
            if not datalote.empty:
                datamerge = datalote.drop_duplicates(subset='barmanpre',keep='first')
                data      = data.merge(datamerge,on='barmanpre',how='left',validate='m:1')
    engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def completeInfoAvaluo(chip):
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data        = pd.DataFrame()
    
    if isinstance(chip,list) and chip!=[]:
        chip = [x for x in chip if not pd.isna(x)]   
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    if isinstance(chip,list) and chip!=[]:
        query = "','".join(chip)
        query = f" chip IN ('{query}')"        
        data  = pd.read_sql_query(f"SELECT chip as prechip,avaluo_catastral,impuesto_ajustado  FROM  {schema}.data_bogota_shd_2024 WHERE {query}" , engine)
    engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def chip2matricula(data):
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    if 'matricula' not in data: data['matricula'] = None
    df = data[data['matricula'].isnull()]
    if not df.empty:
        chip = [x for x in df['prechip'].unique() if not pd.isna(x)]   
        if isinstance(chip,list) and chip!=[]:
            query         = "','".join(chip)
            query         = f" chip IN ('{query}')"
            datamatricula = pd.read_sql_query(f"SELECT matriculainmobiliaria as matricula_new,chip as prechip FROM  {schema}.data_bogota_shd_objetocontrato WHERE {query}" , engine)
            if not datamatricula.empty:
                datamerge = datamatricula.drop_duplicates(subset='prechip',keep='first')
                data      = data.merge(datamerge,on='prechip',how='left',validate='m:1')
                idd       = (data['matricula'].isnull()) & (data['matricula_new'].notnull())
                if sum(idd)>0:
                    data.loc[idd,'matricula'] = data.loc[idd,'matricula_new']
                data.drop(columns=['matricula_new'],inplace=True)
    engine.dispose()
    return data
