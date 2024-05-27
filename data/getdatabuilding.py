import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from datetime import datetime

from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.getuso_destino import getuso_destino

from data.getdataTransactions import main as getdatatransactions
from data.getdatavigencia import main as getdatavigencia

@st.cache_data(show_spinner=False)
def main(barmanpre):
    
    #-----------------------#
    # Informacion Catastral #
    datacatastro,datausosuelo,datalote = _databuilding(barmanpre)

    #-----------------#
    # Informacion SHD #
    datavigencia  = pd.DataFrame()
    if not datacatastro.empty:
        chip = list(datacatastro['prechip'].unique())
        datavigencia  = getdatavigencia(chip)
    #-----------------#
    # Informacion SNR #
    datatransacciones = getdatatransactions(barmanpre,typesearch='barmanpre')
    
    return datacatastro,datausosuelo,datalote,datavigencia,datatransacciones
    

@st.cache_data(show_spinner=False)
def _databuilding(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    datacatastro = pd.DataFrame()
    datausosuelo = pd.DataFrame()
    datalote     = pd.DataFrame()
    
    if isinstance(barmanpre, str) and len(barmanpre)>10:
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst,latitud,longitud FROM  bigdata.data_bogota_catastro WHERE barmanpre='{barmanpre}'" , engine)
        datalote     = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE lotcodigo ='{barmanpre}'" , engine)
        
    elif isinstance(barmanpre, list) and barmanpre!=[]:
        lista        = "','".join(barmanpre)
        query        = f" barmanpre IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst,latitud,longitud FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        
        query        = f" lotcodigo IN ('{lista}')"
        datalote     = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        
    if not datacatastro.empty and not datalote.empty:
        datalote = datalote.drop_duplicates(subset='barmanpre',keep='first')
        datamerge = datacatastro.drop_duplicates(subset='barmanpre',keep='first')
        datalote  = datalote.merge(datamerge[['barmanpre','latitud','longitud']],on='barmanpre',how='left',validate='m:1')
        
    if not datacatastro.empty:
        lista = "','".join(datacatastro['barmanpre'].unique())
        query = f" barmanpre IN ('{lista}')"
        datausosuelo = pd.read_sql_query(f"SELECT barmanpre,precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst_total,preaterre_total,predios_total FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        datausosuelo = datausosuelo.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        datacatastro = datacatastro.merge(dataprecuso,on='precuso',how='left',validate='m:1')

        lista        = "','".join(datacatastro['barmanpre'].unique())
        query        = f" barmanpre IN ('{lista}')"
        datacompacta = pd.read_sql_query(f"SELECT barmanpre,prenbarrio,formato_direccion,prevetustzmin,prevetustzmax,estrato,connpisos,connsotano,construcciones,conelevaci FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)

        if not datacompacta.empty and not datausosuelo.empty:
            datacompacta = datacompacta.drop_duplicates(subset='barmanpre',keep='first')
            datausosuelo = datausosuelo.merge(datacompacta,on='barmanpre',how='left',validate='m:1')

    if not datacatastro.empty:
        lista  = "','".join(datacatastro['prechip'].unique())
        query  = f" chip IN ('{lista}')"
        datamatricula = pd.read_sql_query(f"SELECT chip as prechip,matriculainmobiliaria FROM bigdata.data_bogota_shd_objetocontrato WHERE {query}" , engine)
        
        if not datamatricula.empty:
            datamerge = datamatricula[datamatricula['matriculainmobiliaria'].notnull()]
            datamerge = datamatricula.drop_duplicates(subset='prechip',keep='first')
            datacatastro = datacatastro.merge(datamerge,on='prechip',how='left',validate='m:1')

    engine.dispose()
    return datacatastro,datausosuelo,datalote
