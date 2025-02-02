import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

from data.getuso_destino import getuso_destino

from data.getdataTransactions import main as getdatatransactions
from data.getdatavigencia import main as getdatavigencia
from data.getdataCTL import main as getdatactl

@st.cache_data(show_spinner=False)
def main(barmanpre,chip=None):
    
    #-----------------------------------------#
    # Si se tiene infomarcion del chip o chips#
    if isinstance(chip,str) and chip!="":
        chip = chip.split('|')
    if isinstance(chip,list):
        barmanpre_add = chip2barmanpre(chip)
        if isinstance(barmanpre_add,list) and barmanpre_add!=[]:
            if barmanpre is None or (isinstance(barmanpre,str) and barmanpre==''):
                barmanpre = []
            if isinstance(barmanpre,str):
                barmanpre = barmanpre.split('|')
            if isinstance(barmanpre,list): 
                barmanpre = barmanpre+barmanpre_add
                barmanpre = list(set(barmanpre))

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
    
    #-----------------#
    # CTL             #
    datactl = getdatactl(datacatastro)
    
    return datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl
    

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
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst,prevetustz,latitud,longitud FROM  bigdata.data_bogota_catastro WHERE barmanpre='{barmanpre}'" , engine)
        datalote     = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE lotcodigo ='{barmanpre}'" , engine)
        
    elif isinstance(barmanpre, list) and barmanpre!=[]:
        lista        = "','".join(barmanpre)
        query        = f" barmanpre IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst,prevetustz,latitud,longitud FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        
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

@st.cache_data(show_spinner=False)
def chip2barmanpre(chip):
    user      = st.secrets["user_bigdata"]
    password  = st.secrets["password_bigdata"]
    host      = st.secrets["host_bigdata_lectura"]
    schema    = st.secrets["schema_bigdata"]
    engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    barmanpre = []
    if isinstance(chip, list) and chip!=[]:
        lista        = "','".join(chip)
        query        = f" prechip IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT distinct(barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            barmanpre = list(datacatastro['barmanpre'].unique())
    engine.dispose()
    return barmanpre

@st.cache_data(show_spinner=False)
def chip2codigolote_sinupot(chip):
    user       = st.secrets["user_bigdata"]
    password   = st.secrets["password_bigdata"]
    host       = st.secrets["host_bigdata_lectura"]
    schema     = st.secrets["schema_bigdata"]
    engine     = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    codigolote = None
    if isinstance(chip, str) and chip!='':
        datacatastro = pd.read_sql_query(f"SELECT precbarrio,precmanz,precpredio FROM  bigdata.data_bogota_catastro WHERE prechip='{chip}'" , engine)
        if not datacatastro.empty:
            codigolote = f"{datacatastro['precbarrio'].iloc[0]}{datacatastro['precmanz'].iloc[0]}{datacatastro['precpredio'].iloc[0]}"

    if isinstance(chip, list) and chip!=[]:
        lista        = "','".join(chip)
        query        = f" prechip IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT precbarrio,precmanz,precpredio FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            datacatastro['codigo'] = datacatastro.apply(lambda x: f"{x['precbarrio']}{x['precmanz']}{x['precpredio']}",axis=1)
            codigolote             = list(datacatastro['codigo'].unique())
    engine.dispose()
    return codigolote
