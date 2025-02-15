import streamlit as st
import pandas as pd
import json
import geopandas as gpd
from shapely import wkt
from sqlalchemy import create_engine 
from shapely.ops import unary_union

from functions.getuso_destino import usosuelo_class
from data._algoritmo_cabida  import getareapolygon
from data._principal_shapefile import localidad as datalocalidad

@st.cache_data(show_spinner=False)
def main(inputvar={}):
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_write_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    polygon       = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    localidad     = inputvar['localidad'] if 'localidad' in inputvar and isinstance(inputvar['localidad'], str) else None
    areaminlote   = inputvar['areaminlote'] if 'areaminlote' in inputvar else 0
    areamaxlote   = inputvar['areamaxlote'] if 'areamaxlote' in inputvar else 0
    estratomin    = inputvar['estratomin'] if 'estratomin' in inputvar else 0
    estratomax    = inputvar['estratomax'] if 'estratomax' in inputvar else 0
    precuso       = inputvar['precuso'] if 'precuso' in inputvar else []

    pisos                 = inputvar['pisos'] if 'pisos' in inputvar else 0
    altura_min_pot        = inputvar['altura_min_pot'] if 'altura_min_pot' in inputvar else 0
    tratamiento           = inputvar['tratamiento'] if 'tratamiento' in inputvar else 0
    actuacion_estrategica = inputvar['actuacion_estrategica'] if 'actuacion_estrategica' in inputvar else 0
    area_de_actividad     = inputvar['area_de_actividad'] if 'area_de_actividad' in inputvar else 0
    via_principal         = inputvar['via_principal'] if 'via_principal' in inputvar else 0
    numero_propietarios   = inputvar['numero_propietarios'] if 'numero_propietarios' in inputvar else 0
    
    
    #-------------------------------------------------------------------------#
    # 1. Lista de lotes:
    #-------------------------------------------------------------------------#
    query        = f" tratamiento={tratamiento} AND actuacion_estrategica={actuacion_estrategica} AND area_de_actividad={area_de_actividad} AND pisos={pisos} AND numero_propietarios={numero_propietarios} AND altura_min_pot={altura_min_pot} AND via_principal={via_principal}"
    data         = pd.read_sql_query(f"SELECT lista FROM  bigdata.bogota_lotes_normativa WHERE {query} LIMIT 1" , engine)
    datageometry = pd.DataFrame()

    #-------------------------------------------------------------------------#
    # 2. Filtro por poligono:
    #-------------------------------------------------------------------------#
    query = ""
    if isinstance(polygon,str) and polygon!='' and 'none' not in polygon.lower():
        query = f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"),POINT(longitud,latitud))'
        
    if isinstance(localidad,str) and localidad!='' and 'tod' not in localidad.lower():
        data_localidad,_ = datalocalidad(locnombre=localidad)
        if not data_localidad.empty:
            locpolygon = data_localidad['wkt'].iloc[0]
            query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{locpolygon}"),POINT(longitud,latitud))'
                
    if query!="":
        query        = query.strip().strip('AND')
        datageometry = pd.read_sql_query(f"SELECT grupo, barmanpre, manzcodigo, ST_AsText(geometry) as wkt FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)
        
        if not datageometry.empty:
            lista        = data['lista'].iloc[0].split('|')
            idd          = (datageometry['grupo'].isin(lista)) | (datageometry['grupo'].astype(str).isin(lista))  | (datageometry['grupo'].astype(int).astype(str).isin(lista))
            datageometry = datageometry[idd]
            
    if datageometry.empty and not data.empty: 
        lista        = data['lista'].iloc[0].split('|')
        lista        = ",".join(lista)
        query        = f" grupo IN ({lista})"
        datageometry = pd.read_sql_query(f"SELECT grupo, barmanpre, manzcodigo, ST_AsText(geometry) as wkt FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)

    if not datageometry.empty:
        datageometry['geometry'] = gpd.GeoSeries.from_wkt(datageometry['wkt'])
        datageometry             = gpd.GeoDataFrame(datageometry, geometry='geometry')
        
        # Area de los poligonos
    if not datageometry.empty and 'geometry' in datageometry:
        datageometry['areapolygon'] = datageometry['geometry'].apply( lambda x: getareapolygon(x))


    #-------------------------------------------------------------------------#
    # 3. Filtro por area maxima [remover los lotes que por si solos tienen mas de "areamax"]
    #-------------------------------------------------------------------------#
    if not datageometry.empty and 'areapolygon' in datageometry and areamaxlote>0:
        datageometry = datageometry[datageometry['areapolygon']<=areamaxlote]
        
    #-------------------------------------------------------------------------#
    # 4. Filtros adicionales: 
    #-------------------------------------------------------------------------#
    if not datageometry.empty and 'grupo' in datageometry:
        lista     = list(datageometry['grupo'].astype(str).unique())
        lista     = ','.join(lista)
        query     = f" grupo IN ({lista})"
        data      = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_barmanpre_caracteristicas WHERE {query}" , engine)
        datamerge = pd.DataFrame()
        if not data.empty:
            datamerge = data[['grupo','barmanpre']]
            formato   = [
                {'column':'general_catastro','variables':['barmanpre','prevetustzmin','prevetustzmax','estrato']},
                {'column':'catastro_byprecuso','variables':['barmanpre','precuso','preaconst_precusomin','preaconst_precusomax']},
                {'column':'catastro_precdestin','variables':['barmanpre','precdestin']}
                         ]
            
            for i in formato:
                item       = i['column']
                variables  = i['variables']
                df         = data[['barmanpre',item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
                df         = pd.DataFrame(df)
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                if isinstance(variables,list) and variables!=[]:
                    df     = df[variables]
                datamerge  = datamerge.merge(df,on='barmanpre',how='inner')

            #-----------------------------------------------------------------#
            # Filtros
            if not datamerge.empty and 'estrato' in datamerge and estratomin>0:
                datamerge = datamerge[datamerge['estrato']>=estratomin]

            if not datamerge.empty and 'estrato' in datamerge and estratomax>0:
                datamerge = datamerge[datamerge['estrato']<=estratomax]
                
            if isinstance(precuso,list) and precuso!=[]:
                if not any([x for x in precuso if isinstance(x,str) and 'todo' in x.lower()]):
                    datauso = usosuelo_class()
                    lista   = list(datauso[datauso['clasificacion'].isin(precuso)]['precuso'].unique())
                    if isinstance(lista,list) and lista!=[] and 'precuso' in datamerge:
                        datamerge = datamerge[datamerge['precuso'].isin(lista)]

            #-----------------------------------------------------------------#
            # Filtro de vias publicas / parques publicos
            if not datamerge.empty and 'precdestin' in datamerge:
                idd       = datamerge['precdestin'].isin(['65','66'])
                datamerge = datamerge[~idd]

        if not datamerge.empty:
            idd          = datageometry['grupo'].isin(datamerge['grupo'])
            datageometry = datageometry[idd]
                
    #-------------------------------------------------------------------------#
    # 5. Unir lotes
    #-------------------------------------------------------------------------#
    if not datageometry.empty and 'geometry' in datageometry:
        datagroup                = datageometry.groupby('manzcodigo').apply(lambda x: unary_union(x.geometry)).reset_index()
        datagroup.columns        = ['manzcodigo','geometry']
        
        datageometry['grupo']    = datageometry['grupo'].astype(str)
        datamerge                = datageometry.groupby('manzcodigo').agg({'grupo': lambda x: '|'.join(x),'barmanpre': lambda x: '|'.join(x),'areapolygon':'sum'}).reset_index()
        datamerge.columns        = ['manzcodigo','grupo','barmanpre','areamaxcombinacion']
        datageometry             = datagroup.merge(datamerge,on='manzcodigo',how='left',validate='1:1')
        datageometry             = gpd.GeoDataFrame(datageometry, geometry='geometry')

    #-------------------------------------------------------------------------#
    # 6. Filtro por area minima [remover los lotes que combinados no tienen mas de "areamin"]
    #-------------------------------------------------------------------------#
    if not datageometry.empty and 'areamaxcombinacion' in datageometry and areaminlote>0:
        datageometry = datageometry[datageometry['areamaxcombinacion']>=areaminlote]

    #-------------------------------------------------------------------------#
    # 7. Ajustes del geometry: 
    #-------------------------------------------------------------------------#
    if not datageometry.empty:
        datageometry['geometry'] = datageometry['geometry'].apply(lambda x: x.wkt)
        datageometry = pd.DataFrame(datageometry)
        
    engine.dispose()
    return datageometry
