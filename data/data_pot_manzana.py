import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
from sqlalchemy import create_engine 

from data.getuso_destino import getuso_destino

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata_lectura"]
schema   = st.secrets["schema_bigdata"]
engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')


@st.cache_data(show_spinner=False)
def builddata(tratamiento=[],alturamin=0,actividad=[],actuacion=None):
    data_manzanas    = getmanzanas()
    data_tratamiento = gettratamiento(tratamiento,alturamin)
    data_actividad   = getactividad(actividad=actividad)
    data_barrios     = pd.DataFrame()
    
    # Tratamiento urbanistico
    if not data_manzanas.empty and not data_tratamiento.empty:
        data_manzanas = gpd.overlay(data_manzanas,data_tratamiento, how='intersection')
        if 'index_right' in data_manzanas: del data_manzanas['index_right']
    # Actividad
    if not data_manzanas.empty and not data_actividad.empty:
        data_manzanas = gpd.overlay(data_manzanas,data_actividad, how='intersection')
        if 'index_right' in data_manzanas: del data_manzanas['index_right']
    # Actuacion estrategica
    if isinstance(actuacion, str) and any([x for x in ['si','no'] if x in actuacion.lower()]):
        data_actuacion = getactuacion()
        if 'si' in actuacion.lower() and not data_actuacion.empty:
            data_manzanas = gpd.overlay(data_manzanas,data_actuacion, how='intersection')
        if 'no' in actuacion.lower() and not data_actuacion.empty:
            data_manzanas = gpd.sjoin(data_manzanas, data_actuacion, how="left", op="intersects")
            data_manzanas = data_manzanas[data_manzanas['isin'].isnull()]
            data_manzanas.drop(columns=['isin'],inplace=True)
    if 'index_right' in data_manzanas: del data_manzanas['index_right']
    
    if not data_manzanas.empty:
        data_manzanas.drop(columns=['geometry'],inplace=True)
        lista = "','".join(data_manzanas['scacodigo'].unique())
        query = f" AND scacodigo IN ('{lista}')"
        if query!="":
            query        = query.strip().strip('AND').strip()
            data_barrios = pd.read_sql_query(f"SELECT scacodigo,scanombre,ST_AsText(geometry) as wkt FROM {schema}.data_bogota_barriocatastro WHERE {query}" , engine)
            if not data_barrios.empty:
                data_barrios['geometry'] = gpd.GeoSeries.from_wkt(data_barrios['wkt'])
                data_barrios             = gpd.GeoDataFrame(data_barrios, geometry='geometry')
                data_barrios['geometry'] = data_barrios['geometry'].simplify(0.0001, preserve_topology=True)
                data_barrios['wkt']      = data_barrios['geometry'].apply(lambda x: x.wkt)
                data_barrios.drop(columns=['geometry'],inplace=True)
                data_barrios = pd.DataFrame(data_barrios)
    return data_manzanas,data_barrios


@st.cache_data(show_spinner=False)
def consolidacionlotesselected(polygon=None):
    data  = pd.DataFrame()
    if isinstance(polygon, str) and polygon.lower()!='none':
        query        = f' ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))'
        datausosuelo = pd.read_sql_query(f"SELECT distinct( barmanpre) as barmanpre FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        if not datausosuelo.empty:
            lista = "','".join(datausosuelo['barmanpre'].unique())
            query = f" lotcodigo IN ('{lista}')"
            data  = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)    
    
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        pol              = wkt.loads(polygon)
        idd              = data['geometry'].apply(lambda x: pol.contains(x))==True
        data             = data[idd]
        if not data.empty:
            data.drop(columns=['geometry'],inplace=True)
            data = pd.DataFrame(data)
    return data

@st.cache_data(show_spinner=False)
def getmanzanas():
    data = pd.read_sql_query(f"SELECT mancodigo,seccodigo as scacodigo, ST_AsText(geometry) as wkt FROM {schema}.data_bogota_manzana" , engine)
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
    return data
     
