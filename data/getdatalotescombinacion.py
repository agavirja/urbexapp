import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from shapely.ops import unary_union
from shapely import wkt

from data.getuso_destino import getuso_destino

@st.cache_data(show_spinner=False)
def getdatacombinacionlotes(code):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    datapredios       = pd.DataFrame()
    datalotescatastro = pd.DataFrame()
    polygon           = None  
    numlotes          = 0
    
    if isinstance(code, str) and code!='':
        barmanprelist = str(code).split('|')
        query = "','".join(barmanprelist)
        query = f" lotcodigo IN ('{query}')"   
        datalotescatastro = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        datalotescatastro = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')
        
        if not datalotescatastro.empty:
            datapaso = datalotescatastro.copy()
            datapaso['geometry'] = datapaso['wkt'].apply(lambda x: wkt.loads(x))
            polygon  = unary_union(datapaso['geometry'].to_list()).wkt
            numlotes = len(datalotescatastro)
            
        query = "','".join(barmanprelist)
        query = f" barmanpre IN ('{query}')"   
        datapredios = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_barmanpre_lotes WHERE {query}" , engine)        
        datausosuelo = pd.read_sql_query(f"SELECT precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst_total FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        
        if not datapredios.empty and not datalotescatastro.empty:
            idd = datapredios['barmanpre'].isin(datalotescatastro['barmanpre'])
            if sum(idd)>0:
                datapredios = datapredios[idd]
            datamerge = datapredios[['barmanpre','preaconst','preaterre','estrato','predios','pisos','sotanos','avaluo_catastral','predial','propietarios']]
            datamerge = datamerge.drop_duplicates(subset='barmanpre',keep='first')
            datalotescatastro = datalotescatastro.merge(datamerge,on='barmanpre',how='left',validate='m:1')
        
        if not datapredios.empty:
            datapredios['agg'] = 1
            datapredios = datapredios.groupby('agg').agg({'preaconst': 'sum', 'preaterre': 'sum', 'prevetustzmin': 'min', 'prevetustzmax': 'max', 'estrato': 'max', 'predios_total': 'sum', 'pisos': 'max', 'sotanos': 'max', 'predios': 'sum', 'areapolygon': 'sum', 'esquinero': 'max', 'tipovia': 'min', 'propietarios': 'sum', 'avaluo_catastral': 'sum', 'predial': 'sum'}).reset_index()
            datapredios['wkt']   = polygon
            datapredios['lotes'] = numlotes
            
        if not datausosuelo.empty:
            datausosuelo = datausosuelo.groupby('precuso').agg({'predios_precuso':'sum','preaconst_precuso':'sum','preaterre_precuso':'sum'}).reset_index()
            
            dataprecuso,dataprecdestin = getuso_destino()
            dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
            datausosuelo = datausosuelo.merge(dataprecuso,on='precuso',how='left',validate='m:1')
    engine.dispose()
    
    return datapredios,datalotescatastro,datausosuelo

@st.cache_data(show_spinner=False)
def mergedatabybarmanpre(d1,d2,variables):
    if not d1.empty and not d2.empty and 'barmanpre' in d1 and 'barmanpre' in d2:
        datamerge = d2.drop_duplicates(subset=['barmanpre'],keep='first')
        if variables!=[]:
            variables = [x for x in variables if x in d2 and x not in d1]
            variables = ['barmanpre']+variables
        d1 = d1.merge(datamerge[variables],on='barmanpre',how='left',validate='m:1')
    return d1
