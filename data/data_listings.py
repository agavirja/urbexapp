import streamlit as st
import pandas as pd
import shapely.wkt as wkt
from sqlalchemy import create_engine 
from shapely.geometry import Polygon
from datetime import datetime
from dateutil.relativedelta import relativedelta

from data.coddir import coddir
from data.point2POT import main as point2POT
from data.datadane import main as censodane
from data.formato_direccion import formato_direccion
from data.inmuebleANDusosuelo import usosuelo2inmueble

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata_lectura"]
schema   = st.secrets["schema_bigdata"]
engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
@st.cache_data(show_spinner=False)
def listingsBypolygon(polygon=None,precuso=None):
    
    datamarketactivos,datamarkethistorico = [pd.DataFrame()]*2

    query  = ""
    if precuso is not None and isinstance(precuso, list):
        tipoinmueble = usosuelo2inmueble(precuso)
        tipoinmueble = "','".join(tipoinmueble)
        query       += f""" AND tipoinmueble IN ('{tipoinmueble}')"""
    
    if isinstance(polygon, str) and 'none' not in polygon.lower():
        query += f""" AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))"""
        
    if query!="":
        query               = query.strip().strip('AND').strip()
        datamarketactivos   = pd.read_sql_query(f"SELECT code,valor,tipoinmueble,tiponegocio,areaconstruida,fecha_inicial FROM bigdata.market_portales_activos WHERE {query}" , engine)
        datamarkethistorico = pd.read_sql_query(f"SELECT code,valor,tipoinmueble,tiponegocio,areaconstruida,fecha_inicial FROM bigdata.market_portales_historico WHERE {query}" , engine)
        
        if not datamarketactivos.empty:
            datamarketactivos['valormt2'] = datamarketactivos['valor']/datamarketactivos['areaconstruida']

        if not datamarkethistorico.empty:
            datamarkethistorico['valormt2'] = datamarkethistorico['valor']/datamarkethistorico['areaconstruida']

    return datamarketactivos,datamarkethistorico

@st.cache_data(show_spinner=False)
def buildingMarketValues(direccion,precuso=None,mpioccdgo=None):
    
    datamarket = pd.DataFrame()
    query      = ""
    if isinstance(direccion, list):
        for i in direccion:
            query += f" OR coddir LIKE '{coddir(i)}%'"
        if query!="":
            query = query.strip().strip('OR').strip()
            query = f' AND ({query})'
    elif isinstance(direccion, str):
        query += f" AND coddir LIKE '{coddir(direccion)}%'"
    
    if precuso is not None and isinstance(precuso, list):
        tipoinmueble = usosuelo2inmueble(precuso)
        tipoinmueble = "','".join(tipoinmueble)
        query       += f" AND tipoinmueble IN ('{tipoinmueble}')"
    
    if mpioccdgo is not None and isinstance(mpioccdgo, str):
        query += f" AND mpio_ccdgo='{mpioccdgo}'"
        
    if query!="":
        query               = query.strip().strip('AND').strip()
        datamarketactivos   = pd.read_sql_query(f"SELECT code,valor,tipoinmueble,tiponegocio,direccion,areaconstruida,valoradministracion,url_img,habitaciones,banos,garajes FROM bigdata.market_portales_activos WHERE {query}" , engine)
        datamarkethistorico = pd.read_sql_query(f"SELECT code,valor,tipoinmueble,tiponegocio,direccion,areaconstruida,valoradministracion,url_img,habitaciones,banos,garajes FROM bigdata.market_portales_historico WHERE {query}" , engine)
        
        # Eliminar los inmuebles activos de la data historica para el analisis
        idd                 = datamarkethistorico['code'].isin(datamarketactivos['code'])
        datamarkethistorico = datamarkethistorico[~idd]
        
        #---------------------------------------------------------------------#
        # Ofertas en el mismo barmanpre
        if not datamarketactivos.empty:
            datamarketactivos['valormt2'] = datamarketactivos['valor']/datamarketactivos['areaconstruida']
            datamarketactivos['tipo']     = 'activos'
            datamarket = pd.concat([datamarket,datamarketactivos])

        if not datamarkethistorico.empty:
            datamarkethistorico['valormt2'] = datamarkethistorico['valor']/datamarkethistorico['areaconstruida']
            datamarkethistorico['tipo']     = 'historico'
            datamarket = pd.concat([datamarket,datamarkethistorico])
            
    return datamarket


@st.cache_data(show_spinner=False)
def listingsPolygonActive(polygon=None, tipoinmueble=None, tiponegocio=None, areamin=0, areamax=0, valormin=0, valormax=0, habitacionesmin=0, habitacionesmax=0, banosmin=0, banosmax=0, garajesmin=0, garajesmax=0):

    datamarket = pd.DataFrame()
    if tipoinmueble is not None and tiponegocio is not None:
        query = ''
        if isinstance(tipoinmueble, str): query += f" AND tipoinmueble='{tipoinmueble}'"
        if isinstance(tiponegocio, str): query += f" AND tiponegocio='{tiponegocio}'"
        if areamin > 0:         query += f" AND areaconstruida >= {areamin}"
        if areamax > 0:         query += f" AND areaconstruida <= {areamax}"
        if valormin > 0:        query += f" AND valor >= {valormin}"
        if valormax > 0:        query += f" AND valor <= {valormax}"
        if habitacionesmin > 0: query += f" AND habitaciones >= {habitacionesmin}"
        if habitacionesmax > 0: query += f" AND habitaciones <= {habitacionesmax}"
        if banosmin > 0:        query += f" AND banos >= {banosmin}"
        if banosmax > 0:        query += f" AND banos <= {banosmax}"
        if garajesmin > 0:      query += f" AND garajes >= {garajesmin}"
        if garajesmax > 0:      query += f" AND garajes <= {garajesmax}"

        if isinstance(polygon, str) and 'none' not in polygon.lower():
            query += f""" AND ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))"""

        if query!="":
            query      = query.strip().strip('AND').strip()
            datamarket = pd.read_sql_query(f"SELECT * FROM bigdata.market_portales_activos WHERE {query}" , engine)
            if not datamarket.empty:
                datamarket['valormt2'] = datamarket['valor']/datamarket['areaconstruida']
    return datamarket
