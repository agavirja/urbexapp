import streamlit as st
import pandas as pd
import re
from sqlalchemy import create_engine 
from datetime import datetime, timedelta

from data.coddir import coddir
from data.lastTransacciones import main as lastTransacciones

@st.cache_data(show_spinner=False)
def dataproyectosnuevos(polygon):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datalatlng    = pd.DataFrame()
    dataproyectos = pd.DataFrame()
    dataformulada = pd.DataFrame()
    datalong      = pd.DataFrame()
    
    query = ""
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
        
    if query!="":
        query = query.strip().strip('AND')
        datalatlng  = pd.read_sql_query(f"SELECT codproyecto,latitud,longitud FROM  bigdata.data_bogota_gi_nueva_latlng WHERE {query}" , engine)
        
    if not datalatlng.empty:
        lista = "','".join(datalatlng['codproyecto'].astype(str).unique())
        query = f" codproyecto IN ('{lista}')"
        dataproyectos  = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_proyectos WHERE {query}" , engine)
        if not dataproyectos.empty:
            datamerge     = datalatlng.drop_duplicates(subset='codproyecto',keep='first')
            dataproyectos = dataproyectos.merge(datamerge,on='codproyecto',how='left',validate='m:1')
            for i in ['estado','tipo','tipo_vivienda']:
                if i in dataproyectos: 
                    dataproyectos[i] = dataproyectos[i].apply(lambda x: formatovariables(x))
            dataproyectos['estado'] = dataproyectos['estado'].apply(lambda x: x.split(',')[-1])
            
        dataformulada = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_formulada WHERE {query}" , engine)
        datalong      = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_gi_nueva_long WHERE {query}" , engine)
    
    #-------------------------------------------------------------------------#
    # Merge direccion/barmanpre
    if not dataproyectos.empty:
        dataproyectos['coddir'] = dataproyectos['direccion'].apply(lambda x: coddir(x))
        
        lista = "','".join(dataproyectos['coddir'].astype(str).unique())
        query = f" coddir IN ('{lista}')"
        
        datacatastro = pd.read_sql_query(f"SELECT coddir,barmanpre FROM bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            datamerge     = datacatastro.drop_duplicates(subset='coddir',keep='first')
            dataproyectos = dataproyectos.merge(datamerge,on='coddir',how='left',validate='m:1')
        
        if 'barmanpre' in dataproyectos and sum(dataproyectos['barmanpre'].isnull())>0:
            lista         = []
            dataconjuntos = pd.DataFrame()
            for palabras in dataproyectos['proyecto'].unique():
                for palabra in palabras.split(' '):
                    if len(palabra) >= 3:
                        lista.append(palabra)
                        
            if lista!=[]:
                lista = [re.sub(r'\s+',' ',re.sub('[^a-zA-Z0-9]',' ',x)).strip() for x in lista if isinstance(x,str) and x!='']
                if isinstance(lista,list) and lista!=[]:
                    lista         = "','".join(lista)
                    query         = f" nombre_conjunto IN ('{lista}')"
                    dataconjuntos = pd.read_sql_query(f"SELECT coddir,nombre_conjunto as proyectonew FROM bigdata.bogota_nombre_conjuntos WHERE {query}" , engine)
                    if not dataconjuntos.empty:
                        lista        = "','".join(dataconjuntos['coddir'].astype(str).unique())
                        query        = f" coddir IN ('{lista}')"
                        datacatastro = pd.read_sql_query(f"SELECT coddir,barmanpre as barmanprenew FROM bigdata.data_bogota_catastro WHERE {query}" , engine)
                        if not datacatastro.empty:
                            datamerge     = datacatastro.drop_duplicates(subset='coddir',keep='first')
                            dataconjuntos = dataconjuntos.merge(datamerge,on='coddir',how='left',validate='m:1')
                            dataconjuntos = dataconjuntos[dataconjuntos['barmanprenew'].notnull()]
            if not dataconjuntos.empty and 'barmanprenew' in dataconjuntos:
                datamerge                    = dataconjuntos.drop_duplicates(subset='proyectonew',keep='first')
                datamerge['proyectonew']     = datamerge['proyectonew'].astype(str).str.lower()
                dataproyectos['proyectonew'] = dataproyectos['proyecto'].astype(str).str.lower()
                dataproyectos                = dataproyectos.merge(datamerge[['proyectonew','barmanprenew']],on='proyectonew',how='left',validate='m:1')
                if 'barmanprenew' in dataproyectos:
                    idd = (dataproyectos['barmanpre'].isnull()) & (dataproyectos['barmanprenew'].notnull())
                    if sum(idd)>0:
                        dataproyectos.loc[idd,'barmanpre'] = dataproyectos.loc[idd,'barmanprenew']
                variables = [x for x in ['barmanprenew','proyectonew'] if x in dataproyectos]
                if variables!=[]: dataproyectos.drop(columns=variables,inplace=True)

    datalong    = mergedata(dataformulada,datalong)
    datapricing = dataPricing(dataproyectos,dataformulada,datalong)
    
    if not datapricing.empty and 'areaconstruida' in datapricing:
        datapricing['valormt2'] = datapricing['valor_P']/datapricing['areaconstruida']
        
    return dataproyectos,dataformulada,datalong,datapricing
        
@st.cache_data(show_spinner=False)
def dataPricing(dataproyectos,dataformulada,datalongproyectos):
    df = pd.DataFrame()
    if not dataproyectos.empty and not dataformulada.empty and not datalongproyectos.empty:
        df                = dataformulada[['codproyecto','codinmueble']]
        df                = df.merge(dataproyectos[['codproyecto','estado','fecha_inicio','fecha_entrega']],how='left',validate='m:1')
        datalongproyectos = datalongproyectos.merge(df,on=['codinmueble','codproyecto'],how='left',validate='m:1')
        
        df            = datalongproyectos.copy()
        df            = df.sort_values(by=['codinmueble','ano','mes'],ascending=True)
        df['fecha']   = df.apply(lambda x: datetime(x['ano'],x['mes'],1) if (isinstance(x['ano'],float) or isinstance(x['ano'],int)) or (isinstance(x['mes'],float) or isinstance(x['mes'],int)) else None,axis=1)
    
        #-------------------------------------------------------------------------#
        # Fecha Inicial
        df = df[df['fecha']>=df['fecha_inicio']]
        
        #-------------------------------------------------------------------------#
        # Fecha final
        df['valor_F'] = None
        idd           = df['fecha']==df['fecha_entrega']
        df.loc[idd,'valor_F'] = 1
            
        dj = pd.DataFrame()
        for i in ['valor_D','valor_N','valor_F']:
            djpaso = df[df[i].notnull()]
            djpaso = djpaso.groupby(['codproyecto','codinmueble']).agg({'fecha':'max'}).reset_index()
            dj     = pd.concat([dj,djpaso])
            
        dj  = dj.groupby(['codproyecto','codinmueble']).agg({'fecha':'max'}).reset_index()
        dj.rename(columns={'fecha':'fecha_fin'},inplace=True)
        df  = df.merge(dj[['codproyecto','codinmueble','fecha_fin']],on=['codproyecto','codinmueble'],how='left',validate='m:1')
        df  = df[df['fecha']<=df['fecha_fin']]
        df.drop(columns=['fecha_fin','valor_F'],inplace=True)
     
        idd = df['estado'].isin(['Desist'])
        df  = df[~idd]
    return df

@st.cache_data(show_spinner=False)
def mergedata(dataformulada,datalongproyectos):
    if not dataformulada.empty and not datalongproyectos.empty:
        datamerge         = dataformulada[['codinmueble','codproyecto','areaconstruida','habitaciones','banos','garajes']]
        datamerge         = datamerge.drop_duplicates(subset=['codinmueble','codproyecto'],keep='first')
        datalongproyectos = datalongproyectos.merge(datamerge,on=['codinmueble','codproyecto'],how='left',validate='m:1')
        datalongproyectos['valormt2'] = datalongproyectos['valor_P']/datalongproyectos['areaconstruida']
        
        for i in ['ano','mes']:
            datalongproyectos[i] = pd.to_numeric(datalongproyectos[i],errors='coerce')
            datalongproyectos[i] = datalongproyectos[i].apply(lambda x: int(x) if isinstance(x, int) or isinstance(x, float) else None)
        
        datalongproyectos['fecha'] = None
        idd = (datalongproyectos['ano'].notnull()) & (datalongproyectos['mes'].notnull())
        if sum(idd)>0:
            datalongproyectos.loc[idd,'fecha'] = datalongproyectos[idd].apply(lambda x: datetime(x['ano'],x['mes'],1),axis=1)

    return datalongproyectos
        
def formatovariables(x):
    try:
        return ','.join([re.sub('[^a-zA-Z]','',w) for w in x.strip('/').split('/')])
    except: 
        return x
    
@st.cache_data(show_spinner=False)   
def datatransaccionesproyectos(inputvar):

    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    polygon  = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    usosuelo = inputvar['precuso'] if 'precuso' in inputvar and isinstance(inputvar['precuso'], list) else None

    query = ""
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
    if isinstance(usosuelo, list) and usosuelo!=[]:
        lista  = "','".join(usosuelo)
        query += f" AND precuso IN ('{lista}')"       
        
    if query!='':
        query        = query.strip().strip('AND')
        datausosuelo = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)

        if not datausosuelo.empty:
           barmanpre     = "','".join(datausosuelo['barmanpre'].unique())
           yearmax       = datetime.now().year-3
           query         = f" barmanpre IN ('{barmanpre}') AND prevetustz>={yearmax} "
           if isinstance(usosuelo, list) and usosuelo!=[]:
               lista  = "','".join(usosuelo)
               query += f" AND precuso IN ('{lista}')" 
           st.write(query)
           datacatastro = pd.read_sql_query(f"SELECT barmanpre,predirecc,prechip,preaconst,prevetustz FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)

        if not datacatastro.empty:
            chip   = list(datacatastro['prechip'].unique())
            data,_ = lastTransacciones(chip=chip)
            
            if not data.empty:
                st.dataframe(data)
                datamerge = datacatastro.drop_duplicates(subset='prechip',keep='first')
                data      = data.merge(datamerge,on='prechip',how='left',validate='m:1')
    engine.dispose()
    
    if not data.empty:
        data['fecha_documento_publico'] = pd.to_datetime(data['fecha_documento_publico'],errors='coerce')
        data['valormt2'] = None
        if 'cuantia' in data and 'preaconst' in data:
            data['valormt2'] = data['cuantia']/data['preaconst']

    return data
