import streamlit as st
import pandas as pd
import json
import re
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sqlalchemy import create_engine 
from datetime import datetime

from data._principal_prediales import dataprediales
from data._principal_propietarios_v1 import datapropietarios


def main(polygon=None,grupo=None,inputvar={}):
    
    #-------------------------------------------------------------------------#
    # Ids de propietarios por poligono
    datapredios = pd.DataFrame()
    if isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        datapredios,grupo = ByPolygon(polygon=polygon)
        
    #-------------------------------------------------------------------------#
    # Datos
    data = byId(grupo=grupo, data=datapredios)

    if not data.empty and isinstance(inputvar,dict) and inputvar!={}:
        
        tipopropietario = inputvar['tipopropietario'] if 'tipopropietario' in inputvar and isinstance(inputvar['tipopropietario'],str) else None  # ['PERSONA NATURAL', 'PERSONA JURIDICA']
        precuso         = inputvar['precuso'] if 'precuso' in inputvar and isinstance(inputvar['precuso'],list) else []
        propiedades     = inputvar['propiedades'] if 'propiedades' in inputvar and isinstance(inputvar['propiedades'],(int,float)) else 1
        areamin         = inputvar['areamin'] if 'areamin' in inputvar and isinstance(inputvar['areamin'],(int,float)) else 0
        areamax         = inputvar['areamax'] if 'areamax' in inputvar and isinstance(inputvar['areamax'],(int,float)) else 0
        valormin        = inputvar['valormin'] if 'valormin' in inputvar and isinstance(inputvar['valormin'],(int,float)) else 0
        valormax        = inputvar['valormax'] if 'valormax' in inputvar and isinstance(inputvar['valormax'],(int,float)) else 0
        hacecuanto      = inputvar['hacecuanto'] if 'hacecuanto' in inputvar and isinstance(inputvar['hacecuanto'],(int,float)) else 0
        actuales        = inputvar['actuales'] if 'actuales' in inputvar and isinstance(inputvar['actuales'],str) else None # Actual propietario
        edadmin         = inputvar['edadmin'] if 'edadmin' in inputvar and isinstance(inputvar['edadmin'],(int,float)) else 0
        edadmax         = inputvar['edadmax'] if 'edadmax' in inputvar and isinstance(inputvar['edadmax'],(int,float)) else 0
        credito         = inputvar['credito'] if 'credito' in inputvar and isinstance(inputvar['credito'],str) else None
        
        # Filtro por: tipo de propietario
        if tipopropietario is not None and 'tod' not in tipopropietario.lower():
            data = data[data['tipoPropietario']==tipopropietario]
            
        # Filtro por: Numero de propiedades
        if propiedades is not None and isinstance(propiedades,int) and propiedades>1 and 'propiedades' in data:
            data = data[data['propiedades']>=propiedades]
            
        # Filtro por: areamin
        if areamin>0:
            data = data[data['areamin']>=areamin]
            
        # Filtro por: areamax
        if areamin>0:
            data = data[data['areamax']<=areamax]

        # Filtro por: valor min
        if valormin>0:
            data = data[data['valor']>=valormin]

        # Filtro por: valor min
        if valormax>0:
            data = data[data['valor']<=valormax]
            
        # Filtro por: valor min
        if hacecuanto>0 and 'minyear' in data:
            data = data[data['minyear']>=(datetime.now().year-hacecuanto)]
            
        # Filtro por: Propietarios actuales
        if isinstance(actuales,str) and 'maxyear' in data:
            if 'si' in actuales.lower():
                data = data[data['maxyear']>=(datetime.now().year-1)]
            elif 'no' in actuales.lower():
                data = data[data['maxyear']<=datetime.now().year]
                
        # Filtro por: edad min 
        if 'fechaDocumento' in data:
            try:
                data['edad'] = data['fechaDocumento'].apply(lambda x: x.year-18)
                data['edad'] = data['edad'].apply(lambda x: datetime.now().year-x)
                data['edad'] = pd.to_numeric(data['edad'],errors='coerce')
            except: pass
        
        if edadmin>0 and 'edad' in data:
            data = data[data['edad']>=edadmin]

        # Filtro por: edad max 
        if edadmax>0 and 'edad' in data:
            data = data[data['edad']<=edadmax]
            
        # Filtro por: credito actual
        if isinstance(credito,str) and 'credito' in data:
            if 'si' in credito.lower():
                data = data[data['credito']==True]
            elif 'no' in actuales.lower():
                data = data[data['credito']!=True]
                
        # Filtro por: credito actual
        if isinstance(precuso,list) and precuso!=[] and 'precuso' in data:
            data['idmerge'] = range(len(data))
            df   = data.copy()
            df   = df.assign(precuso=df['precuso'].str.split('|')).explode('precuso').reset_index(drop=True)
            df   = df[df['precuso'].isin(precuso)]
            data = data[data['idmerge'].isin(df['idmerge'])]
            data.drop(columns=['idmerge'],inplace=True)
            
            
    #-------------------------------------------------------------------------#
    # Mapa de calor de propietarios
    datalotes = pd.DataFrame(columns=['grupo', 'identificacion', 'color', 'wkt'])
    if not datapredios.empty:
        w           = datapredios.groupby(['grupo','chip'])['year'].max().reset_index()
        w.columns   = ['grupo','chip','maxyear']
        datapredios = datapredios.merge(w,on=['grupo','chip'],how='left',validate='m:1')
        datapaso    = datapredios[datapredios['year']==datapredios['maxyear']]
        idd         = datapaso['identificacion'].isin(data['numero'])
        datapaso    = datapaso[idd]
        
        datapaso    = datapaso.drop_duplicates(subset=['grupo','identificacion'],keep='first')
        datapaso    = datapaso.groupby('grupo')['identificacion'].count().reset_index()

        datapaso['rank']  = datapaso['identificacion'].rank(method='min')
        datapaso['rank']  = (datapaso['rank'] - datapaso['rank'].min()) / (datapaso['rank'].max() - datapaso['rank'].min())
        cmap              = plt.cm.Blues
        datapaso['color'] = datapaso['rank'].apply(lambda x: mcolors.to_hex(cmap(x)))
        datapaso.drop(columns=['rank'],inplace=True)
        
        grupo   = list(datapaso['grupo'].unique())
        datawkt = getWKTfromgrupo(grupo=grupo)
        if not datawkt.empty:
            datapaso = datapaso.merge(datawkt,on='grupo',how='left',validate='m:1')
        datalotes = datapaso.copy()
    
    return data,datalotes
            
