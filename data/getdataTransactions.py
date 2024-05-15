import streamlit as st
import re
import json
import pandas as pd
from sqlalchemy import create_engine 
from datetime import datetime
from unidecode import unidecode

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata_lectura"]
schema   = st.secrets["schema_bigdata"]
engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
@st.cache_data(show_spinner=False)
def main(code=None,typesearch=None,datamatricula=pd.DataFrame(),polygon=None):
    
    dataprocesos       = pd.DataFrame()
    datacatastro       = pd.DataFrame()
    datamatriculadocid = pd.DataFrame()
    dataoficinas       = getoficinas()
    dataoficinas.index = range(len(dataoficinas))
    
    if isinstance(typesearch, str) and 'chip' in typesearch:
        datacatastro = if_chip(code)
    elif isinstance(typesearch, str) and 'barmanpre' in typesearch:
        datacatastro = if_barmanpre(code)
    elif isinstance(polygon, str) and not 'none' in polygon.lower() :
        datacatastro = pd.read_sql_query(f"""SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst FROM bigdata.data_bogota_catastro WHERE ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))""" , engine)

    if not datacatastro.empty:
        lista  = "','".join(datacatastro['prechip'].unique())
        query  = f" chip IN ('{lista}')"
        datamatricula = pd.read_sql_query(f"SELECT chip,matriculainmobiliaria FROM bigdata.data_bogota_shd_objetocontrato WHERE {query}" , engine)
        
        if not datamatricula.empty:
            datamerge     = datacatastro.drop_duplicates(subset='prechip',keep='first')
            datamatricula = datamatricula.merge(datamerge[['prechip','precuso','predirecc','preaterre','preaconst']],left_on='chip',right_on='prechip',how='left',validate='m:1')
            datamatricula = datamatricula[datamatricula['matriculainmobiliaria'].notnull()]
            
    if not datamatricula.empty:
        datamatricula            = datamatricula[datamatricula['matriculainmobiliaria'].notnull()]
        datamatricula['codigos'] = datamatricula['matriculainmobiliaria'].apply(lambda x: x[0:4] if isinstance(x,str) else None)
        datamatricula['oficina'] = None
        datamatricula['codoficina'] = None
        for i in range(len(dataoficinas)):
            codigo  = dataoficinas['codigos'].iloc[i]
            oficina = dataoficinas['oficina'].iloc[i]
            idd     = datamatricula['codigos'].str.contains(codigo)
            if sum(idd)>0:
                datamatricula.loc[idd,'oficina']    = oficina
                datamatricula.loc[idd,'codoficina'] = codigo
        datamatricula = datamatricula[datamatricula['codoficina'].notnull()]
        
    if not datamatricula.empty:
        
        datamatricula['matricula']      = datamatricula.apply(lambda x: x['matriculainmobiliaria'].split(x['codoficina'],1)[-1].strip(),axis=1)
        datamatricula['matricula']      = datamatricula['matricula'].apply(lambda x: x.lstrip('0'))
        datamatricula['matriculamatch'] = datamatricula['codoficina']+datamatricula['matricula']
        
        lista              = "','".join(datamatricula['matricula'].unique())
        query              = f" value IN ('{lista}')"
        datamatriculadocid = pd.read_sql_query(f"SELECT docid,value FROM  bigdata.snr_data_matricula WHERE {query}" , engine)
        
        if not datamatriculadocid.empty:
            lista  = "','".join(datamatriculadocid['docid'].astype(str).unique())
            query  = f" docid IN ('{lista}')"
            datacompleta = pd.read_sql_query(f"SELECT docid,oficina as oficina_original,entidad,fecha_documento_publico,tipo_documento_publico, numero_documento_publico,datos_solicitante,documento_json FROM  bigdata.snr_data_completa WHERE {query}" , engine)
        
            if not datacompleta.empty:
                datacompleta       = add2tablaSNR(datacompleta)
                variables          = [x for x in ['docid','oficina_original','entidad','fecha_documento_publico','tipo_documento_publico','numero_documento_publico'] if x in datacompleta]
                datacompleta       = datacompleta[variables]
                datacompleta       = datacompleta.drop_duplicates(subset='docid',keep='last')
                datamatriculadocid = datamatriculadocid.merge(datacompleta,on='docid',how='left',validate='m:1')
                datamatriculadocid['oficina_original'] = datamatriculadocid['oficina_original'].apply(lambda x: re.sub(r'\s+',' ',unidecode(x.lower())))
                datamatriculadocid = datamatriculadocid.merge(dataoficinas,left_on='oficina_original',right_on='oficina',how='left',validate='m:1')
                datamatriculadocid['matriculamatch'] = datamatriculadocid['codigos']+datamatriculadocid['value']
        
                datamerge          = datamatricula.drop_duplicates(subset='matriculamatch',keep='first')
                datamatriculadocid = datamatriculadocid.merge(datamerge[['matriculamatch','prechip', 'precuso', 'predirecc', 'preaterre', 'preaconst']],on='matriculamatch',how='left',validate='m:1')
                datamatriculadocid = datamatriculadocid[datamatriculadocid['prechip'].notnull()]
        
    if not datamatriculadocid.empty:
        query        = "','".join(datamatriculadocid['docid'].astype(str).unique())
        query        = f" docid IN ('{query}')"
        dataprocesos = pd.read_sql_query(f"SELECT docid,codigo,nombre,tarifa,cuantia FROM  bigdata.snr_tabla_procesos WHERE {query}" , engine)
        dataprocesos = datamatriculadocid.merge(dataprocesos,on='docid',how='inner')
        dataprocesos['link'] = dataprocesos['docid'].apply(lambda x: f'https://radicacion.supernotariado.gov.co/app/static/ServletFilesViewer?docId={x}')
        dataprocesos['fecha_documento_publico'] = dataprocesos['fecha_documento_publico'].dt.strftime('%Y-%m-%d')
        dataprocesos = dataprocesos.sort_values(by=['fecha_documento_publico','docid'],ascending=False)

    return dataprocesos

