import streamlit as st
import pandas as pd
import geopandas as gpd
import geojson
from sqlalchemy import create_engine 
from area import area as areapolygon
from shapely.ops import unary_union

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    polygon        = inputvar['polygon'] if 'polygon' in inputvar and isinstance(inputvar['polygon'], str) else None
    pot            = inputvar['pot']  if 'pot'  in inputvar else []
    areamin        = inputvar['areamin'] if 'areamin' in inputvar else 0
    areamax        = inputvar['areamax'] if 'areamax' in inputvar else 0
    antiguedadmin  = inputvar['antiguedadmin'] if 'antiguedadmin' in inputvar else 0
    antiguedadmax  = inputvar['antiguedadmax'] if 'antiguedadmax' in inputvar else 0
    loteesquinero  = inputvar['loteesquinero'] if 'loteesquinero' in inputvar else None
    viaprincipal   = inputvar['viaprincipal']  if 'viaprincipal'  in inputvar else None
    frente         = inputvar['frente'] if 'frente' in inputvar else 0
    maxpredios     = inputvar['maxpredios'] if 'maxpredios' in inputvar else 0
    maxpropietario = inputvar['maxpropietario'] if 'maxpropietario' in inputvar else 0
    maxavaluo      = inputvar['maxavaluo'] if 'maxavaluo' in inputvar else 0
    maxpiso        = inputvar['maxpiso'] if 'maxpiso' in inputvar else 0
    usodelsuelo    = inputvar['usodelsuelo'] if 'usodelsuelo' in inputvar else None
    
    datapredios       = pd.DataFrame()
    datalotescatastro = pd.DataFrame()  
    
    if isinstance(polygon, str):
        
        datapredios = pd.read_sql_query(f"SELECT *  FROM  bigdata.bogota_lotes_general WHERE ST_CONTAINS(ST_GEOMFROMTEXT('{polygon}'), geometry)" , engine)
        if 'geometry' in datapredios: del datapredios['geometry']
        if areamax>0:
            datapredios['preaterre'] = pd.to_numeric(datapredios['preaterre'],errors='coerce')
            datapredios = datapredios[(datapredios['preaterre']<=areamax) | (datapredios['preaterre'].isnull())]
        if maxpiso>0:
            datapredios['connpisos'] = pd.to_numeric(datapredios['connpisos'],errors='coerce')
            datapredios = datapredios[(datapredios['connpisos']<=maxpiso) | (datapredios['connpisos'].isnull())]
        if maxpropietario>0:
            datapredios['propietarios'] = pd.to_numeric(datapredios['propietarios'],errors='coerce')
            datapredios = datapredios[(datapredios['propietarios']<=maxpropietario) | (datapredios['propietarios'].isnull())]
        if maxavaluo>0:
            datapredios['avaluocatastral'] = pd.to_numeric(datapredios['avaluocatastral'],errors='coerce')
            datapredios = datapredios[(datapredios['avaluocatastral']<=maxavaluo) | (datapredios['avaluocatastral'].isnull())]
            
        if pot is not None and pot!=[]:
            for items in pot:
                #-------------------------------------------------------------#
                # Tratamiento urbanistico
                if 'tipo' in items and 'tratamientourbanistico' in items['tipo']:
                    if 'alturaminpot' in items and items['alturaminpot']>0:
                        datapredios['alturamax_tratamientourbanistico'] = pd.to_numeric(datapredios['alturamax_tratamientourbanistico'],errors='coerce')
                        datapredios = datapredios[(datapredios['alturamax_tratamientourbanistico']>=items['alturaminpot']) | (datapredios['alturamax_tratamientourbanistico'].isnull())]
                    if 'tratamiento' in items and items['tratamiento']!=[]:
                        datapredios = datapredios[datapredios['nombretra_tratamientourbanistico'].isin(items['tratamiento'])]

                #-------------------------------------------------------------#
                # Area de actividad
                if 'tipo' in items and 'areaactividad' in items['tipo']:
                    if 'nombreare' in items and items['nombreare']!=[]:
                        datapredios = datapredios[datapredios['nombreare_areaactividad'].isin(items['nombreare'])]

                #-------------------------------------------------------------#
                # Actuacion Estrategica
                if 'tipo' in items and 'actuacionestrategica' in items['tipo']:
                    if 'isin' in items and any([w for w in ['si','no'] if w in items['isin'].lower()]):
                        if 'si' in items['isin'].lower():
                            datapredios = datapredios[datapredios['nombre_actuacionestrategica'].notnull()]
                        elif 'no' in items['isin'].lower():
                            datapredios = datapredios[datapredios['nombre_actuacionestrategica'].isnull()]

    if not datapredios.empty:
        
        #-----------------------------------------------------------------#
        # Merge polygons
        query = "','".join(datapredios['barmanpre'].unique())
        query = f" barmanpre IN ('{query}')"   
        databarmanpre = pd.read_sql_query(f"SELECT distinct(barmanpre) as barmanpre FROM  bigdata.data_bogota_catastro WHERE {query} AND ( precdestin<>'65' AND precdestin<>'66')" , engine)

        if not databarmanpre.empty:
            query = "','".join(databarmanpre['barmanpre'].unique())
            query = f" lotcodigo IN ('{query}')"   
            datalotescatastro = pd.read_sql_query(f"SELECT lotcodigo as barmanpre, ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_lotes WHERE {query}" , engine)
            datalotescatastro = datalotescatastro.drop_duplicates(subset='barmanpre',keep='first')
    
    # Identificar que lotes estan solos o colindan con otro que cumple condiciones
    if not datalotescatastro.empty:
        datapaso             = datalotescatastro.copy()
        datapaso['geometry'] = gpd.GeoSeries.from_wkt(datapaso['wkt'])
        datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
        datapaso['idunique'] = 0 
        datapaso.index       = range(len(datapaso))
        
        for ilote in range(len(datapaso)):
            poly = datapaso['geometry'].iloc[ilote]
            idd  = (datapaso['geometry'].apply(lambda x: x.intersects(poly) and
                    has_two_or_more_common_points(x, poly) and
                    not poly.contains(x)))
            if sum(idd)==0:
                datapaso.loc[ilote,'idunique'] = 1
        
        datapaso = datapaso[datapaso['idunique']==1]
        if not datapaso.empty:
            if areamin>0: 
                datapredios['preaterre'] = pd.to_numeric(datapredios['preaterre'],errors='coerce')
                idd         = (datapredios['barmanpre'].isin(datapaso['barmanpre'])) & (datapredios['preaterre']<areamin)
                datapredios = datapredios[~idd]
        datalotescatastro = datalotescatastro[datalotescatastro['barmanpre'].isin(datapredios['barmanpre'])]

    # Seleccionar aquellos lotes que al menos en conglomeracion total tiene al menos el area minima requerida
    if not datapredios.empty and not datalotescatastro.empty and areamin>0:
        datapredios,datalotescatastro = multipolygonsUnion(datapredios,datalotescatastro,areamin)
        
    if not datalotescatastro.empty and not datapredios.empty:
        idd = datapredios['barmanpre'].isin(datalotescatastro['barmanpre'])
        if sum(idd)>0:
            datapredios = datapredios[idd]
        datamerge = datapredios[['barmanpre','prenbarrio','preaconst','preaterre','estrato','predios','connpisos','connsotano','avaluocatastral','propietarios','nombretra_tratamientourbanistico']]
        datamerge = datamerge.drop_duplicates(subset='barmanpre',keep='first')
        datalotescatastro = datalotescatastro.merge(datamerge,on='barmanpre',how='left',validate='m:1')
        
    engine.dispose()
    return datapredios,datalotescatastro

