import streamlit as st
import pandas as pd
import json
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import MultiPolygon
from sqlalchemy import create_engine 

from functions.getuso_destino import usosuelo_class

from data._algoritmo_cabida  import getareapolygon

@st.cache_data(show_spinner=False)
def main(inputvar={}):
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    data          = pd.DataFrame()
     
    polygon       = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    areaminlote   = inputvar['areaminlote'] if 'areaminlote' in inputvar else 0
    areamaxlote   = inputvar['areamaxlote'] if 'areamaxlote' in inputvar else 0
    estratomin    = inputvar['estratomin'] if 'estratomin' in inputvar else 0
    estratomax    = inputvar['estratomax'] if 'estratomax' in inputvar else 0
    tipoinmueble  = inputvar['tipoinmueble']  if 'tipoinmueble'  in inputvar else []

    
    if isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        
        # Busqueda por poligono
            # query   = f' ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"),geometry)'
        # Busqueda por lat/lng
            # datagrupo = pd.read_sql_query(f"SELECT distinct(grupo) FROM  bigdata.bogota_lotes_point WHERE ST_Within(geometry, ST_GeomFromText('{polygon}'))" , engine)
            # datagrupo = pd.read_sql_query(f"SELECT distinct(grupo) FROM  bigdata.bogota_lotes_point WHERE ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'),geometry)" , engine)
        
        query     = f' ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"),POINT(longitud,latitud))'
        datagrupo = pd.read_sql_query(f"SELECT distinct(grupo) as grupo,ST_AsText(geometry) as wkt FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)
        if not datagrupo.empty:
            lista     = ",".join(datagrupo['grupo'].astype(str).unique())
            query     = f" grupo IN ({lista})"
            data      = pd.read_sql_query(f"SELECT * FROM  bigdata.bogota_barmanpre_caracteristicas WHERE {query}" , engine)
            datamerge = pd.DataFrame()
            
            if not data.empty:
                data   = data.merge(datagrupo,on=['grupo'],how='left',validate='m:1')
    
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


            # Filtro por altura o pisos
            
            
             
            
            if not datamerge.empty and 'estrato' in datamerge and estratomin>0:
                datamerge = datamerge[datamerge['estrato']>=estratomin]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
                
            if not datamerge.empty and 'estrato' in datamerge and estratomax>0:
                datamerge = datamerge[datamerge['estrato']<=estratomax]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
        
            if isinstance(tipoinmueble,list) and tipoinmueble!=[]:
                if not any([x for x in tipoinmueble if isinstance(x,str) and 'todo' in x.lower()]):
                    datauso = usosuelo_class()
                    lista   = list(datauso[datauso['clasificacion'].isin(tipoinmueble)]['precuso'].unique())
                    if isinstance(lista,list) and lista!=[] and 'precuso' in datamerge:
                        datamerge = datamerge[datamerge['precuso'].isin(lista)]
                        data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
                    
            #-----------------------------------------------------------------#
            # Filtro de vias publicas / parques publicos
            if not datamerge.empty and 'precdestin' in datamerge:
                idd       = datamerge['precdestin'].isin(['65','66'])
                datamerge = datamerge[~idd]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]

    engine.dispose()
    
    #-------------------------------------------------------------------------#
    # Leer datos de getinfoterreno
    data_manzanas = getinfoterreno(data=data, areaminlote=areaminlote, areamaxlote=areamaxlote)
    
    
    #-------------------------------------------------------------------------#
    # Filtros por POT
    
    
    
    
    return data, data_manzanas


