import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine 

from functions.read_data import execute_query
from data.filters import main as filters
from data._principal_lotes_radio import data_lotes_radio

@st.cache_data(show_spinner=False)
def dataprediales(grupo=None, variables='*',seleccion=0):  # seleccion- 0: ambos, 1: actuales, 2: historicos, 
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]

    datapredialesactuales = pd.DataFrame(columns=['grupo', 'barmanpre', 'prediales', 'prediales_mt2', 'prediales_mt2_by_precuso'])
    datapredialestotales  = pd.DataFrame(columns=['grupo', 'barmanpre', 'prediales', 'prediales_mt2', 'prediales_mt2_by_precuso'])
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        if len(grupo)>100:
            if seleccion==0:
                datapredialesactuales = execute_query(grupo, 'bogota_barmanpre_prediales_actuales', variables=variables, chunk_size=100)
                datapredialestotales  = execute_query(grupo, 'bogota_barmanpre_prediales_totales', variables=variables, chunk_size=100)
            elif seleccion==1:
                datapredialesactuales = execute_query(grupo, 'bogota_barmanpre_prediales_actuales', variables=variables, chunk_size=100)
            elif seleccion==2:
                datapredialestotales  = execute_query(grupo, 'bogota_barmanpre_prediales_totales', variables=variables, chunk_size=100)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            if seleccion==0:
                datapredialesactuales = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_prediales_actuales WHERE {query}", engine)
                datapredialestotales  = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_prediales_totales WHERE {query}", engine)
            elif seleccion==1:
                datapredialesactuales = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_prediales_actuales WHERE {query}", engine)
            elif seleccion==2:
                datapredialestotales  = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_prediales_totales WHERE {query}", engine)
            engine.dispose()
    data = pd.concat([datapredialesactuales,datapredialestotales])
    return data


@st.cache_data(show_spinner=False)
def data_prediales(grupo=None,seleccion=0):
    variables  = 'grupo,barmanpre,prediales'
    data       = dataprediales(grupo=grupo, variables=variables,seleccion=seleccion)
    resultado  = pd.DataFrame()
    variable   = 'prediales'
    if not data.empty:
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
    return resultado


@st.cache_data(show_spinner=False)
def estadisticas_prediales(data=pd.DataFrame(), data_geometry=pd.DataFrame(), inputvar={}):
    
    output  = {
         'avaluocatastralmt2':{'label': 'Avalúo catastral por mt2 (último año)','value': None},
         'predialmt2':{'label': 'Predial por mt2 (último año)','value': None},
         'predialesyear':{'label': 'Histórico prediales y avalúo catastral','value': None},
         }
    
    data = filters(data=data, datageometry=pd.DataFrame(), inputvar=inputvar)
    if not data.empty:
        df                       = data.copy()
        df['preaconst']          = pd.to_numeric(df['preaconst'],errors='coerce') if 'preaconst' in df else None
        df['avaluo_catastral']   = pd.to_numeric(df['avaluo_catastral'],errors='coerce')  if 'avaluo_catastral' in df else None
        df['impuesto_ajustado']  = pd.to_numeric(df['impuesto_ajustado'],errors='coerce') if 'impuesto_ajustado' in df else None
        df['avaluomt2']          = None
        idd                      = (df['avaluo_catastral']>0) & (df['preaconst']>0)
        df.loc[idd,'avaluomt2']  = df.loc[idd,'avaluo_catastral']/df.loc[idd,'preaconst'] 
        df['predialmt2']         = None
        idd                      = (df['impuesto_ajustado']>0) & (df['preaconst']>0)
        df.loc[idd,'predialmt2'] = df.loc[idd,'impuesto_ajustado']/df.loc[idd,'preaconst'] 

        #---------------------------------------------------------------------#
        # Avaluo y predial por metro cuadrado
        predialeslastyear = df.copy()
        w                 = predialeslastyear.groupby(['chip'])['year'].max().reset_index()
        w.columns         = ['chip','maxyear']
        predialeslastyear = predialeslastyear.merge(w,on='chip',how='left',validate='m:1')
        predialeslastyear = predialeslastyear[predialeslastyear['year']==predialeslastyear['maxyear']]
        predialeslastyear = predialeslastyear.sort_values(by=['chip','avaluomt2'],ascending=False).drop_duplicates(subset='chip',keep='first')
        
        output.update({'avaluocatastralmt2':{'label':'Avalúo catastral por mt2 (último año)','value':predialeslastyear['avaluomt2'].median()}})
        output.update({'predialmt2':{'label':'Predial por mt2 (último año)','value':predialeslastyear['predialmt2'].median()}})
        
        #---------------------------------------------------------------------#
        # Avaluo y predial por years
        datagroup = df.copy()
        datagroup = datagroup[datagroup['year']>2020]
        datagroup = datagroup.groupby(['year','chip']).agg({'avaluomt2':'max','predialmt2':'max'}).reset_index()
        datagroup.columns = ['year','chip','avaluomt2','predialmt2']
        datagroup = datagroup.groupby('year').agg({'avaluomt2':'median','predialmt2':'median'}).reset_index()
        datagroup.columns = ['year','avaluomt2','predialmt2']
        datagroup = datagroup.to_dict(orient='records')
        output.update({'predialesyear':{'label':'Histórico prediales y avalúo catastral','value':datagroup}})

    return output

def transformjson(x):
    result = []
    try:
        data_dict = json.loads(x)
        
        for tipo, transacciones in data_dict.items():
            for transaccion in transacciones:
                transaccion['tipo'] = tipo  # Añadir el campo 'tipo'
                result.append(transaccion)
    except: result = None
    return result
