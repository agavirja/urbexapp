import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from datetime import datetime

from data.inmuebleANDusosuelo import inmueble2usosuelo,usosuelo2inmueble
from data.getuso_destino import getuso_destino

from data.getdataTransactions import main as getdatatransactions
from data.getdatavigencia import main as getdatavigencia


@st.cache_data(show_spinner=False)
def main(inputvar):
        
    #-----------------------#
    # Informacion Catastral #
    datacatastro,datalotes = _datalotespolygon(inputvar)

    #-----------------#
    # Informacion SNR #
    datatransacciones = getdatatransactions(code=None,typesearch=None,datamatricula=datacatastro)
    
    if not datacatastro.empty and not datatransacciones.empty:
        datamerge  = datacatastro.drop_duplicates(subset='prechip',keep='first')
        if 'barmanpre' not in datatransacciones: 
            datatransacciones = datatransacciones.merge(datamerge[['prechip','barmanpre']],on='prechip',how='left',validate='m:1')
        
    #-------------#
    # Data market #
    datamarket = MarketActivos(inputvar)
    return datacatastro,datalotes,datatransacciones,datamarket
    

@st.cache_data(show_spinner=False)
def _datalotespolygon(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datacatastro = pd.DataFrame()
    datalotes    = pd.DataFrame()
    
    polygon  = inputvar['polygon']  if 'polygon' in  inputvar and isinstance(inputvar['polygon'], str) else None
    latitud  = inputvar['latitud']  if 'latitud' in  inputvar and ( isinstance(inputvar['latitud'], float) or isinstance(inputvar['latitud'], int)) else None
    longitud = inputvar['longitud'] if 'longitud' in inputvar and ( isinstance(inputvar['longitud'], float) or isinstance(inputvar['longitud'], int)) else None

    #-------------------------------------------------------------------------#
    # Data lotes
    query    = ''
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
        
    if query!='':
        query        = query.strip().strip('AND')
        datacompacta = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)

    if not datacompacta.empty:
        query = "','".join(datacompacta['barmanpre'].unique())
        query = f" barmanpre IN ('{query}')" 
        
        addvar = ''
        if longitud is not None and longitud is not None:
            addvar = f""", ST_Distance_Sphere(geometry, Point({longitud},{latitud})) AS distance"""
        datacatastro = pd.read_sql_query(f"SELECT distinct(barmanpre) as barmanpre {addvar}  FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
        
        if not datacatastro.empty:
            query = "','".join(datacatastro['barmanpre'].unique())
            query = f" lotcodigo IN ('{query}')" 
            datalotes  = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
            
            if 'distance' in datacatastro: 
                datamerge = datacatastro.sort_values(by=['barmanpre','distance'],ascending=True).drop_duplicates(subset='barmanpre',keep='first')
                datalotes = datalotes.merge(datamerge[['barmanpre','distance']],on='barmanpre',how='left',validate='m:1')

    #-------------------------------------------------------------------------#
    # Data catastro
    if not datalotes.empty:
        query        = "','".join(datacompacta['barmanpre'].unique())
        query        = f" barmanpre IN ('{query}')" 
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,predirecc,preaterre,preaconst FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
        
    if not datacatastro.empty:
        lista = "','".join(datacatastro['barmanpre'].unique())
        query = f" barmanpre IN ('{lista}')"

        datacompacta = pd.read_sql_query(f"SELECT barmanpre,prenbarrio,formato_direccion,prevetustzmin,prevetustzmax,estrato,connpisos,connsotano,construcciones,preaconst as preaconst_total,preaterre as preaterre_total FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)
        if not datacompacta.empty:
            datamerge    = datacompacta.drop_duplicates(subset='barmanpre',keep='first')
            datacatastro = datacatastro.merge(datamerge,on='barmanpre',how='left',validate='m:1')
            
            if not datalotes.empty:
                datalotes = datalotes.merge(datamerge,on='barmanpre',how='left',validate='m:1')

            
        if 'precuso' in datacatastro: 
            dataprecuso,dataprecdestin = getuso_destino()
            dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
            datacatastro = datacatastro.merge(dataprecuso,on='precuso',how='left',validate='m:1')

        lista  = "','".join(datacatastro['prechip'].unique())
        query  = f" chip IN ('{lista}')"
        datamatricula = pd.read_sql_query(f"SELECT chip as prechip,matriculainmobiliaria FROM bigdata.data_bogota_shd_objetocontrato WHERE {query}" , engine)
        
        if not datamatricula.empty:
            datamerge    = datamatricula[datamatricula['matriculainmobiliaria'].notnull()]
            datamerge    = datamatricula.drop_duplicates(subset='prechip',keep='first')
            datacatastro = datacatastro.merge(datamerge,on='prechip',how='left',validate='m:1')

    engine.dispose()
    return datacatastro,datalotes

@st.cache_data(show_spinner=False)
def MarketActivos(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datamarket = pd.DataFrame()
    precuso    = inputvar['precuso'] if 'precuso' in inputvar and isinstance(inputvar['precuso'], list) else None
    polygon    = inputvar['polygon'] if 'polygon' in  inputvar and isinstance(inputvar['polygon'], str) else None
    latitud    = inputvar['latitud']  if 'latitud' in  inputvar and ( isinstance(inputvar['latitud'], float) or isinstance(inputvar['latitud'], int)) else None
    longitud   = inputvar['longitud'] if 'longitud' in inputvar and ( isinstance(inputvar['longitud'], float) or isinstance(inputvar['longitud'], int)) else None

    query      = ""
    if precuso is not None:
        tipoinmueble = usosuelo2inmueble(precuso)
        tipoinmueble = "','".join(tipoinmueble)
        query       += f' AND tipoinmueble IN ("{tipoinmueble}")'
    
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), geometry)'

    addvar = ''
    if longitud is not None and longitud is not None:
        addvar = f""", ST_Distance_Sphere(geometry, Point({longitud},{latitud})) AS distance"""

    if query!="":
        query = query.strip().strip('AND').strip()
        datamarket  = pd.read_sql_query(f"SELECT valor,areaconstruida,tiponegocio,tipoinmueble,latitud,longitud,direccion,inmobiliaria,url,habitaciones,banos,garajes,fecha_inicial {addvar} FROM bigdata.market_portales_activos WHERE {query}" , engine)
        if not datamarket.empty:
            datamarket['valormt2'] = datamarket['valor']/datamarket['areaconstruida']
            
    return datamarket
