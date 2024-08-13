import streamlit as st
import re
import json
import pandas as pd
from unidecode import unidecode
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(chip=None,identificacion=None):
    
    user        = st.secrets["user_bigdata"]
    password    = st.secrets["password_bigdata"]
    host        = st.secrets["host_bigdata_lectura"]
    schema      = st.secrets["schema_bigdata"]
    engine      = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    data        = pd.DataFrame()
    
    if isinstance(chip,list) and chip!=[]:
        chip = [x for x in chip if not pd.isna(x)]
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    if isinstance(chip,list) and chip!=[]:
        #---------------------------------------------------------------------#
        # Data de matricula por chip
        #---------------------------------------------------------------------#
        query          = "','".join(chip)
        query          = f" numeroChip IN ('{query}')"
        datamatricula1 = pd.read_sql_query(f"SELECT numeroMatriculaInmobiliaria as value,numeroChip as prechip FROM  {schema}.data_bogota_catastro_predio WHERE {query}" , engine)
    
        query          = "','".join(chip)
        query          = f" chip IN ('{query}')"
        datamatricula2 = pd.read_sql_query(f"SELECT matriculainmobiliaria as matricula,chip as prechip FROM  {schema}.data_bogota_shd_objetocontrato WHERE {query}" , engine)
        datamatricula2['numoficina'] = None
        for j in ['50N','50C','50S']:
            idd = datamatricula2['matricula'].astype(str).str.contains(j)
            if sum(idd)>0:
                datamatricula2.loc[idd,'numoficina'] = j
        datamatricula2['value'] = datamatricula2.apply(lambda x: x['matricula'].split(x['numoficina'])[-1] if isinstance(x['numoficina'],str) else None,axis=1)
        
        #---------------------------------------------------------------------#
        # Docid por matricula
        #---------------------------------------------------------------------#
        datamatricula = pd.concat([datamatricula2,datamatricula1])
        datadocid     = pd.DataFrame()
        if not datamatricula.empty:
            datamatricula = datamatricula.drop_duplicates(subset='value',keep='first')
            query     = "','".join(datamatricula[datamatricula['value'].notnull()]['value'].astype(str).unique())
            query     = f" value IN ('{query}')"        
            datadocid = pd.read_sql_query(f"SELECT docid,value FROM  {schema}.snr_data_matricula WHERE {query}" , engine)
        
        #---------------------------------------------------------------------#
        # Info de la transaccion por docid
        #---------------------------------------------------------------------#
        if not datadocid.empty:
            query        = "','".join(datadocid[datadocid['docid'].notnull()]['docid'].astype(str).unique())
            query        = f" docid IN ('{query}')"  
            datacompleta = pd.read_sql_query(f"SELECT docid,oficina,entidad,fecha_documento_publico,tipo_documento_publico,numero_documento_publico,documento_json ,datos_solicitante FROM  {schema}.snr_data_completa WHERE {query}" , engine)         
            
            if not datacompleta.empty:
                if 'documento_json' in datacompleta:
                    datacompleta['fechanotnull'] = datacompleta['documento_json'].apply(lambda x: getEXACTfecha(x))
                    formato_fecha = '%d-%m-%Y'
                    datacompleta['fechanotnull'] = pd.to_datetime(datacompleta['fechanotnull'],format=formato_fecha,errors='coerce')
        
                    idd = (datacompleta['fecha_documento_publico'].isnull()) & (datacompleta['fechanotnull'].notnull())
                    if sum(idd)>0:
                        datacompleta.loc[idd,'fecha_documento_publico'] = datacompleta.loc[idd,'fechanotnull']
                    datacompleta.drop(columns=['fechanotnull','documento_json'],inplace=True)
                
                if 'datos_solicitante' in datacompleta:
                    datacompleta['datos_solicitante'] = datacompleta['datos_solicitante'].apply(json.loads)
                    datacompleta['titular'] = datacompleta['datos_solicitante'].apply(lambda x: getvalue(x,0))
                    datacompleta['email']   = datacompleta['datos_solicitante'].apply(lambda x: getvalue(x,1))
                    datacompleta['tipo']    = datacompleta['datos_solicitante'].apply(lambda x: getname(x,2))
                    datacompleta['id']      = datacompleta['datos_solicitante'].apply(lambda x: getvalue(x,2))
                    datacompleta['tipo']    = datacompleta['tipo'].replace(['cedula de ciudadania','nit','cedula de extranjeria','tarjeta de identidad','pasaporte'], ['C.C.','N.I.T.','C.E.','T.I.','PASAPORTE'])
    
                variables = [x for x in ['documento_json','datos_solicitante'] if x in datacompleta]
                if variables!=[]: datacompleta.drop(columns=variables,inplace=True)
                datacompleta['oficina2code'] = None
                if 'oficina' in datacompleta:
                    datacompleta['oficina2code'] = datacompleta['oficina'].replace(['bogota zona norte','bogota zona centro','bogota zona sur'],['50N','50C','50S'])

            #-----------------------------------------------------------------#
            # Ultimas transacciones por chip
            #-----------------------------------------------------------------#
            if not datacompleta.empty:
                datamerge = datacompleta.sort_values(by=['docid','fecha_documento_publico'],ascending=[False,False])
                datamerge = datamerge.drop_duplicates(subset='docid',keep='first')
                datadocid = datadocid.merge(datamerge,on='docid',how='left',validate='m:1')
                    
                datamerge = datamatricula.drop_duplicates(subset='value',keep='first')
                datadocid = datadocid.merge(datamatricula,on='value',how='left',validate='m:1')

                data = datadocid.sort_values(by=['prechip','fecha_documento_publico'],ascending=[False,False])
                data = data.drop_duplicates(subset='prechip',keep='first')
                              
    #-------------------------------------------------------------------------#
    # Chip a matricula para completar datos
    #-------------------------------------------------------------------------#
    if not data.empty and 'prechip' in data:
        df = data[data['matricula'].isnull()]
        if not df.empty:
        
            query         = "','".join(df['prechip'].unique())
            query         = f" chip IN ('{query}')"
            datamatricula = pd.read_sql_query(f"SELECT matriculainmobiliaria as matricula_new,chip as prechip FROM  {schema}.data_bogota_shd_objetocontrato WHERE {query}" , engine)
            datamatricula['numoficina_new'] = None
            for j in ['50N','50C','50S']:
                idd = datamatricula['matricula_new'].astype(str).str.contains(j)
                if sum(idd)>0:
                    datamatricula.loc[idd,'numoficina_new'] = j
            
            if not datamatricula.empty:
                datamerge = datamatricula.drop_duplicates(subset='prechip',keep='first')
                data      = data.merge(datamerge,on='prechip',how='left',validate='m:1')
                for i in ['matricula','numoficina']:
                    idd = (data[i].isnull()) & (data[f'{i}_new'].notnull())
                    if sum(idd)>0:
                        data.loc[idd,i] = data.loc[idd,f'{i}_new']
                variables = [x for x in ['matricula_new','numoficina_new']]
                if variables!=[]: data.drop(columns=variables,inplace=True)

    if not data.empty and all([x for x in ['oficina2code','numoficina'] if x in data]):
        idd  = data['oficina2code']==data['numoficina']
        data = data[idd]
        data.drop(columns=['oficina2code','numoficina'],inplace=True)
        
    if not data.empty:
        data.rename(columns={'id':'nroIdentificacion','tipo':'tipoDocumento'},inplace=True)
        
    #-------------------------------------------------------------------------#
    # Traer valor de la transaccion
    #-------------------------------------------------------------------------#
    if not data.empty:
        listadocid     = "','".join(data['docid'].astype(str).unique())
        listacodigos   = "','".join(['125','126','168','169','0125','0126','0168','0169'])
        query          = f" docid IN ('{listadocid}') AND codigo IN ('{listacodigos}')"
        dataprocesos   = pd.read_sql_query(f"SELECT docid,cuantia FROM  {schema}.snr_tabla_procesos WHERE {query}" , engine)
        if not dataprocesos.empty:
            datamerge = dataprocesos.groupby('docid')['cuantia'].max().reset_index()
            data      = data.merge(datamerge,on='docid',how='left',validate='m:1')
            

    #-------------------------------------------------------------------------#
    # Match con identificacion
    #-------------------------------------------------------------------------#
    dataid = pd.DataFrame()
    if not data.empty and identificacion is not None:
        if isinstance(identificacion,str) and identificacion!='':
            identificacion = [re.sub('[^0-9]', '', str(x)) for x in identificacion.split(',') if len(re.sub('[^0-9]', '', str(x))) >= 6]
        if isinstance(identificacion,list) and identificacion!=[]:
            idd = True
            for j in identificacion:
                idd = (idd) & (data['nroIdentificacion'].astype(str).str.contains(j))
            dataid = data[idd]
            
    return data,dataid
            
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

def getvalue(x,pos):
    try: return x[pos]['value']
    except: return None
def getname(x,pos):
    try: return x[pos]['variable']
    except: return None  