@st.cache_data(show_spinner=False)    
def getinfoterreno(data=pd.DataFrame(),areaminlote=None,areamaxlote=None):

    #-------------------------------------------------------------------------#
    # Info del terreno
    dataterreno             = getinfo(data=data,item='info_terreno')
    dataterreno['geometry'] = gpd.GeoSeries.from_wkt(dataterreno['wkt'])
    dataterreno             = gpd.GeoDataFrame(dataterreno, geometry='geometry')
    dataterreno['mancodigo'] = dataterreno['barmanpre'].apply(lambda x: x[0:9])
    
    if isinstance(areamaxlote,(float,int)) and areamaxlote>0:
        dataterreno = dataterreno[dataterreno['areapolygon']<=areamaxlote]
        
    #-------------------------------------------------------------------------#
    # Consolidar poligonos
    datageometry = gpd.GeoDataFrame(geometry=[unary_union(dataterreno.geometry)])
    poligonos    = []
    for idx, row in datageometry.iterrows():
        if isinstance(row.geometry, MultiPolygon):
            for parte in row.geometry.geoms:
                poligonos.append(parte)
        else:
            poligonos.append(row.geometry)
    datageometry       = gpd.GeoDataFrame(geometry=poligonos)
    datageometry['id'] = range(len(datageometry))
    datanew            = gpd.sjoin(dataterreno, datageometry, how='inner', op='intersects')
    datageometry['areapolygon'] = datageometry['geometry'].apply( lambda x: getareapolygon(x))
    
    #-------------------------------------------------------------------------#
    # Filtrar por area min y max del lote
    if isinstance(areaminlote,(float,int)) and areaminlote>0:
        datageometry = datageometry[datageometry['areapolygon']>=areaminlote]
        
    #-------------------------------------------------------------------------#
    # Merge data
    if not datageometry.empty:
        datamerge1 = datanew.groupby('id').agg({'areapolygon':'sum','mancodigo':'first','barmanpre':'nunique'}).reset_index()
        datamerge1.columns = ['id','areapolygontotal','mancodigo','lotes']
            
        datamerge2          = datanew.copy()
        datamerge2['grupo'] = datamerge2['grupo'].astype(str)
        datamerge2          = datamerge2.groupby('id')['grupo'].agg(lambda x: '|'.join(x)).reset_index()
        datamerge2.columns  = ['id','grupo']
        
        datamerge3 = datanew.groupby('id')['barmanpre'].agg(lambda x: '|'.join(x)).reset_index()
        datamerge3.columns  = ['id','barmanpre']
        
        datageometry = datageometry.merge(datamerge1,on='id',how='left',validate='1:1')
        datageometry = datageometry.merge(datamerge2,on='id',how='left',validate='1:1')
        datageometry = datageometry.merge(datamerge3,on='id',how='left',validate='1:1')
        datageometry['wkt_lotes'] = datageometry['geometry'].apply(lambda x: x.wkt)
        datageometry.drop(columns=['geometry'],inplace=True)
        
    #-------------------------------------------------------------------------#
    # Data de manzanas
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    
    if not datageometry.empty:
        lista        = "','".join(datageometry['mancodigo'].unique())
        query        = f" mancodigo IN ('{lista}')"
        engine       = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        datamanzanas = pd.read_sql_query(f"SELECT mancodigo, ST_AsText(geometry) as wkt_manzanas FROM  bigdata.data_bogota_manzana_simplify WHERE {query}" , engine)
        engine.dispose()
        
        if not datamanzanas.empty: 
            datamerge    = datamanzanas.drop_duplicates(subset='mancodigo',keep='first') 
            datageometry = datageometry.merge(datamerge,on='mancodigo',how='left',validate='m:1')
    
            datamerge         = datageometry.groupby('mancodigo').agg({'lotes':'sum'}).reset_index()
            datamerge.columns = ['mancodigo','lotesbymanzana']
            datageometry      = datageometry.merge(datamerge,on='mancodigo',how='left',validate='m:1')
            
    if not datageometry.empty:
        datageometry = pd.DataFrame(datageometry)
        
    return datageometry

@st.cache_data(show_spinner=False)     
def getinfo(data=pd.DataFrame(),item=None):
    result = []
    if not data.empty and 'barmanpre' in data and item in data:
        df         = data[['barmanpre','grupo','wkt',item]]
        df         = df[df[item].notnull()]
        df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df[df[item].notnull()]
        df         = df.explode(item)
        df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre'], 'grupo':x['grupo'], 'wkt':x['wkt']}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        result     = pd.json_normalize(df['formato'])
    return result 
