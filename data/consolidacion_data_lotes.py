import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine 
from shapely.ops import unary_union

from data.getuso_destino import getuso_destino

@st.cache_data(show_spinner=False)
def main(barmanpre):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    data      = pd.DataFrame()
    datauso   = pd.DataFrame()
    datalote  = pd.DataFrame()
    num_lotes = None
    if isinstance(barmanpre, list) and barmanpre!=[]:
        lista   = "','".join(barmanpre)
        query   = f" barmanpre IN ('{lista}')"
        data    = pd.read_sql_query(f"SELECT barmanpre,formato_direccion,preaconst,preaterre,prevetustzmin,prevetustzmax,estrato,predios,connpisos,connsotano,construcciones  FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)
        datauso = pd.read_sql_query(f"SELECT barmanpre,precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst_total,preaterre_total,predios_total FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)

        lista    = "','".join(barmanpre)
        query    = f" lotcodigo IN ('{lista}')"
        datalote = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        num_lotes = len(barmanpre)
    try:
        datapaso             = datalote.copy()
        datapaso['geometry'] = gpd.GeoSeries.from_wkt(datapaso['wkt'])
        datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
        polygon              = unary_union(datapaso['geometry'].to_list())
        polygon              = polygon.wkt
    except:  polygon = None
    
    if not data.empty:
        data['idmerge'] = 1
        data            = data.groupby('idmerge').agg({'preaconst':'sum','preaterre':'sum','predios':'sum','connpisos':'max','connsotano':'max','construcciones':'sum','prevetustzmin':'min','prevetustzmax':'max','estrato':'max'}).reset_index()
        data.columns    = ['idmerge','preaconst','preaterre','predios','pisos','sotanos','construcciones','vetustezmin','vetustezmax','estrato']
        data['num_lotes'] = num_lotes
        data['wkt']       = polygon

    if not datauso.empty:
        datauso = datauso.groupby(['precuso']).agg({'predios_precuso':'sum','preaconst_precuso':'sum','preaterre_precuso':'sum'}).reset_index()
        datauso.columns = ['precuso','predios_precuso','preaconst_precuso','preaterre_precuso']
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        datauso = datauso.merge(dataprecuso,on='precuso',how='left',validate='m:1')

    engine.dispose()
    return data,datauso