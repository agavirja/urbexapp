import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def getoptions():
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    dataoptions = pd.read_sql_query("SELECT distinct(empresa) as empresa, idxlabel, label FROM  bigdata.brand_data" , engine)
    engine.dispose()
    return dataoptions


@st.cache_data(show_spinner=False)
def getdatabrans(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.DataFrame()
    query    = ""
    if isinstance(inputvar,list) and inputvar!=[]:
        dfquery = pd.DataFrame(inputvar)
    
        if not dfquery.empty:
            if 'idxlabel' in dfquery:
                df    = dfquery[dfquery['idxlabel'].notnull()]
                lista = "','".join(df['idxlabel'].unique())
                query += f" AND idxlabel IN ('{lista}')"
            if 'empresa' in dfquery:
                df    = dfquery[dfquery['empresa'].notnull()]
                lista = "','".join(df['empresa'].unique())
                query += f" AND empresa IN ('{lista}')"
            if 'mpio_ccdgo' in dfquery:
                df    = dfquery[dfquery['mpio_ccdgo'].notnull()]
                lista = "','".join(df['mpio_ccdgo'].unique())
                query += f" AND mpio_ccdgo IN ('{lista}')"
                
    if isinstance(query,str) and query!='':
        query = query.strip().strip('AND')
        data  = pd.read_sql_query(f"SELECT nombre,direccion,empresa,lotcodigo as barmanpre,predirecc,marker,marker_color FROM  bigdata.brand_data WHERE {query} " , engine)

    if not data.empty:
        query     = "','".join(data[data['barmanpre'].notnull()]['barmanpre'].unique())
        query     = f" lotcodigo IN ('{query}')"        
        datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        
        # Remover vias
        query               = "','".join(datalotes['barmanpre'].unique())
        query               = f" barmanpre IN ('{query}')"          
        datacatastro_novias = pd.read_sql_query(f"SELECT  barmanpre  FROM  bigdata.data_bogota_catastro WHERE precdestin IN ('65','66') AND {query}" , engine)
        idd          = datalotes['barmanpre'].isin(datacatastro_novias['barmanpre'])
        if sum(idd)>0:
            datalotes = datalotes[~idd]

        datamerge = datalotes.drop_duplicates(subset='barmanpre',keep='first')
        datamerge['ind'] = 1
        data      = data.merge(datamerge,on='barmanpre',how='left',validate='m:1')
        data      = data[data['ind']==1]
        data.drop(columns=['ind'],inplace=True)
        
        if not data.empty and 'barmanpre' in data:
            barmanpre    = list(data['barmanpre'].unique())
            datacompleta = completeInfo(barmanpre)
            if not datacompleta.empty:
                datamerge = datacompleta.drop_duplicates(subset='barmanpre',keep='first')
                data      = data.merge(datamerge,on='barmanpre',how='left',validate='m:1')
                
    engine.dispose()
        
    return data


@st.cache_data(show_spinner=False)
def completeInfo(barmanpre):
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data        = pd.DataFrame()
    
    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    if isinstance(barmanpre,list) and barmanpre!=[]:
        query = "','".join(barmanpre)
        query = f" barmanpre IN ('{query}')"        
        data  = pd.read_sql_query(f"SELECT barmanpre,prenbarrio,latitud,longitud  FROM  {schema}.data_bogota_catastro WHERE {query}" , engine)
    engine.dispose()
    return data
