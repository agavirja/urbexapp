import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import MultiPolygon
from sqlalchemy import create_engine 

from data._principal_lotes import datalote
from data._algoritmo_cabida  import getareapolygon

@st.cache_data(show_spinner=False)
def getoptionsnormativa():
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.read_sql_query("SELECT variable,indice,input FROM  bigdata.bogota_lotes_normativa_dict" , engine)
    engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def getlotesnormativa(inputvar={}):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame(columns=['lista'])
    
    datageometry  = pd.DataFrame(columns=['barmanpre', 'grupo', 'wkt'])
    areaminlote   = inputvar['areaminlote'] if 'areaminlote' in inputvar else 0
    areamaxlote   = inputvar['areamaxlote'] if 'areamaxlote' in inputvar else 0
        
    if isinstance(inputvar,list) and inputvar!=[]:
        query = ""
        for items in inputvar:
            query += f" AND {items['variable']}={items['indice']} "
            query = query.strip().strip('AND')
            
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT lista FROM  bigdata.bogota_lotes_normativa WHERE {query} LIMIT 1" , engine)
        engine.dispose()
        
    if not data.empty:
        lista      = data['lista'].iloc[0]
        data_lotes = datalote(grupo=lista)

        data_lotes['geometry']  = gpd.GeoSeries.from_wkt(data_lotes['wkt'])
        data_lotes              = gpd.GeoDataFrame(data_lotes, geometry='geometry')
        
        #---------------------------------------------------------------------#
        # Filtrar por area max
        if isinstance(areamaxlote,(float,int)) and areamaxlote>0:
            data_lotes = data_lotes[data_lotes['areapolygon']<=areamaxlote]

        datageometry = gpd.GeoDataFrame(geometry=[unary_union(data_lotes.geometry)])
        poligonos    = []
        for idx, row in datageometry.iterrows():
            if isinstance(row.geometry, MultiPolygon):
                for parte in row.geometry.geoms:
                    poligonos.append(parte)
            else:
                poligonos.append(row.geometry)
        datageometry       = gpd.GeoDataFrame(geometry=poligonos)
        datageometry['id'] = range(len(datageometry))
        datageometry['areapolygon'] = datageometry['geometry'].apply( lambda x: getareapolygon(x))

        #---------------------------------------------------------------------#
        # Filtrar por area min
        if isinstance(areaminlote,(float,int)) and areaminlote>0:
            datageometry = datageometry[datageometry['areapolygon']>=areaminlote]

        datapaso          = gpd.sjoin(data_lotes[['grupo','barmanpre','geometry']], datageometry[['id','geometry']], how='inner', op='intersects')
        datapaso['grupo'] = datapaso['grupo'].astype(str)
        datapaso1         = datapaso.groupby('id')[['barmanpre','grupo']].agg(lambda x: '|'.join(x)).reset_index()
        datapaso1.columns = ['id','barmanpre','grupo']
        datapaso2         = datapaso.groupby('id')['barmanpre'].count().reset_index()
        datapaso2.columns = ['id','lotes']
        datageometry      = datageometry.merge(datapaso1,on='id',how='left',validate='1:1')
        datageometry      = datageometry.merge(datapaso2,on='id',how='left',validate='1:1')

        datageometry['wkt'] = datageometry['geometry'].apply(lambda x: x.wkt)
        datageometry.drop(columns=['geometry'],inplace=True)
        datageometry = pd.DataFrame(datageometry)

    return datageometry