def has_two_or_more_common_points(poly1, poly2):
    try: return len(set(poly1.boundary.coords).intersection(poly2.boundary.coords)) >= 2
    except: return False
    
@st.cache_data(show_spinner=False)
def multipolygonsUnion(datapredios,datalotescatastro,areamin):
    try:
        datapaso             = datalotescatastro.copy()
        datapaso['geometry'] = gpd.GeoSeries.from_wkt(datapaso['wkt'])
        datapaso             = gpd.GeoDataFrame(datapaso, geometry='geometry')
        multipolygon         = unary_union(datapaso['geometry'].to_list())
        try:
            polygons             = list(multipolygon.geoms)
            datapolygons         = pd.DataFrame(polygons,columns=['geometry'])
            datapolygons         = gpd.GeoDataFrame(datapolygons, geometry='geometry')
        
            datapolygons['areapolygon'] = datapolygons['geometry'].apply(lambda x: getareapolygon(x))
            datapolygons = datapolygons[datapolygons['areapolygon']>=areamin]
            datapolygons['id'] = 1
        
            datapaso = gpd.sjoin(datapaso, datapolygons, how="left", op="intersects")
            datapaso = datapaso[datapaso['id']==1]
            datalotescatastro = datalotescatastro[datalotescatastro['barmanpre'].isin(datapaso['barmanpre'])]
            datapredios       = datapredios[datapredios['barmanpre'].isin(datapaso['barmanpre'])]
        except:
            if getareapolygon(multipolygon)<areamin:
                datapredios,datalotescatastro = [pd.DataFrame()]*2
    except: pass
    return datapredios,datalotescatastro

def getareapolygon(polygon):
    try:
        geojson_polygon = geojson.dumps(polygon)
        return areapolygon(geojson_polygon)
    except: return None
