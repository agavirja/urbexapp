import streamlit as st
import pandas as pd
import geopandas as gpd
import json
from geopy.distance import geodesic
from sqlalchemy import create_engine 
from shapely.geometry import Point
from shapely import wkt

from functions.read_data import execute_query,execute_listing_code_query
from data._principal_lotes import datalote 
from data._principal_caracteristicas import datacaracteristicas


@st.cache_data(show_spinner=False)
def datacodelistings(grupo=None, variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    data     = pd.DataFrame()
    if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
        grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        if len(grupo)>500:
            data = execute_query(grupo, 'bogota_barmanpre_listings', variables=variables, chunk_size=500)
        else:
            lista  = ",".join(grupo)
            query  = f" grupo IN ({lista})"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_barmanpre_listings WHERE {query}", engine)
            engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def datalistings(code=None):
    variables = '`code`,`listings`'
    user      = st.secrets["user_write_urbex"]
    password  = st.secrets["password_write_urbex"]
    host      = st.secrets["host_read_urbex"]
    schema    = st.secrets["schema_write_urbex"]
    data      = pd.DataFrame()
    resultado = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code'])
    if isinstance(code,str) and code!='':
        code = code.split('|')
    elif isinstance(code,(float,int)):
        code = [f'{code}']
    if isinstance(code,list) and code!=[]:
        code = list(map(str, code))
        if len(code)>500:
            data = execute_listing_code_query(code, 'bogota_bycode_listings', variables=variables, chunk_size=500)
        else:
            lista  = "','".join(code)
            query  = f" `code` IN ('{lista}')"
            engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            data   = pd.read_sql_query(f"SELECT {variables} FROM bigdata.bogota_bycode_listings WHERE {query}", engine)
            engine.dispose()
            
    if not data.empty:
        variable     = 'listings'
        df           = data[data[variable].notnull()]
        df[variable] = df[variable].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df           = df[df[variable].notnull()]
        df           = df.explode(variable)
        df           = df.apply(lambda x: {**(x[variable]), 'code': x['code']}, axis=1)
        df           = pd.DataFrame(df,columns=['formato'])
        df           = pd.json_normalize(df['formato'])
        resultado    = df.copy()
    return resultado

@st.cache_data(show_spinner=False)
def data_ligtinsgs_barmanpre(grupo=None,inputvar={}):
    datacode    = datacodelistings(grupo=grupo, variables='code_activo_barmanpre,code_desactivado_barmanpre')
    data        = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code', 'direccion'])
    resultado   = {'listings_data':{'label':'','value':None},
                   'listings_estadisticas':{'label':'','value':None},
                   }

    listingcode = []
    for variable in ['code_activo_barmanpre','code_desactivado_barmanpre']:
        if not datacode.empty and variable in datacode:
            datapaso = datacode[datacode[variable].notnull()]
            for _,items in datapaso.iterrows():
                listingcode += items[variable].split('|')
                
    if isinstance(listingcode,list) and listingcode!=[]:
        listingcode = list(set(listingcode))
        data        = datalistings(code=listingcode)
    
    if not data.empty:
        data['valor']            = pd.to_numeric(data['valor'],errors='coerce')  if 'valor' in data else None
        data['areaconstruida']   = pd.to_numeric(data['areaconstruida'],errors='coerce') if 'areaconstruida' in data else None
        data['valormt2']         = None
        idd                      = (data['valor']>0) & (data['areaconstruida']>0)
        data.loc[idd,'valormt2'] = data.loc[idd,'valor']/data.loc[idd,'areaconstruida'] 

        datagroup         = data.groupby(['tipoinmueble','tiponegocio']).agg({'valormt2':['median','count']}).reset_index()
        datagroup.columns = ['tipoinmueble','tiponegocio','valormt2','listings']
        datagroup         = datagroup.to_dict(orient='records')
        resultado.update({'listings_estadisticas':{'label':'','value':datagroup}})
        resultado.update({'listings_data':{'label':'','value':data.to_dict(orient='records')}})
    return resultado

@st.cache_data(show_spinner=False)
def data_ligtinsgs_radio(grupo=None,inputvar={}):
    datacode    = datacodelistings(grupo=grupo, variables='code_activo_radio')
    data        = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code'])
    resultado   = {'listings_estadisticas':{'label':'','value':None}}
    listingcode = []
    for variable in ['code_activo_radio']:
        if not datacode.empty and variable in datacode:
            datapaso = datacode[datacode[variable].notnull()]
            for _,items in datapaso.iterrows():
                listingcode += items[variable].split('|')
                
    if isinstance(listingcode,list) and listingcode!=[]:
        listingcode = list(set(listingcode))
        data        = datalistings(code=listingcode)
        
    if not data.empty:
        datalot = datalote(grupo=grupo)
        if not datalot.empty and 'latitud' in datalot and 'longitud' in datalot:
            latref  = datalot['latitud'].iloc[0]
            lngref  = datalot['longitud'].iloc[0]
            data['distancia'] = data.apply(lambda x: calcular_distancia(x['latitud'],x['longitud'],latref,lngref),axis=1)

    # Filtros
    data = listings_filter(data,inputvar=inputvar)

    if not data.empty: 
        data['valor']            = pd.to_numeric(data['valor'],errors='coerce')  if 'valor' in data else None
        data['areaconstruida']   = pd.to_numeric(data['areaconstruida'],errors='coerce') if 'areaconstruida' in data else None
        data['valormt2']         = None
        idd                      = (data['valor']>0) & (data['areaconstruida']>0)
        data.loc[idd,'valormt2'] = data.loc[idd,'valor']/data.loc[idd,'areaconstruida'] 

        datagroup         = data.groupby(['tipoinmueble','tiponegocio']).agg({'valormt2':['median','count']}).reset_index()
        datagroup.columns = ['tipoinmueble','tiponegocio','valormt2','listings']
        datamerge         =  data.groupby(['tipoinmueble','tiponegocio'])['code'].agg(lambda x: '|'.join(x)).reset_index()
        datamerge.columns = ['tipoinmueble','tiponegocio','code']
        datagroup         = datagroup.merge(datamerge,on=['tipoinmueble','tiponegocio'],how='left',validate='1:1')
        datagroup         = datagroup.to_dict(orient='records')
        resultado.update({'listings_estadisticas':{'label':'','value':datagroup}})
    return resultado

@st.cache_data(show_spinner=False)
def datalistingsbarrio(scacodigo=None,grupo=None,variables='*'):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data = pd.DataFrame()
    
    if scacodigo is None:
        if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
            grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
        if isinstance(grupo,str) and grupo!='':
            grupo = grupo.split('|')
        elif isinstance(grupo,(float,int)):
            grupo = [f'{grupo}']
        if isinstance(grupo,list) and grupo!=[]:
            grupo = list(map(str, grupo))
            datascacodigo = datacaracteristicas(grupo=grupo)
            try: 
                scacodigo = json.loads(datascacodigo['general_catastro'].iloc[0])[0]['precbarrio']
            except: pass
    if isinstance(scacodigo,str):
        query = f'scacodigo = "{scacodigo}"'
        data  = pd.read_sql_query(f"SELECT {variables} FROM  bigdata.bogota_barrio_listings WHERE {query}" , engine)
    engine.dispose()
    return data

@st.cache_data(show_spinner=False)
def data_listings_polygon(polygon=None,inputvar={}):
    
    data  = get_listings_from_polygon(polygon=polygon)
    data  = listings_filter(data,inputvar=inputvar)

    return data
    
@st.cache_data(show_spinner=False)
def get_listings_from_polygon(polygon=None):
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    
    data        = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code'])
    datacodigos = pd.DataFrame()
    polygon     = polygon if isinstance(polygon,str) and polygon!='' and not 'none' in polygon.lower() else None
    
    if polygon is not None:
        engine        = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        datacodigos   = pd.read_sql_query(f"SELECT distinct(code) as code FROM bigdata.bogota_bycode_listings_geometry WHERE ST_Contains(ST_GeomFromText('{polygon}'),geometry)", engine)
        engine.dispose()
        
    if not datacodigos.empty:
        listingcode = list(set(datacodigos['code']))
        data        = datalistings(code=listingcode)

    if not data.empty: 
        data['valor']            = pd.to_numeric(data['valor'],errors='coerce')  if 'valor' in data else None
        data['areaconstruida']   = pd.to_numeric(data['areaconstruida'],errors='coerce') if 'areaconstruida' in data else None
        data['valormt2']         = None
        idd                      = (data['valor']>0) & (data['areaconstruida']>0)
        data.loc[idd,'valormt2'] = data.loc[idd,'valor']/data.loc[idd,'areaconstruida'] 

        try:
            data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
            data             = gpd.GeoDataFrame(data, geometry='geometry')
            polygon          = wkt.loads(polygon)
            data             = data[data['geometry'].apply(lambda x: polygon.contains(x))]
        except: pass
    
        if 'geometry' in data:
            data.drop(columns=['geometry'],inplace=True)
            data = pd.DataFrame(data)
            
    return data
    
#-----------------------------------------------------------------------------#
def calcular_distancia(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters

def listings_filter(data,inputvar={}):
    
    tipoinmueble    = inputvar['tipoinmueble'] if 'tipoinmueble' in inputvar and isinstance(inputvar['tipoinmueble'], list) else []
    tiponegocio     = inputvar['tiponegocio'] if 'tiponegocio' in inputvar and isinstance(inputvar['tiponegocio'], list) else [] 
    areamin         = inputvar['areamin'] if 'areamin' in inputvar and isinstance(inputvar['areamin'], (int, float)) else 0 
    areamax         = inputvar['areamax'] if 'areamax' in inputvar and isinstance(inputvar['areamax'], (int, float)) else 0 
    habitacionesmin = inputvar['habitacionesmin'] if 'habitacionesmin' in inputvar and isinstance(inputvar['habitacionesmin'], int) else 0 
    habitacionesmax = inputvar['habitacionesmax'] if 'habitacionesmax' in inputvar and isinstance(inputvar['habitacionesmax'], int) else 0 
    banosmin        = inputvar['banosmin'] if 'banosmin' in inputvar and isinstance(inputvar['banosmin'], int) else 0 
    banosmax        = inputvar['banosmax'] if 'banosmax' in inputvar and isinstance(inputvar['banosmax'], int) else 0 
    garajesmin      = inputvar['garajesmin'] if 'garajesmin' in inputvar and isinstance(inputvar['garajesmin'], int) else 0 
    garajesmax      = inputvar['garajesmax'] if 'garajesmax' in inputvar and isinstance(inputvar['garajesmax'], int) else 0 
    valormin        = inputvar['valormin'] if 'valormin' in inputvar and isinstance(inputvar['valormin'], (int,float)) else 0 
    valormax        = inputvar['valormax'] if 'valormax' in inputvar and isinstance(inputvar['valormax'], (int,float)) else 0 
    metros          = inputvar['metros'] if 'metros' in inputvar and isinstance(inputvar['metros'], (int, float)) else None 

    if not data.empty: 
        
        # Filtro por area 
        if areamin>0 and 'areaconstruida' in data:
            data = data[data['areaconstruida']>=areamin]
        if areamax>0 and 'areaconstruida' in data:
            data = data[data['areaconstruida']<=areamax]
          
        # Filtro por habitaciones 
        if habitacionesmin>0 and 'habitaciones' in data:
            data = data[data['habitaciones']>=habitacionesmin]
        if habitacionesmax>0 and 'habitaciones' in data:
            data = data[data['habitaciones']<=habitacionesmax]
          
        # Filtro por banos 
        if banosmin>0 and 'banos' in data:
            data = data[data['banos']>=banosmin]
        if banosmax>0 and 'banos' in data:
            data = data[data['banos']<=banosmax]
            
        # Filtro por garajes 
        if garajesmin>0 and 'garajes' in data:
            data = data[data['garajes']>=garajesmin]
        if garajesmax>0 and 'garajes' in data:
            data = data[data['garajes']<=garajesmax]
            
        # Filtro por valor 
        if valormin>0 and 'valor' in data:
            data = data[data['valor']>=valormin]
        if valormax>0 and 'valor' in data:
            data = data[data['valor']<=valormax]
            
        # Filtro por distancia 
        if isinstance(metros,(int,float)) and metros>0 and 'distancia' in data:
            data = data[data['distancia']<=metros]
            
        # Filtro por tipoinmueble:
        if isinstance(tipoinmueble,list) and tipoinmueble!=[] and 'tipoinmueble' in data:
            data = data[data['tipoinmueble'].isin(tipoinmueble)]
            
        # Filtro por tipo de negocio:
        if isinstance(tiponegocio,list) and tiponegocio!=[] and 'tiponegocio' in data:
            data = data[data['tiponegocio'].isin(tiponegocio)]
            
        if 'fecha_inicial' in data:
            data['fecha_inicial'] = pd.to_datetime(data['fecha_inicial'], unit='ms')
            filtro_fecha          = pd.Timestamp.today() - pd.DateOffset(months=12)
            data                  = data[data['fecha_inicial'].between(filtro_fecha, pd.Timestamp.today())]
            data['year']          = data['fecha_inicial'].apply(lambda x: x.year)
            
    return data
