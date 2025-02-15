import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 
from geopy.distance import geodesic

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


@st.cache_data(show_spinner=False)
def getallcountrybrands(idxlabel=None):
    
    # idxlabel = 'estacion_servicio'
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.DataFrame()
    query    = ""
    if isinstance(idxlabel,str) and idxlabel!='':
        idxlabel = idxlabel.split('|')
    
    if isinstance(idxlabel,list) and idxlabel!=[]:
        lista = "','".join(list(set(idxlabel)))
        query = f" idxlabel IN ('{lista}')"
        data  = pd.read_sql_query(f"SELECT id,nombre,direccion,empresa,lotcodigo as barmanpre,predirecc,marker,marker_color,radio,latitud,longitud,prenbarrio,dpto_ccdgo,dpto_cnmbr,mpio_cnmbr,mpio_ccdgo FROM  bigdata.brand_data WHERE {query} " , engine)

    if not data.empty:
        data = data[data['dpto_ccdgo'].notnull()]
        
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
        data      = data.merge(datamerge,on='barmanpre',how='left',validate='m:1')
     
    engine.dispose()
        
    return data


@st.cache_data(show_spinner=False)
def getdatabyid(codigo=None):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data      = pd.DataFrame()
    dataradio = pd.DataFrame()
    query    = ""
    
    
    if isinstance(codigo,str) and codigo!='':
        codigo = codigo.split('|')
    elif isinstance(codigo,(float,int)) and codigo>=0:
        codigo = [f'{codigo}']
    
    if isinstance(codigo,list) and codigo!=[]:
        lista = "','".join(list(set(codigo)))
        query = f" id IN ('{lista}')"
        dataradio = pd.read_sql_query(f"SELECT * FROM  bigdata.brand_data WHERE {query} " , engine)
        if not dataradio.empty:
            variable     = 'radio'
            df           = dataradio[dataradio[variable].notnull()]
            df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df           = df[df[variable].notnull()]
            df           = df.explode(variable)
            df           = df.apply(lambda x: {**(x[variable])}, axis=1)
            df           = pd.DataFrame(df)
            df.columns   = ['formato']
            df           = pd.json_normalize(df['formato'])
            data         = df.copy()

    if not data.empty:
        data = data[data['dpto_ccdgo'].notnull()]
        
    engine.dispose()
        
   
    if not data.empty and not dataradio.empty:
        data = pd.concat([dataradio,data])
            
    # Distancia
    if not data.empty and not dataradio.empty:
        latref = dataradio['latitud'].iloc[0] if 'latitud' in dataradio else None
        lonref = dataradio['longitud'].iloc[0] if 'longitud' in dataradio else None
        if latref is not None and  lonref is not None:
            data['distancia'] = data.apply(lambda x: calcular_distancia(x['latitud'], x['longitud'], latref, lonref), axis=1)
            
    if not data.empty:
        data = data.drop_duplicates(subset=['nombre','direccion','empresa','latitud','longitud','label'])
        
    if 'distancia' not in data:
        data['distancia'] = None
        
    if 'barmanpre' not in data and 'lotcodigo' in data: 
        data['barmanpre'] = data['lotcodigo'].copy()
    
    return data,dataradio

def calcular_distancia(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters