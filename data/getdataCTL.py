import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata_lectura"]
schema   = st.secrets["schema_bigdata"]

@st.cache_data(show_spinner=False)
def main(data):
    
    # input: data -> Es la data catastral, debe tener la columna matricula inmobiliaria
    datactl   = pd.DataFrame()
    datamatch = pd.DataFrame()
    
    if not data.empty:
        data = data[data['matriculainmobiliaria'].notnull()]
        data['matriculainmobiliaria'] = data['matriculainmobiliaria'].astype(str)
        
    if not data.empty:
        data['idmatch']   = range(len(data))
        data['codigo']    = data['matriculainmobiliaria'].apply(lambda x: x[0:4])
        data['matchcode'] = None
        
        #---------------------------------------------------------------------#
        # *** Bogota [hay que agregar mas ciudades al momento de expandirse]
        #---------------------------------------------------------------------#
        for i in ['50N','50C','50S']:
            idd = data['codigo'].str.contains(i)
            if sum(idd)>0:
                data.loc[idd,'matchcode'] = i
            
    if not data.empty and 'matchcode' in data:
        data['matricula'] = None
        idd = data['matchcode'].notnull()
        if sum(idd)>0:
            data.loc[idd,'matricula'] = data.loc[idd].apply(lambda x: x['matriculainmobiliaria'].split(x['matchcode'])[-1],axis=1)
    
    if not data.empty and 'matricula' in data:
        idd = data['matricula'].notnull()
        if sum(idd)>0:
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+datapaso['matricula']
                datapaso['prioridad'] = 1
                datamatch = pd.concat([datamatch,datapaso])
            except: pass
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'-'+datapaso['matricula']
                datapaso['prioridad'] = 1
                datamatch = pd.concat([datamatch,datapaso])    
            except: pass
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'0'+datapaso['matricula']
                datapaso['prioridad'] = 2
                datamatch = pd.concat([datamatch,datapaso])
            except: pass 
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'-0'+datapaso['matricula']
                datapaso['prioridad'] = 2
                datamatch = pd.concat([datamatch,datapaso]) 
            except: pass
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+datapaso['matricula'].apply(lambda x: x.lstrip('0'))
                datapaso['prioridad'] = 3
                datamatch = pd.concat([datamatch,datapaso])
            except: pass
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'-'+datapaso['matricula'].apply(lambda x: x.lstrip('0'))
                datapaso['prioridad'] = 3
                datamatch = pd.concat([datamatch,datapaso])    
            except: pass
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'0'+datapaso['matricula'].apply(lambda x: x.lstrip('0'))
                datapaso['prioridad'] = 3
                datamatch = pd.concat([datamatch,datapaso])
            except: pass 
            try:
                datapaso = data[idd][['idmatch','matriculainmobiliaria','matricula','matchcode']].copy()
                datapaso['matriculainmobiliaria'] = datapaso['matchcode']+'-0'+datapaso['matricula'].apply(lambda x: x.lstrip('0'))
                datapaso['prioridad'] = 3
                datamatch = pd.concat([datamatch,datapaso]) 
            except: pass
            
    if not datamatch.empty:
            lista = "','".join(datamatch['matriculainmobiliaria'].unique())
            query = f" matricula_completa IN ('{lista}')"
    
            engine  = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            dataCTL = pd.read_sql_query(f"SELECT url,direccion,codigos,last_code,last_fecha, matricula_completa as matriculainmobiliaria FROM bigdata.snr_CTL WHERE {query} ;" , engine)
            engine.dispose()
            
            if not dataCTL.empty:
                datamatch = datamatch.drop_duplicates(subset='matriculainmobiliaria',keep='first')
                dataCTL   = dataCTL.merge(datamatch[['matriculainmobiliaria','idmatch','prioridad']],on='matriculainmobiliaria',how='left',validate='m:1')
                
            if not dataCTL.empty and 'idmatch' in dataCTL:
                
                datamerge = dataCTL.sort_values(by='prioridad',ascending=True).drop_duplicates(subset='idmatch',keep='first')
                if 'matriculainmobiliaria' in datamerge: datamerge.drop(columns='matriculainmobiliaria',inplace=True) 
                data = data.merge(datamerge,on='idmatch',how='left',validate='1:1')

            if not data.empty and 'url' in data:
                datactl = data[data['url'].notnull()]
                
    if not datactl.empty and 'last_fecha' in datactl:
        try: 
            datactl = datactl.sort_values(by='last_fecha',ascending=False)
            datactl['last_fecha'] = pd.to_datetime(datactl['last_fecha'],errors='coerce').apply(lambda x: x.strftime('%Y-%m-%d'))
        except: pass
        
    return datactl
