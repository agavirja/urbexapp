import streamlit as st
import pandas as pd
import json
import re
from sqlalchemy import create_engine 
from datetime import datetime

from data._principal_prediales import dataprediales
from data._principal_propietarios_v1 import datapropietarios,propietarios_shd_historicos
from data._principal_transaccionesByChip import main as _principal_transaccionesByChip
from data._principal_caracteristicas import datacaracteristicas
from data._principal_shapefile  import  getscacodigo 
from functions.getuso_destino import usosuelo_class

@st.cache_data(show_spinner=False)      
def main(grupo=None):

    dataresult             = pd.DataFrame(columns=['tipo','numero'])
    data_predios           = pd.DataFrame(columns=['tipo','numero','chip'])
    data_transacciones     = pd.DataFrame(columns=['tipo','numero','chip'])
    data_transacciones_nal = pd.DataFrame(columns=['tipo','numero','chip'])
    
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
                dataresult = dataresult.merge(df[['tipo', 'numero','tipoPropietario','nombre', 'email','fechaDocumento']],on=['tipo','numero'],how='outer')
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
                data_predios = df.copy()
                data_predios = data_predios.sort_values(by='year',ascending=False).drop_duplicates()
                
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
                data_transacciones = df.copy()
                
        # Informacion de transaccciones a nivel nacional
        item = 'transacciones_nal'
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
                data_transacciones_nal = df.copy()
                
    #-------------------------------------------------------------------------#
    # Transacciones de los chip
    #-------------------------------------------------------------------------#
    datapaso                = pd.concat([data_predios[['chip']],data_transacciones[['chip']]])
    data_predios['activo']  = 0
    data_transacciones_chip = pd.DataFrame()
    if not datapaso.empty:
        chip = list(datapaso['chip'].unique())
        data_transacciones_chip = _principal_transaccionesByChip(chip=chip)

    #-------------------------------------------------------------------------#
    # Activos / no activos:
    #-------------------------------------------------------------------------#
    if not data_predios.empty and not data_transacciones_chip.empty:

        data_transacciones_chip['year_t']   = data_transacciones_chip['fecha_documento_publico'].apply(lambda x: getyear(x)) 
        data_transacciones_chip['numero_t'] = data_transacciones_chip['identificacion'].copy()   
        datamege     = data_transacciones_chip.sort_values(by=['chip','fecha_documento_publico'],ascending=False).drop_duplicates(subset='chip',keep='first')
        data_predios = data_predios.merge(datamege[['chip','numero_t','year_t']],on='chip',how='left',validate='m:1')
        idd          = data_predios.apply(lambda x: isinstance(x['numero'], str) and isinstance(x['numero_t'], str) and x['numero']!='' and x['numero_t']!='' and ((x['numero'] in x['numero_t'] or x['numero_t'] in x['numero'])),axis=1)        
        idd          = (idd) | (data_predios.apply(lambda x: x['year']==datetime.now().year and pd.isna(x['numero_t']) and any(w in x['numero'] for w in grupo), axis=1))
        if sum(idd)>0:
            data_predios.loc[idd,'activo'] = 1
        
    elif not data_predios.empty and data_transacciones_chip.empty:
        idd = (data_predios['year'] == datetime.now().year) & (data_predios['numero'].apply(lambda num: any(grp in num for grp in grupo)))
        if sum(idd)>0:
            data_predios.loc[idd,'activo'] = 1

    elif data_predios.empty and not data_transacciones_chip.empty:
        
        datapaso  = data_transacciones_chip.sort_values(by=['chip','fecha_documento_publico'],ascending=False).drop_duplicates(subset='chip',keep='first')
        idd       = datapaso['identificacion'].apply(lambda num: any(grp in num for grp in grupo))
        datapaso  = datapaso[idd]
        if not datapaso.empty:
            datapaso['year'] = datapaso['fecha_documento_publico'].apply(lambda x: getyear(x)) 
            data_predios     = datapaso.copy()
            variables        = ['grupo', 'barmanpre', 'chip', 'matriculainmobiliaria', 'nombre', 'preaconst', 'preaterre', 'precuso', 'tipo','identificacion','year','predirecc',]
            data_predios     = data_predios[variables]
            data_predios.rename(columns={'predirecc':'direccion','identificacion':'numero'},inplace=True)
            data_predios['activo'] = 1
        
    #-------------------------------------------------------------------------#
    # Activos en transacciones pero no en SHD
    #-------------------------------------------------------------------------#
    if not data_transacciones_chip.empty:
        datapaso  = data_transacciones_chip.sort_values(by=['chip','fecha_documento_publico'],ascending=False).drop_duplicates(subset='chip',keep='first')
        idd       = datapaso['identificacion'].apply(lambda num: any(grp in num for grp in grupo))
        datapaso  = datapaso[idd]
        if not datapaso.empty:
            datapaso['year'] = datapaso['fecha_documento_publico'].apply(lambda x: getyear(x)) 
            variables        = ['grupo', 'barmanpre', 'chip', 'matriculainmobiliaria', 'nombre', 'preaconst', 'preaterre', 'precuso', 'tipo','identificacion','year','predirecc',]
            datapaso         = datapaso[variables]
            datapaso.rename(columns={'predirecc':'direccion','identificacion':'numero'},inplace=True)
            datapaso['activo'] = 1
            datapaso['fuente'] = 'transacciones'
        if not datapaso.empty and not data_predios.empty:
            idd      = datapaso['chip'].isin(data_predios['chip'])
            datapaso = datapaso[~idd]
            if not datapaso.empty:
                data_predios['fuente'] = 'shd'
                data_predios           = pd.concat([data_predios,datapaso])
                
    if not data_predios.empty and 'activo' in data_predios:
        data_predios   = data_predios[data_predios['activo']==1]
        
        
    #-------------------------------------------------------------------------#
    # Completar avaluos y prediales
    #-------------------------------------------------------------------------#
    if not data_predios.empty:
        duso  = usosuelo_class()
        idd   = duso['clasificacion'].isin(['Depósitos','Parqueadero'])
        duso  = duso[~idd]
        lista = list(duso['precuso'].unique())
        lista += ['024','050']
        lista = list(set(lista))
        
        idd          = data_predios['precuso'].isin(lista)
        data_predios = data_predios[idd]
        
    if not data_predios.empty:
        listagrupo     = list(data_predios[data_predios['grupo'].notnull()]['grupo'].astype(int).unique())
        
        # Actualizar prediales
        data_prediales = dataprediales(grupo=listagrupo, variables='grupo,prediales',seleccion=1)
        item           = 'prediales'
        if not data_prediales.empty:
            df         = data_prediales[data_prediales[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'grupo': x['grupo']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
            if not df.empty and 'chip' in df: 
                datapaso_n =  df[df['chip'].isin(data_predios['chip'])]
                variables  = ['direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'impuesto_predial', 'impuesto_ajustado', 'year', 'preaconst', 'preaterre', 'precuso']
                varname    = {x: f'{x}_new' for x in variables}
                variables  = ['chip']+variables
                datapaso_n = datapaso_n[variables]
                datapaso_n.rename(columns=varname,inplace=True)
                datapaso_n     = datapaso_n.drop_duplicates(subset='chip',keep='first')
                data_predios   = data_predios.merge(datapaso_n,on='chip',how='left',validate='m:1')
                variables.remove('chip')
                variables_valormax = ['avaluo_catastral', 'impuesto_predial', 'impuesto_ajustado', 'year', 'preaconst', 'preaterre']
                for i in variables:
                    idd = data_predios[f'{i}_new'].notnull()
                    if sum(idd)>0:
                        data_predios.loc[idd,i] = data_predios.loc[idd,f'{i}_new']
                    del data_predios[f'{i}_new']
                        
                
        # Actualizar antiguedad
        data_cataracteristicas = datacaracteristicas(grupo=listagrupo,variables='grupo,general_catastro')
        item                   = 'general_catastro'
        if not data_prediales.empty:
            df         = data_cataracteristicas[data_cataracteristicas[item].notnull()]
            df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df[item].notnull()]
            df         = df.explode(item)
            df         = df.apply(lambda x: {**(x[item]), 'grupo': x['grupo']}, axis=1)
            df         = pd.DataFrame(df)
            if not df.empty:
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                variables  = ['prevetustzmin','prevetustzmax','estrato','connpisos']
                variables  = [x for x in variables if x not in data_predios]
                variables  = ['grupo'] +variables
                df         = df[variables]
                df         = df.drop_duplicates(subset='grupo',keep='first')
                data_predios = data_predios.merge(df,on='grupo',how='left',validate='m:1')
                
    if not data_predios.empty:
        variablesdrop = [ x for x in ['nombre', 'activo', 'numero_t', 'year_t', 'fuente'] if x in data_predios]
        if variablesdrop!='':
            data_predios.drop(columns=variablesdrop,inplace=True)

    #-------------------------------------------------------------------------#
    # Historicos
    #-------------------------------------------------------------------------#
    data_historico     = propietarios_shd_historicos(identificacion=grupo)
    item               = 'propietario'
    data_shd_historico = pd.DataFrame(columns=['chip', 'vigencia', 'direccionPredio', 'valorAutoavaluo', 'valorImpuesto', 'tarifaPlena', 'indPago', 'nomBanco', 'nombrePeriodo'])
    if not data_historico.empty:
        df         = data_historico[data_historico[item].notnull()]
        df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df[df[item].notnull()]
        df         = df.explode(item)
        df         = df.apply(lambda x: {**(x[item]), 'numero': x['numero']}, axis=1)
        df         = pd.DataFrame(df)
        if not df.empty:
            df.columns = ['formato']
            df         = pd.json_normalize(df['formato'])
            variables  = ['chip', 'vigencia', 'direccionPredio', 'valorAutoavaluo', 'valorImpuesto', 'tarifaPlena', 'indPago', 'nomBanco', 'nombrePeriodo']
            variables  = [x for x in variables if x in df]
            if variables!='':
                df = df[variables]
            data_shd_historico = df.copy()
            
    #-------------------------------------------------------------------------#
    # Lat/Lng
    #-------------------------------------------------------------------------#
    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_read_urbex"]
    schema   = st.secrets["schema_write_urbex"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    lista    = []
    for ddbb in [data_predios, data_transacciones, data_transacciones_nal, data_shd_historico]:
        if not ddbb.empty  and 'chip' in ddbb:
            lista += list(ddbb['chip'].unique())
            if not ddbb.empty and 'latitud'  not in ddbb: ddbb['latitud'] = None
            if not ddbb.empty and 'longitud' not in ddbb: ddbb['longitud'] = None
            if not ddbb.empty and 'grupo'    not in ddbb: ddbb['grupo'] = None
        
    if isinstance(lista,list) and lista!=[]:
        lista = list(set(lista))
        datalatlng  = pd.DataFrame()
        lista       = "','".join(lista)
        query       = f" chip IN ('{lista}')"
        datalatlng  = pd.read_sql_query(f"SELECT chip,latitud as latitud_new,longitud as longitud_new, grupo as grupo_new FROM  bigdata.bogota_barmanpre_chip WHERE {query}" , engine)

        if not datalatlng.empty: 
            datalatlng = datalatlng.drop_duplicates(subset='chip',keep='first')
            
            if not data_predios.empty           and 'chip' in data_predios:           data_predios = data_predios.merge(datalatlng,on='chip',how='left',validate='m:1')
            if not data_transacciones.empty     and 'chip' in data_transacciones:     data_transacciones = data_transacciones.merge(datalatlng,on='chip',how='left',validate='m:1')
            if not data_transacciones_nal.empty and 'chip' in data_transacciones_nal: data_transacciones_nal = data_transacciones_nal.merge(datalatlng,on='chip',how='left',validate='m:1')
            if not data_shd_historico.empty     and 'chip' in data_shd_historico:     data_shd_historico = data_shd_historico.merge(datalatlng,on='chip',how='left',validate='m:1')
            
            for ddbb in [data_predios, data_transacciones, data_transacciones_nal, data_shd_historico]:
                if not ddbb.empty and 'chip' in ddbb:
                    for i in ['latitud','longitud','grupo']:
                        idd = (ddbb[i].isnull()) & (ddbb[f'{i}_new'].notnull())
                        if sum(idd)>0:
                            ddbb.loc[idd,i] = ddbb.loc[idd,f'{i}_new']
                        del ddbb[f'{i}_new']

    #-------------------------------------------------------------------------#
    # Barrio catastral
    #-------------------------------------------------------------------------#
    lista      = []
    databarrio = pd.DataFrame()
    for ddbb in [data_predios, data_transacciones, data_transacciones_nal, data_shd_historico]:
        if not ddbb.empty and 'grupo' in ddbb: 
            try: 
                ddbb['grupo'] = ddbb['grupo'].astype(int)
                listapaso     = list(ddbb['grupo'].unique())
                if isinstance(listapaso,list) and listapaso!=[]:
                    lista  += list(set(listapaso))
            except: pass

    if isinstance(lista,list) and lista!=[]:
        lista      = list(set(lista))
        databarrio = getscacodigo(grupo=lista)
        
    if not databarrio.empty:
        databarrio                = databarrio.drop_duplicates(subset='grupo',keep='first')
        databarrio['grupo']       = databarrio['grupo'].astype(int)
        data_predios              = data_predios.merge(databarrio[['grupo','scacodigo','wkt']],on='grupo',how='left',validate='m:1') if not data_predios.empty and 'grupo' in data_predios else data_predios
        data_transacciones        = data_transacciones.merge(databarrio[['grupo','scacodigo','wkt']],on='grupo',how='left',validate='m:1') if not data_transacciones.empty and 'grupo' in data_transacciones else data_transacciones
        data_transacciones_nal    = data_transacciones_nal.merge(databarrio[['grupo','scacodigo','wkt']],on='grupo',how='left',validate='m:1') if not data_transacciones_nal.empty and 'grupo' in data_transacciones_nal else data_transacciones_nal
        data_shd_historico        = data_shd_historico.merge(databarrio[['grupo','scacodigo','wkt']],on='grupo',how='left',validate='m:1') if not data_shd_historico.empty and 'grupo' in data_shd_historico else data_shd_historico

    engine.dispose()
    
    # Formato fecha: 
    if not data_transacciones.empty and 'fecha_documento_publico' in data_transacciones: 
        data_transacciones['fecha_documento_publico'] = pd.to_datetime(data_transacciones['fecha_documento_publico'], unit='ms')
        
    if not data_transacciones_nal.empty and 'fecha_documento_publico' in data_transacciones_nal: 
        data_transacciones_nal['fecha_documento_publico'] = pd.to_datetime(data_transacciones_nal['fecha_documento_publico'], unit='ms')

    return dataresult, data_predios, data_transacciones, data_transacciones_nal, data_shd_historico

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
    
def getyear(x):
    try: return x.year
    except: return None