@st.cache_data(show_spinner=False)
def ByPolygon(polygon=None):
    
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    lista    = []
    data     = pd.DataFrame()
    
    #-------------------------------------------------------------------------#
    # Lotes por poligono
    if isinstance(polygon, str) and polygon!='' and not 'none' in polygon.lower():
        query     = f' ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"),POINT(longitud,latitud))'
        datagrupo = pd.read_sql_query(f"SELECT distinct(grupo) as grupo FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)
        if not datagrupo.empty:
            grupo = list(datagrupo['grupo'].unique())
            data  = getprediales(grupo=grupo)
            lista = list(data[data['identificacion'].notnull()]['identificacion'].unique())
    engine.dispose()
    return data,lista
        
@st.cache_data(show_spinner=False)      
def byId(grupo=None,data=pd.DataFrame()):

    dataresult = pd.DataFrame(columns=['tipo','numero'])
    
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo             = list(map(str, grupo))
        data_propietarios = datapropietarios(identificacion=grupo)
        
        # Informacion de propietarios
        item = 'propietario'
        if not data_propietarios.empty:
            df         = data_propietarios[data_propietarios[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'tipo': x['tipo'], 'numero': x['numero']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
            if not df.empty:
                df         = infoinput(df)
                dataresult = dataresult.merge(df[['tipo', 'numero','tipoPropietario','nombre', 'email','fechaDocumento','telefonos']],on=['tipo','numero'],how='outer')
                if 'fechaDocumento' in dataresult:
                    dataresult['fechaDocumento'] = pd.to_datetime(dataresult['fechaDocumento'], unit='ms')
                    
        # Informacion de propiedades
        item = 'propiedades_shd'
        if not data_propietarios.empty:
            df         = data_propietarios[data_propietarios[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'tipo': x['tipo'], 'numero': x['numero']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])   
                
            if not df.empty and 'email' in df:
                datapaso = pd.DataFrame()
                if not dataresult.empty and 'email' in dataresult:
                    datapaso = pd.concat([dataresult[['tipo','numero','email']],df[['tipo','numero','email']]])
                    dataresult.drop(columns=['email'],inplace=True)
                else:
                    datapaso = df.copy()
                    
                datapaso          = datapaso.assign(email=datapaso['email'].str.split('|')).explode('email').reset_index(drop=True)
                datapaso          = datapaso.explode('email')
                datapaso['email'] = datapaso['email'].apply(lambda x: x.strip() if isinstance(x,str) and x!='' else None)
                datapaso          = datapaso.drop_duplicates(subset=['tipo','numero','email'])
                datapaso          = datapaso.groupby(['tipo','numero'])['email'].apply(lambda row: ' | '.join(str(email).lower() for email in row.dropna().unique() if '@' in str(email))).reset_index()
                datapaso.columns  = ['tipo','numero','email']
                dataresult        = dataresult.merge(datapaso,on=['tipo','numero'],how='left',validate='m:1')
                
            if not df.empty:
                df         = df.sort_values(by=['chip','year','tipo','numero','avaluo_catastral'],ascending=False).drop_duplicates(subset=['chip','tipo','numero'],keep='first')
                datapaso   = df.groupby(['tipo','numero']).agg({'chip':'nunique','preaconst':['min','max'],'avaluo_catastral':'sum','year':['min','max']}).reset_index()
                datapaso.columns = ['tipo','numero','propiedades','areamin','areamax','valor','minyaer','maxyear']
                dataresult = dataresult.merge(datapaso[['tipo','numero','propiedades','areamin','areamax','valor','minyaer','maxyear']],on=['tipo','numero'],how='outer')
                
                datapaso   = df[df['precuso'].notnull()]
                datapaso   = datapaso.groupby(['tipo','numero'])['precuso'].agg(lambda x: '|'.join(list(set(x)))).reset_index()
                datapaso.columns = ['tipo','numero','precuso']
                dataresult = dataresult.merge(datapaso,on=['tipo','numero'],how='outer')
            
        # Informacion de transaccciones
        item = 'transacciones_snr'
        if not data_propietarios.empty:
            df         = data_propietarios[data_propietarios[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'tipo': x['tipo'], 'numero': x['numero']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                
            if not df.empty and 'email' in df:
                datapaso = pd.DataFrame()
                if not dataresult.empty and 'email' in dataresult:
                    datapaso = pd.concat([dataresult[['tipo','numero','email']],df[['tipo','numero','email']]])
                    dataresult.drop(columns=['email'],inplace=True)
                else:
                    datapaso = df.copy()
                    
                datapaso          = datapaso.assign(email=datapaso['email'].str.split('|')).explode('email').reset_index(drop=True)
                datapaso          = datapaso.explode('email')
                datapaso['email'] = datapaso['email'].apply(lambda x: x.strip() if isinstance(x,str) and x!='' else None)
                datapaso          = datapaso.drop_duplicates(subset=['tipo','numero','email'])
                datapaso          = datapaso.groupby(['tipo','numero'])['email'].apply(lambda row: ' | '.join(str(email).lower() for email in row.dropna().unique() if '@' in str(email))).reset_index()
                datapaso.columns  = ['tipo','numero','email']
                dataresult        = dataresult.merge(datapaso,on=['tipo','numero'],how='left',validate='m:1')
   
            if not df.empty:
                df  = df[df['codigo'].isin(['168','169','219','203','0203','219','0219','164','0164','0168','0169','0219','197','0197'])]
            if not df.empty:
                datamerge = df.sort_values(by=['tipo','numero','email'], na_position='last').drop_duplicates(subset=['tipo','numero'],keep='first')
                datamerge['credito'] = True
                dataresult = dataresult.merge(datamerge[['tipo','numero','credito']],on=['tipo','numero'],how='outer')

    if not data.empty:
        datapaso         = data.copy()
        idd              = datapaso['tipo'].isnull()
        datapaso.loc[idd,'tipo'] = 'NA'
        datapaso         = datapaso.groupby(['chip','identificacion']).agg({'preaconst':'max','avaluo_catastral':'max','year':['min','max']}).reset_index()
        datapaso.columns = ['chip','numero','preaconst','avaluo_catastral','minyaer_new','maxyear_new']
        datapaso         = datapaso.groupby(['numero']).agg({'chip':'nunique','preaconst':['min','max'],'avaluo_catastral':'sum','minyaer_new':'min','maxyear_new':'max'}).reset_index()
        datapaso.columns = ['numero','propiedades_new','areamin_new','areamax_new','valor_new','minyaer_new','maxyear_new']
        dataresult       = dataresult.merge(datapaso,on=['numero'],how='left',validate='m:1')
        
        datapaso         = data[data['precuso'].notnull()]
        datapaso         = datapaso.groupby(['identificacion'])['precuso'].agg(lambda x: '|'.join(list(set(x)))).reset_index()
        datapaso.columns = ['numero','precuso_new']
        dataresult       = dataresult.merge(datapaso,on=['numero'],how='left',validate='m:1')

        for i in ['propiedades','areamin','areamax','valor','minyaer','maxyear','precuso']:
            idd = (dataresult[i].isnull()) & (dataresult[f'{i}_new'].notnull())
            if sum(idd)>0:
                dataresult.loc[idd,i] = dataresult.loc[idd,f'{i}_new']
                
        idd = dataresult['minyaer_new']<dataresult['minyaer']
        if sum(idd)>0:
            dataresult.loc[idd,'minyaer'] = dataresult.loc[idd,'minyaer_new']
            
        idd = dataresult['maxyear_new']>dataresult['maxyear']
        if sum(idd)>0:
            dataresult.loc[idd,'maxyear'] = dataresult.loc[idd,'maxyear_new']
                
        dataresult.drop(columns=['propiedades_new','areamin_new','areamax_new','valor_new','minyaer_new','maxyear_new','precuso_new'],inplace=True)

    return dataresult

@st.cache_data(show_spinner=False)
def getprediales(grupo=None):
    
    data = pd.DataFrame()
    #-------------------------------------------------------------------------#
    # Propietarios
    if isinstance(grupo,list) and grupo!=[]:
        data_predial = dataprediales(grupo=grupo, seleccion=0, variables='grupo,barmanpre,prediales')
        
        if not data_predial.empty:
            df              = data_predial[data_predial['prediales'].notnull()]
            df['prediales'] = df['prediales'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df              = df[df['prediales'].notnull()]
            df              = df.explode('prediales')
            df              = df.apply(lambda x: {**(x['prediales']), 'grupo': x['grupo'], 'barmanpre': x['barmanpre']}, axis=1)
            df              = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                data       = df.copy()
    #-------------------------------------------------------------------------#
    # Datos de propietario / propiedades y transacciones
    if not data.empty:
        
        data['identificacion'] = data['identificacion'].apply(lambda x: re.sub('[^0-9]','',x) if isinstance(x,str) else None)
        data['tipo'] = data['tipo'].apply(lambda x: re.sub('[^a-zA-Z]','',x.upper()) if isinstance(x,str) else None)
        data['tipo'] = data['tipo'].replace({'PASAPORTE':'PA','CARNETDIPLOMATICO':'CD'})
        idd = data['tipo'].isin(['CC','NIT','CE','TI','PA','RC','NUIP','CD'])
        if sum(~idd)>0:
            data.loc[~idd,'tipo'] = None
                    
    return data

def infoinput(data):
    if not data.empty:
        for i in [1,2,3,4,5]:
            data[f'telefono{i}'] = data['telefonos'].apply(lambda x: getparam(x,'numero',i-1))
        for i in [1,2,3]:
            data[f'email{i}'] = data['email'].apply(lambda x: getparam(x,'direccion',i-1))
        data.drop(columns=['telefonos','email'],inplace=True)
        
        vartel = [x for x in list(data) if 'telefono' in x]
        if isinstance(vartel,list) and vartel!=[]:
            data['telefonos'] = data[vartel].apply(lambda row: ' | '.join(pd.Series([str(num).split('.0')[0] for num in row if not pd.isna(num)]).unique()), axis=1)
        else: data['telefonos'] = None
        
        varmail = [x for x in list(data) if 'email' in x]
        if isinstance(varmail,list) and varmail!=[]:
            data['email'] = data[varmail].apply(lambda row: ' | '.join(pd.Series([str(num).lower() for num in row if pd.notnull(num)]).unique()) , axis=1)
        else: data['email'] = None

        varname = [x for x in ['primerNombre','segundoNombre','primerApellido','segundoApellido'] if x in data]
        if isinstance(varname,list) and varname!=[]:
            data['nombre'] = data[varname].apply(lambda row: ' '.join([str(num) for num in row if not pd.isna(num)]), axis=1)
        else: data['nombre'] = None

    return data
        
def getparam(x,tipo,pos):
    try: return json.loads(x)[pos][tipo]
    except: return None
    
@st.cache_data(show_spinner=False)
def getWKTfromgrupo(grupo=None):
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data     = pd.DataFrame(columns=['grupo', 'wkt'])
    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        lista = ",".join(grupo)
        query = f" grupo IN ({lista})"
        data  = pd.read_sql_query(f"SELECT distinct(grupo) as grupo, ST_AsText(geometry) as wkt FROM  bigdata.bogota_lotes_geometry WHERE {query}" , engine)
    engine.dispose()
    return data