import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]

    viaprincipal   = inputvar['viaprincipal']  if 'viaprincipal'  in inputvar else None
    maxpropietario = inputvar['maxpropietario'] if 'maxpropietario' in inputvar else 0
    maxavaluo      = inputvar['maxavaluo'] if 'maxavaluo' in inputvar else 0
    maxpiso        = inputvar['maxpiso'] if 'maxpiso' in inputvar else 0
    pot            = inputvar['pot']  if 'pot'  in inputvar else []

    query    = ""
    if isinstance(maxpiso,(float,int)) and maxpiso>0:
        query += f" AND connpisos<={maxpiso}"
    if isinstance(maxpropietario,(float,int)) and maxpropietario>0:
        query += f" AND propietarios<={maxpropietario}" 
    if isinstance(maxavaluo,(float,int)) and maxavaluo>0:
        query += f" AND avaluo_catastral<={maxavaluo}" 
    if query!='':
        query = query.strip().strip('AND')
        query = f" WHERE {query}"
        
    engine          = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data            = pd.read_sql_query(f"SELECT mancodigo,prenbarrio,preaconst,preaterre,prevetustzmin,prevetustzmax,estrato,lotes,predios,connpisos,avaluo_catastral,propietarios,infoByprecuso,ST_AsText(geometry) as wkt FROM  bigdata.bogota_mancodigo_general {query}" , engine)
    datalocalidades = pd.read_sql_query("SELECT locnombre,loccodigo,ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_localidades_simplify" , engine)

    if not data.empty and isinstance(pot,list) and pot!=[]:
        
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')

        if not datalocalidades.empty:
            df             = datalocalidades.copy()
            df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt'])
            df             = gpd.GeoDataFrame(df, geometry='geometry')
            data           = gpd.sjoin(data,df, how="left", op="within")
            for j in ['index_left','index_right']:
                if j in data: del data[j]
        
        datamerge         = data.groupby('loccodigo')['mancodigo'].count().reset_index()
        datamerge.columns = ['loccodigo','countmanzanas']
        datalocalidades   = datalocalidades.merge(datamerge,on='loccodigo',how='left',validate='m:1')
        
        for items in pot:
            #-------------------------------------------------------------#
            # Tratamiento urbanistico
            if 'tipo' in items and 'tratamientourbanistico' in items['tipo']:
                query = ""
                if 'alturaminpot' in items and items['alturaminpot']>0:
                    query += f" AND  (alturamax_num>={items['alturaminpot']} OR alturamax_num IS NULL)"
                if 'tratamiento' in items and isinstance(items['tratamiento'],list) and items['tratamiento']!=[]:
                    lista  = "','".join(items['tratamiento'])
                    query += f" nombretra IN ('{lista}')"   
                if query!='':
                    query = query.strip().strip('AND')
                    query = f" WHERE {query}"
                
                datatratamiento = pd.read_sql_query(f"SELECT id as idtrat,alturamax,nombretra as tratamiento, ST_AsText(geometry) as wkt FROM  pot.bogota_tratamientourbanistico {query}" , engine)
                if not datatratamiento.empty:
                    datatratamiento['geometry'] = gpd.GeoSeries.from_wkt(datatratamiento['wkt'])
                    datatratamiento             = gpd.GeoDataFrame(datatratamiento, geometry='geometry')
                    datatratamiento.drop(columns=['wkt'],inplace=True)
                    data                        = gpd.sjoin(data,datatratamiento, how="left", op="within")
                    data                        = data[data['idtrat'].notnull()]
                    for j in ['index_left','index_right']:
                        if j in data: del data[j]
                
            #-------------------------------------------------------------#
            # Area de actividad
            if 'tipo' in items and 'areaactividad' in items['tipo']:
                query = ""
                if 'nombreare' in items and isinstance(items['nombreare'],list) and items['nombreare']!=[]:
                    lista  = "','".join(items['nombreare'])
                    query += f" nombreare IN ('{lista}')"  
                if query!='':
                    query = query.strip().strip('AND')
                    query = f" WHERE {query}"
                    
                datactivad = pd.read_sql_query(f"SELECT id as idactividad,nombreare as actividad, ST_AsText(geometry) as wkt FROM  pot.bogota_areaactividad {query}" , engine)
                if not datactivad.empty:
                    datactivad['geometry'] = gpd.GeoSeries.from_wkt(datactivad['wkt'])
                    datactivad             = gpd.GeoDataFrame(datactivad, geometry='geometry')
                    datactivad.drop(columns=['wkt'],inplace=True)
                    data                   = gpd.sjoin(data,datactivad, how="left", op="within")
                    data                   = data[data['idactividad'].notnull()]
                    for j in ['index_left','index_right']:
                        if j in data: del data[j]

            #-------------------------------------------------------------#
            # Actuacion Estrategica
            if 'tipo' in items and 'actuacionestrategica' in items['tipo']:
                if 'isin' in items and any([w for w in ['si','no'] if w in items['isin'].lower()]):
                    dataactuacion = pd.read_sql_query("SELECT id as idactuacion,nombre as actuacion,priorizaci as priorizacion, ST_AsText(geometry) as wkt FROM  pot.bogota_actuacionestrategica " , engine)
                    if not dataactuacion.empty:
                        dataactuacion['geometry'] = gpd.GeoSeries.from_wkt(dataactuacion['wkt'])
                        dataactuacion             = gpd.GeoDataFrame(dataactuacion, geometry='geometry')
                        dataactuacion.drop(columns=['wkt'],inplace=True)
                        data                      = gpd.sjoin(data,dataactuacion, how="left", op="within")
                        for j in ['index_left','index_right']:
                            if j in data: del data[j]
                            
                    if 'si' in items['isin'].lower():
                        data = data[data['idactuacion'].notnull()]
                    elif 'no' in items['isin'].lower():
                        data = data[data['idactuacion'].isnull()]
                        
       
                        
    engine.dispose()

    variables = [x for x in ['geomtry','wkt'] if x in list(data)]
    if isinstance(variables,list) and variables!=[]:
        data.drop(columns=variables,inplace=True)
            
    if not data.empty:
        data         = pd.DataFrame(data)
        lista        = "','".join(data['mancodigo'].unique())
        query        = f" mancodigo IN ('{lista}')"  
        datamanzanas = pd.read_sql_query(f"SELECT mancodigo, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_manzana_simplify WHERE {query}" , engine)
        
        if not datamanzanas.empty:
            datamerge = datamanzanas.drop_duplicates(subset='mancodigo',keep='first')
            data      = data.merge(datamerge,on='mancodigo',how='left',validate='m:1')

    return data,datalocalidades