@st.cache_data(show_spinner=False)
def gettratamiento(tratamiento=[],alturamin=0):  
    data  = pd.DataFrame()
    query = ""
    if alturamin>0:
        query += f" AND (alturamax_num>={alturamin} OR alturamax_num IS NULL)"
    if isinstance(tratamiento, list) and tratamiento!=[]:
        lista  = "','".join(tratamiento)
        query += f" AND nombretra IN ('{lista}')"
    if query!="":
        query = query.strip().strip('AND').strip()
        data  = pd.read_sql_query(f"SELECT nombretra as tratamiento,tipologia,alturamax,alturamax_num,ST_AsText(geometry) as wkt FROM pot.bogota_tratamientourbanistico WHERE {query}" , engine)
        if not data.empty:
            data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
            data             = gpd.GeoDataFrame(data, geometry='geometry')
            data.drop(columns=['wkt'],inplace=True)
    return data

@st.cache_data(show_spinner=False)
def getactuacion():
    data = pd.read_sql_query("SELECT nombre as actuacion,priorizaci as priorizacion,ST_AsText(geometry) as wkt FROM pot.bogota_actuacionestrategica" , engine)
    data['isin'] = 1
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data.drop(columns=['wkt'],inplace=True)
    return data

@st.cache_data(show_spinner=False)
def getactividad(actividad=[]):
    data  = pd.DataFrame()
    query = ''
    if isinstance(actividad, list) and actividad!=[]:
        lista  = "','".join(actividad)
        query += f" AND nombreare IN ('{lista}')"
    if query!='':
        query = query.strip().strip('AND').strip()
        data  = pd.read_sql_query(f"SELECT nombreare as actividad,ST_AsText(geometry) AS wkt FROM  pot.bogota_areaactividad WHERE {query}" , engine)
        if not data.empty:
            data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
            data             = gpd.GeoDataFrame(data, geometry='geometry')
            data.drop(columns=['wkt'],inplace=True)
    return data

@st.cache_data(show_spinner=False)
def getmanzanasfromlatlng(latitud,longitud):
    datamanzana = pd.DataFrame()
    datalotes   = pd.DataFrame()
    query = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        query += f" AND ST_CONTAINS(geometry,Point({longitud},{latitud}))"
    if query!='':
        query = query.strip().strip('AND').strip()
        datamanzana = pd.read_sql_query(f"SELECT mancodigo FROM {schema}.data_bogota_manzana WHERE {query}" , engine)

    if not datamanzana.empty:
        query         ="barmanpre LIKE '"+"%' OR barmanpre LIKE '".join(datamanzana['mancodigo'].astype(str).unique())+"%'"
        databarmanpre = pd.read_sql_query(f"SELECT barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)
        if not databarmanpre.empty:
            lista     = "','".join(databarmanpre['barmanpre'].unique())
            query     = f" lotcodigo IN ('{lista}')"
            datalotes = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
    return datamanzana,datalotes

@st.cache_data(show_spinner=False)
def getscacodigofromlatlng(latitud,longitud):
    scacodigo = None
    query     = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        query = f" AND ST_CONTAINS(geometry,Point({longitud},{latitud}))"
    if query!='':
        query        = query.strip().strip('AND').strip()
        data_barrios = pd.read_sql_query(f"SELECT scacodigo FROM {schema}.data_bogota_barriocatastro WHERE {query}" , engine)
        if not data_barrios.empty:
            scacodigo = data_barrios['scacodigo'].iloc[0]
    return scacodigo

@st.cache_data(show_spinner=False)
def getmanzanadescripcion(mancodigo):
    if isinstance(mancodigo, str) and mancodigo!="":
        return pd.read_sql_query(f"SELECT * FROM {schema}.bogota_mancodigo_general WHERE mancodigo='{mancodigo}'" , engine)
    else: return pd.DataFrame()
    
    
@st.cache_data(show_spinner=False)
def getconfiguracionmanazana(mancodigo):
    data = pd.DataFrame()
    if isinstance(mancodigo, str) and mancodigo!="":
        query = f" barmanpre LIKE '{mancodigo}%'"
        data  = pd.read_sql_query(f"SELECT barmanpre,precuso,predios_precuso,preaconst_precuso,preaterre_precuso FROM {schema}.bogota_catastro_compacta_precuso WHERE {query}" , engine)
    if not data.empty:
        dataprecuso,dataprecdestin = getuso_destino()
        dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
        data = data.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        data = data.groupby(['usosuelo']).agg({'predios_precuso':'sum','preaconst_precuso':'sum','preaterre_precuso':'sum'}).reset_index()
        data.columns = ['usosuelo','predios_precuso','preaconst_precuso','preaterre_precuso']
    return data