def if_barmanpre(code):
    datacatastro = pd.DataFrame()
    if isinstance(code, str):
        code = [code]
    if isinstance(code, list):
        lista  = "','".join(code)
        query  = f" barmanpre IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
    return datacatastro
    
def if_chip(code):
    datacatastro = pd.DataFrame()
    if isinstance(code, str):
        code = [code]
    if isinstance(code, list):
        lista  = "','".join(code)
        query  = f" prechip IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,precuso,prechip,precedcata,predirecc,preaterre,preaconst FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
    return datacatastro

@st.cache_data(show_spinner=False) 
def getoficinas():
    dataoficinas = pd.read_sql_query("SELECT codigos,oficina,mpio_cnmbr FROM bigdata.snr_oficina2mpio" , engine)
    if not dataoficinas.empty:
        dataoficinas['oficina'] = dataoficinas['oficina'].apply(lambda x: re.sub(r'\s+',' ',unidecode(x.lower())))
    return dataoficinas

def add2tablaSNR(datatable):
    datatable = datatable.drop_duplicates()
    datatable['fecha_documento_publico'] = pd.to_datetime(datatable['fecha_documento_publico'],errors='coerce')
    idd       = datatable['fecha_documento_publico'].isnull()
    
    # Los que tienen fecha nula
    if sum(idd)>0:
        datatable['merge']   = range(len(datatable))
        datapaso                 = datatable[idd]
        datapaso['fechanotnull'] = datapaso['documento_json'].apply(lambda x: getEXACTfecha(x))
        formato_fecha = '%d-%m-%Y'
        datapaso['fechanotnull'] = pd.to_datetime(datapaso['fechanotnull'],format=formato_fecha,errors='coerce')
        datatable  = datatable.merge(datapaso[['merge','fechanotnull']],how='left',validate='m:1')
        idd = (datatable['fecha_documento_publico'].isnull()) & (datatable['fechanotnull'].notnull())
        if sum(idd)>0:
            datatable.loc[idd,'fecha_documento_publico'] = datatable.loc[idd,'fechanotnull']
        datatable.drop(columns=['fechanotnull','merge'],inplace=True)
    return datatable

def getEXACTfecha(x):
    result = None
    try:
        x = json.loads(x)
        continuar = 0
        for i in ['fecha','fecha:','fecha expedicion','fecha expedicion:','fecha recaudo','fecha recaudo:']:
            for j in x:
                if i==re.sub('\s+',' ',unidecode(j['value'].lower())):
                    posicion = x.index(j)
                    result   = x[posicion+1]['value']
                    continuar = 1
                    break
            if continuar==1:
                break
    except: result = None
    if result is None:
        result = getINfecha(x)
    return result
    
def getINfecha(x):
    result = None
    try:
        x = json.loads(x)
        continuar = 0
        for i in ['fecha','fecha:','fecha expedicion','fecha expedicion:','fecha recaudo','fecha recaudo:']:
            for j in x:
                if i in re.sub('\s+',' ',unidecode(j['value'].lower())):
                    posicion = x.index(j)
                    result   = x[posicion+1]['value']
                    continuar = 1
                    break
            if continuar==1:
                break
    except: result = None
    return result
