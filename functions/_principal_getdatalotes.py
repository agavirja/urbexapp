import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from functions.getuso_destino import usosuelo_class
from data._principal_caracteristicas import datapredios

@st.cache_data(show_spinner=False)
def main(inputvar={}):
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    data          = pd.DataFrame()
    
    polygon       = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    areamin       = inputvar['areamin'] if 'areamin' in inputvar else 0
    areamax       = inputvar['areamax'] if 'areamax' in inputvar else 0
    tipoinmueble  = inputvar['tipoinmueble']  if 'tipoinmueble'  in inputvar else []
    antiguedadmin = inputvar['antiguedadmin'] if 'antiguedadmin' in inputvar else 0
    antiguedadmax = inputvar['antiguedadmax'] if 'antiguedadmax' in inputvar else 0
    estratomin    = inputvar['estratomin'] if 'estratomin' in inputvar else 0
    estratomax    = inputvar['estratomax'] if 'estratomax' in inputvar else 0
        
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
            if not datamerge.empty and 'preaconst_precusomin' in datamerge and areamin>0:
                datamerge = datamerge[datamerge['preaconst_precusomin']>=areamin]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
                
            if not datamerge.empty and 'preaconst_precusomax' in datamerge and areamax>0:
                datamerge = datamerge[datamerge['preaconst_precusomax']<=areamax]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
              
            if not datamerge.empty and 'prevetustzmin' in  datamerge and antiguedadmin>0:
                datamerge = datamerge[datamerge['prevetustzmin']>=antiguedadmin]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]

            if not datamerge.empty and 'prevetustzmax' in  datamerge and antiguedadmax>0:
                datamerge = datamerge[datamerge['prevetustzmax']<=antiguedadmax]
                data      = data[data['barmanpre'].isin(datamerge['barmanpre'])]
                
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
    return data
