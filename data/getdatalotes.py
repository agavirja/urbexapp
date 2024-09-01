import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from datetime import datetime

from data.inmuebleANDusosuelo import inmueble2usosuelo
from data.getuso_destino import getuso_destino

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    data          = pd.DataFrame()
    databarmanpre = pd.DataFrame()
    
    polygon        = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    areamin        = inputvar['areamin'] if 'areamin' in inputvar else 0
    areamax        = inputvar['areamax'] if 'areamax' in inputvar else 0
    tipoinmueble   = inputvar['tipoinmueble']  if 'tipoinmueble'  in inputvar else []
    antiguedadmin  = inputvar['antiguedadmin'] if 'antiguedadmin' in inputvar else 0
    antiguedadmax  = inputvar['antiguedadmax'] if 'antiguedadmax' in inputvar else 0
    loteesquinero  = inputvar['loteesquinero'] if 'loteesquinero' in inputvar else None
    viaprincipal   = inputvar['viaprincipal']  if 'viaprincipal'  in inputvar else None
    frente         = inputvar['frente'] if 'frente' in inputvar else 0
    maxpredios     = inputvar['maxpredios'] if 'maxpredios' in inputvar else 0
    maxpropietario = inputvar['maxpropietario'] if 'maxpropietario' in inputvar else 0
    maxavaluo      = inputvar['maxavaluo'] if 'maxavaluo' in inputvar else 0
    latitud        = inputvar['latitud']  if 'latitud' in  inputvar and ( isinstance(inputvar['latitud'], float) or isinstance(inputvar['latitud'], int)) else None
    longitud       = inputvar['longitud'] if 'longitud' in inputvar and ( isinstance(inputvar['longitud'], float) or isinstance(inputvar['longitud'], int)) else None


    #-------------------------------------------------------------------------#
    # 1) Buscar los barmanpre que cumplen con uso del suelo 
    precuso      = inmueble2usosuelo(tipoinmueble)
    datausosuelo = pd.DataFrame()
    query        = ''
    if precuso!=[] and precuso!='':
        if isinstance(precuso, str):
            query += f" AND precuso = '{precuso}'"
        elif isinstance(precuso, list):
            precusolist  = "','".join(precuso)
            query += f" AND precuso IN ('{precusolist}')"
            
    if isinstance(polygon, str) and not 'none' in polygon.lower() :
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
        
    if query!='':
        query        = query.strip().strip('AND')
        datausosuelo = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
    
        if not datausosuelo.empty:
            barmanpre    = "','".join(datausosuelo['barmanpre'].unique())
            datausosuelo = pd.read_sql_query(f"SELECT barmanpre,precuso,predios_precuso,preaconst_precuso,preaterre_precuso,preaconst_total,preaterre_total,predios_total FROM  bigdata.bogota_catastro_compacta_precuso WHERE barmanpre IN ('{barmanpre}')" , engine)
    
            dataprecuso,dataprecdestin = getuso_destino()
            dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
            datausosuelo = datausosuelo.merge(dataprecuso,on='precuso',how='left',validate='m:1')
                       
    #-------------------------------------------------------------------------#
    # 2) Filtros por barmanpre, area y antiguedad 
    if not datausosuelo.empty:
    
        barmanpre  = "','".join(datausosuelo['barmanpre'].unique())
        query      = f" AND barmanpre IN ('{barmanpre}')"
        
        if areamin>0:
            query += f" AND preaconst>={areamin}"
        if areamax>0:
            query += f" AND preaconst<={areamax}"

        if antiguedadmin>0:
            antmin = datetime.now().year-antiguedadmin
            query += f" AND prevetustz<={antmin}"
        if antiguedadmax>0:
            antmax = datetime.now().year-antiguedadmax
            query += f" AND prevetustz>={antmax}"   
            
        if query!="":
            addvar = ''
            if longitud is not None and longitud is not None:
                addvar = f""", ST_Distance_Sphere(geometry, Point({longitud},{latitud})) AS distance"""

            query         = query.strip().strip('AND')+' AND '
            databarmanpre = pd.read_sql_query(f"SELECT distinct(barmanpre) as barmanpre {addvar} FROM  bigdata.data_bogota_catastro WHERE {query} ( precdestin<>'65' AND precdestin<>'66')" , engine)

        if not databarmanpre.empty:
            idd          = datausosuelo['barmanpre'].isin(databarmanpre['barmanpre'])
            datausosuelo = datausosuelo[idd]

    #-------------------------------------------------------------------------#
    # 3) Merge con data compacta y lotes
    if not datausosuelo.empty:
        barmanpre    = "','".join(datausosuelo['barmanpre'].unique())
        query        = f" barmanpre IN ('{barmanpre}')"
        datacompacta = pd.read_sql_query(f"SELECT barmanpre,prenbarrio,formato_direccion,prevetustzmin,prevetustzmax,estrato,connpisos,connsotano,conelevaci FROM  bigdata.bogota_catastro_compacta WHERE {query}" , engine)
        if not datacompacta.empty:
            datacompacta = datacompacta.drop_duplicates(subset='barmanpre',keep='first')
            datausosuelo = datausosuelo.merge(datacompacta,on='barmanpre',how='left',validate='m:1')
    
        datausosuelo = datausosuelo.groupby('barmanpre').apply(lambda x: x.to_dict(orient='records')).reset_index()
        datausosuelo.columns = ['barmanpre','infoByprecuso']
        
        query     = "','".join(datausosuelo['barmanpre'].unique())
        query     = f" lotcodigo IN ('{query}')" 
        datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
        datalotes = datalotes.drop_duplicates(subset='barmanpre',keep='first')
        if not datalotes.empty:
            idd          = datausosuelo['barmanpre'].isin(datalotes['barmanpre'])
            datausosuelo = datausosuelo[idd]
            data         = datalotes.merge(datausosuelo,on='barmanpre',how='left',validate='m:1')
            data.index   = range(len(data))
    engine.dispose()
    
    if not data.empty and not databarmanpre.empty and 'distance' in databarmanpre:
        datamerge = databarmanpre.drop_duplicates(subset=['barmanpre'],keep='first')
        data      = data.merge(datamerge[['barmanpre','distance']],on='barmanpre',how='left',validate='m:1')
        
    return data
