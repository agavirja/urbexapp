import streamlit as st
import geopandas as gpd
from shapely.ops import unary_union

@st.cache_data(show_spinner=False)
def polygonunion(data_lote):
    df = data_lote.copy()
    if not data_lote.empty and len(data_lote)>1:
        df['geometry'] = gpd.GeoSeries.from_wkt(df['wkt'])
        df             = gpd.GeoDataFrame(df, geometry='geometry')
        df             = gpd.GeoDataFrame(geometry=[unary_union(df.geometry)])
        df['wkt']      = df['geometry'].apply(lambda x: x.wkt)
        df['idmerge']  = 1
        df             = df[['idmerge','wkt']]
        
        data_lote['idmerge'] = 1
        datamerge1 = data_lote.astype(str).groupby('idmerge')[['barmanpre','grupo']].agg(lambda x: ' | '.join(set(x))).reset_index()
        datamerge2 = data_lote.groupby('idmerge').agg({'latitud':'median','longitud':'median'}).reset_index()
        datamerge1['idmerge'] = datamerge1['idmerge'].astype(int)
        datamerge2['idmerge'] = datamerge2['idmerge'].astype(int)
        datapaso = datamerge1.merge(datamerge2,on='idmerge',how='outer')
        df       = df.merge(datapaso,on='idmerge',how='outer')
        df.drop(columns=['idmerge'],inplace=True)
    return df