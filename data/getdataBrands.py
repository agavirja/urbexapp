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
    dataoptions = pd.read_sql_query("SELECT distinct(idxlabel) as idxlabel, label FROM  bigdata.brand_data" , engine)
    engine.dispose()
    return dataoptions


@st.cache_data(show_spinner=False)
def getdatabrans(inputvar):
    
    mpio_ccdgo = inputvar['mpio_ccdgo']
    idxlabel   = inputvar['idxlabel']
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query(f"SELECT * FROM  bigdata.brand_data WHERE idxlabel='{idxlabel}' AND mpio_ccdgo='{mpio_ccdgo}' " , engine)

    if not data.empty:
        query     = "','".join(data[data['lotcodigo'].notnull()]['lotcodigo'].unique())
        query     = f" lotcodigo IN ('{query}')"        
        datalotes = pd.read_sql_query(f"SELECT lotcodigo, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        
        # Remover vias
        query               = "','".join(datalotes['lotcodigo'].unique())
        query               = f" barmanpre IN ('{query}')"          
        datacatastro_novias = pd.read_sql_query(f"SELECT  barmanpre as lotcodigo  FROM  bigdata.data_bogota_catastro WHERE precdestin IN ('65','66') AND {query}" , engine)
        idd          = datalotes['lotcodigo'].isin(datacatastro_novias['lotcodigo'])
        if sum(idd)>0:
            datalotes = datalotes[~idd]

        datamerge = datalotes.drop_duplicates(subset='lotcodigo',keep='first')
        datamerge['ind'] = 1
        data      = data.merge(datamerge,on='lotcodigo',how='left',validate='m:1')
        data      = data[data['ind']==1]
        data.drop(columns=['ind'],inplace=True)

    engine.dispose()
    return data
