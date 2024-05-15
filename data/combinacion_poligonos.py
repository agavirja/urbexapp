import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from shapely.ops import cascaded_union,unary_union

@st.cache_data(show_spinner=False)
def combinapolygons(datapredios,datalotescatastro):
    if not datapredios.empty and not datalotescatastro.empty and 'wkt' in datalotescatastro:
        datapredios = datapredios.merge(datalotescatastro,on='barmanpre',how='left',validate='m:1')        
        datapredios['order'] = range(len(datapredios))
        idd   = datapredios['wkt'].notnull()
        data1 = datapredios[idd]
        data2 = datapredios[~idd]
        
        if not data2.empty:
            data2.index = range(len(data2))
            datalotescatastro['geometry'] = datalotescatastro['wkt'].apply(lambda x: wkt.loads(x))
        
            for i in range(len(data2)):
                idd = datalotescatastro['barmanpre'].isin(data2['barmanpre'].iloc[i].split('|'))
                if sum(idd)>0:
                    #polygon = cascaded_union(datalotescatastro[idd]['geometry'].to_list())
                    polygon = unary_union(datalotescatastro[idd]['geometry'].to_list())
                    data2.loc[i,'wkt'] = polygon.wkt
        datapredios = pd.concat([data1,data2])
        datapredios = datapredios.sort_values(by='order',ascending=True)
        datapredios.drop(columns=['order'],inplace=True)
        datapredios.index = range(len(datapredios))
    return datapredios

def num_combinaciones_lote(datapredios,datalotescatastro):
    if not datapredios.empty and not datalotescatastro.empty:
        datalotescatastro.index = range(len(datalotescatastro))
        datalotescatastro['num_lotes_comb'] = None
        datalotescatastro['combinacion']    = None
        for i in range(len(datalotescatastro)):
            barmanpre = datalotescatastro['barmanpre'].iloc[i]
            idd       = datapredios['barmanpre'].str.contains(barmanpre)
            if sum(idd)>0:
                datalotescatastro.loc[i,'num_lotes_comb'] = sum(idd)
                datalotescatastro.loc[i,'combinacion'] = '|'.join(datapredios[idd]['id'].astype(int).astype(str).unique())
        
        idd = datalotescatastro['num_lotes_comb'].isnull()
        datalotescatastro = datalotescatastro[~idd]
    return datapredios,datalotescatastro
