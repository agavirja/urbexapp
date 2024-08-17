import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 

from data.getdatabuilding import main as getdatabuilding
from data.inmuebleANDusosuelo import usosuelo2inmueble

@st.cache_data(show_spinner=False)
def main(polygon=None,precuso=None):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    #-------------------------------------------------------------------------#
    # Informacion de predios
    datapredios = pd.DataFrame()
    query = ""
    if isinstance(polygon, str) and not 'none' in polygon.lower() and polygon!='':
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), geometry)'
        
    if isinstance(precuso,list) and precuso!=[]:
        precusolist  = '","'.join(precuso)
        query += f' AND precuso IN ("{precusolist}")'
    elif isinstance(precuso,str) and precuso!='':
        query += f" AND precuso = '{precuso}'"
        
    if query!='':
        query       = query.strip().strip('AND')
        datapredios = pd.read_sql_query(f"SELECT barmanpre,formato_direccion,precuso,predios_precuso,preaconst_precuso,preaterre_precuso,prenbarrio,preaconst,preaterre,prevetustzmin,prevetustzmax,estrato,predios,connpisos,connsotano,contsemis,construcciones,conelevaci,nombre_conjunto,avaluomt2,predialmt2,propietarios,avaluocatastral,valormt2_transacciones,transacciones,latitud,longitud FROM  bigdata.bogota_barmanpre_general WHERE {query}" , engine)
    engine.dispose()
    
    #-------------------------------------------------------------------------#
    # Informacion de barmanpre
    datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = [pd.DataFrame()]*6
    if not datapredios.empty:
        listabarmanpre = list(datapredios['barmanpre'].unique())
        datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(listabarmanpre)

        barmanprelist  = '","'.join(listabarmanpre)
        query          = f' barmanpre IN ("{barmanprelist}")'
        databarmanpre  = pd.read_sql_query(f"SELECT distinct(barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND (precdestin='65' OR precdestin='66')" , engine)
        if not databarmanpre.empty:
            idd          = datapredios['barmanpre'].isin(databarmanpre['barmanpre'])
            datapredios  = datapredios[~idd]
            idd          = datacatastro['barmanpre'].isin(databarmanpre['barmanpre'])
            datacatastro = datacatastro[~idd]
            
    #-------------------------------------------------------------------------#
    # Merge lote
    if not datapredios.empty and not datalote.empty:
        datamerge   = datalote.drop_duplicates(subset='barmanpre',keep='first')
        datapredios = datapredios.merge(datamerge[['barmanpre','wkt']],on='barmanpre',how='left',validate='m:1')
        
    #-------------------------------------------------------------------------#
    # Transacciones
    if not datatransacciones.empty and not datacatastro.empty and 'barmanpre' not in datatransacciones and 'prechip' in datatransacciones:
        datamerge         = datacatastro.drop_duplicates(subset='prechip',keep='first')
        datatransacciones = datatransacciones.merge(datamerge[['barmanpre','prechip']],on='prechip',how='left',validate='m:1')
    if 'barmanpre' not in datatransacciones: datatransacciones['barmanpre'] = None
    if not datatransacciones.empty:
        if isinstance(precuso,list) and precuso!=[]:
            datatransacciones = datatransacciones[datatransacciones['precuso'].isin(precuso)]
        elif isinstance(precuso,str) and precuso!='':
            datatransacciones = datatransacciones[datatransacciones['precuso'].isin([precuso])]
        datatransacciones = datatransacciones[datatransacciones['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
        if not datatransacciones.empty:
            datatransacciones['fecha_documento_publico'] = pd.to_datetime(datatransacciones['fecha_documento_publico'],errors='coerce')
            datatransacciones['cuantiamt2'] = datatransacciones['cuantia']/datatransacciones['preaconst']
            variables = ['barmanpre','fecha_documento_publico', 'matriculamatch','codigo', 'prechip', 'precuso', 'cuantia', 'cuantiamt2', 'preaconst', 'preaterre']
            variables = [x for x in variables if x in datatransacciones]
            datatransacciones = datatransacciones[variables]
            
    #-------------------------------------------------------------------------#
    # Vigencia
    if not datavigencia.empty:
        datavigencia = datavigencia.groupby(['chip','vigencia']).agg({'valorAutoavaluo':'max','valorImpuesto':'max'}).reset_index()
        datamerge    = datacatastro.drop_duplicates(subset=['prechip'],keep='first')
        datamerge.rename(columns={'prechip':'chip'},inplace=True)
        datavigencia = datavigencia.merge(datamerge[['chip','precuso','preaconst','preaterre']],on='chip',how='left',validate='m:1')
        datavigencia['avaluomt2']  = None
        datavigencia['predialmt2'] = None
        try: 
            datavigencia['avaluomt2']  = datavigencia['valorAutoavaluo']/datavigencia['preaconst']
            datavigencia['predialmt2'] = datavigencia['valorImpuesto']/datavigencia['preaconst']
        except: pass
        if isinstance(precuso,list) and precuso!=[]:
            datavigencia = datavigencia[datavigencia['precuso'].isin(precuso)]
        elif isinstance(precuso,str) and precuso!='':
            datavigencia = datavigencia[datavigencia['precuso'].isin([precuso])]
    
    #-------------------------------------------------------------------------#
    # Catastro
    if not datacatastro.empty:
        if isinstance(precuso,list) and precuso!=[]:
            datacatastro = datacatastro[datacatastro['precuso'].isin(precuso)]
        elif isinstance(precuso,str) and precuso!='':
            datacatastro = datacatastro[datacatastro['precuso'].isin([precuso])]
        variables = ['barmanpre','precuso','prechip','preaterre','preaconst','matriculainmobiliaria','prevetustz']
        variables = [x for x in variables if x in datacatastro]
        datacatastro = datacatastro[variables]
        
    
    #-------------------------------------------------------------------------#
    # Data Listings
    datamarket = pd.DataFrame()
    query      = ""
    usosuelo   = None
    if isinstance(precuso,list) and precuso!=[]:
        usosuelo = usosuelo2inmueble(precuso)
    elif isinstance(precuso,str) and precuso!='':
        usosuelo = usosuelo2inmueble([precuso])
        
    if isinstance(usosuelo,list) and usosuelo!=[]:
        usosuelolist  = '","'.join(usosuelo)
        query        += f' AND tipoinmueble IN ("{usosuelolist}")'
        
    if isinstance(polygon, str) and not 'none' in polygon.lower() and polygon!='':
        query += f' AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), geometry)'
        
    if query!="":
        query      = query.strip().strip('AND')
        datamarket = pd.read_sql_query(f"SELECT tipoinmueble,tiponegocio,areaconstruida,habitaciones,banos,garajes,valor FROM  bigdata.market_portales_activos WHERE {query}" , engine)
        if not datamarket.empty and 'valormt2' not in datamarket: 
            datamarket['valormt2'] = datamarket['valor']/datamarket['areaconstruida']
        datamarket = datamarket.drop_duplicates()
    
    return datapredios,datacatastro,datavigencia,datatransacciones,datamarket
