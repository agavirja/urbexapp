import streamlit as st
import pandas as pd
import re
import requests
import fitz
import tempfile
import boto3
import hashlib
from twocaptcha import TwoCaptcha
from datetime import datetime
from price_parser import Price
from sqlalchemy import create_engine 

from functions._principal_getunidades import getpropietarios

# https://2captcha.com/pricing
# https://2captcha.com/enterpage

#@st.cache_data(show_spinner=False)
def main(chip=None,data_prediales=pd.DataFrame(), data_anotaciones=pd.DataFrame(), year=2025):
    
    df         = pd.DataFrame()
    dataresult = pd.DataFrame()
    if not data_prediales.empty:
        
        # 1. Verificar primero si existe en la base de datos data_bogota_shd_{year}
        dataresult = check_predial(chip=chip, year=year)
        
        if dataresult.empty:
            
            # 2. Si no existe registro, verificar los propietarios para buscar el predial

            #data_prediales['tipodocumentoid']   = data_prediales['tipoDocumento'].apply(lambda x: f"{re.sub('[^a-zA-Z]','',x.upper())}" if isinstance(x,str) else None) if 'tipoDocumento' in data_prediales else None
            #data_prediales['numerodocumentoid'] = data_prediales['identificacion'].apply(lambda x: f"{re.sub('[^0-9]','',x)}" if isinstance(x,str) else None ) if 'identificacion' in data_prediales else None

            if 'tipoDocumento' in data_prediales and 'tipo' in data_prediales:
                data_prediales['tipodocumentoid'] = data_prediales.apply(lambda row: f"{re.sub('[^a-zA-Z]', '', row['tipoDocumento'].upper())}"if isinstance(row['tipoDocumento'], str) else (f"{re.sub('[^a-zA-Z]', '', row['tipo'].upper())}" if isinstance(row['tipo'], str) else None),axis=1)
            elif 'tipoDocumento' in data_prediales:
                data_prediales['tipodocumentoid'] = data_prediales['tipoDocumento'].apply(lambda x: f"{re.sub('[^a-zA-Z]','',x.upper())}" if isinstance(x,str) else None) if 'tipoDocumento' in data_prediales else None
            elif 'tipo' in data_prediales:
                data_prediales['tipodocumentoid'] = data_prediales['tipo'].apply(lambda x: f"{re.sub('[^a-zA-Z]','',x.upper())}" if isinstance(x,str) else None) if 'tipo' in data_prediales else None

            data_prediales['numerodocumentoid'] = data_prediales['identificacion'].apply(lambda x: f"{re.sub('[^0-9]','',x)}" if isinstance(x,str) else None ) if 'identificacion' in data_prediales else None
            data_prediales['mergeid']           = data_prediales.apply(lambda x: f"{x['year']}|{x['tipodocumentoid']}|{x['numerodocumentoid']}" if x['tipodocumentoid'] is not None and x['numerodocumentoid'] is not None else None,axis=1)
            
            try:    listadocumento = list(data_prediales[data_prediales['mergeid'].notnull()]['mergeid'].unique())
            except: listadocumento = []
            
            if not data_anotaciones.empty:
                data_anotaciones['fecha_year']        = pd.to_datetime(data_anotaciones['fecha_documento_publico'], unit='ms') if 'fecha_documento_publico' in data_anotaciones else None
                data_anotaciones['fecha_year']        = data_anotaciones['fecha_year'].apply( lambda x: x.year if isinstance(x, pd.Timestamp) else None )
                

                if 'tipoDocumento' in data_anotaciones and 'tipo' in data_anotaciones:
                    data_anotaciones['tipodocumentoid'] = data_anotaciones.apply(lambda row: f"{re.sub('[^a-zA-Z]', '', row['tipoDocumento'].upper())}"if isinstance(row['tipoDocumento'], str) else (f"{re.sub('[^a-zA-Z]', '', row['tipo'].upper())}" if isinstance(row['tipo'], str) else None),axis=1)
                elif 'tipoDocumento' in data_anotaciones:
                    data_anotaciones['tipodocumentoid'] = data_anotaciones['tipoDocumento'].apply(lambda x: f"{re.sub('[^a-zA-Z]','',x.upper())}" if isinstance(x,str) else None) if 'tipoDocumento' in data_anotaciones else None
                elif 'tipo' in data_anotaciones:
                    data_anotaciones['tipodocumentoid'] = data_anotaciones['tipo'].apply(lambda x: f"{re.sub('[^a-zA-Z]','',x.upper())}" if isinstance(x,str) else None) if 'tipo' in data_anotaciones else None
                
                data_anotaciones['numerodocumentoid'] = data_anotaciones['nrodocumento'].apply(lambda x: f"{re.sub('[^0-9]','',x)}" if isinstance(x,str) else None ) if 'nrodocumento' in data_anotaciones else None
                data_anotaciones['mergeid']           = data_anotaciones.apply(lambda x: f"{x['fecha_year']}|{x['tipodocumentoid']}|{x['numerodocumentoid']}" if x['tipodocumentoid'] is not None and x['numerodocumentoid'] is not None else None,axis=1)
                try:    
                    listadocumentoadd = list(data_anotaciones[data_anotaciones['mergeid'].notnull()]['mergeid'].unique())
                    listadocumento    = listadocumento+listadocumentoadd
                except: pass
            
            if isinstance(listadocumento,list) and listadocumento!=[]:
                listadocumento = list(set(listadocumento))
                df = pd.DataFrame([item.split('|') for item in listadocumento], columns=['year', 'tipo', 'documento'])
                df = df.sort_values(by='year',ascending=False).drop_duplicates(subset=['tipo', 'documento'],keep='first')
                df.index = range(len(df))

    # 3. Si no existe registro en las bases de datos y tenemos informacion de los propietarios, se procede a descargar el predial
    if isinstance(chip,str) and dataresult.empty and not df.empty:
        
        for _,items in df.iterrows():
            rr = resolver_recaptcha(chip=chip, tipo=items['tipo'], documento=items['documento'], year=year)
            if isinstance(rr,list) and rr!=[]:
                dataresult = pd.DataFrame(rr)
                break
            
    if not dataresult.empty:
        dataresult, _, _ = getpropietarios(dataresult,pd.DataFrame())
        dataresult.rename(columns={'dirección':'direccion','matrícula inmobiliaria':'matriculainmobiliaria','matricula inmobiliaria':'matriculainmobiliaria'},inplace=True)


    return dataresult

def resolver_recaptcha(chip=None,tipo=None,documento=None,year=2025):
    
    resultado = None
    solver    = TwoCaptcha('a31e7e8fee8bf3c63c534f2989a673ca')
    try:
        result = solver.recaptcha(
            sitekey='6LdZIr8UAAAAANi3mhu9EJxnFoCWDIC_eHR9feeM',
            url='https://nuevaoficinavirtual.shd.gov.co/bogota/es/descargaFacturaVA'
        )
        if 'code' in result:
            data = {
                "tipoDoc": tipo, #"CC",
                "numDoc": documento, #"1020712479",
                "claveImpuesto": "0001",
                "anioGravable": year, #"2025",
                "claveObjeto": chip, #"AAA0218YARJ",
                "recaptchaResponse": result['code'],
            }
            form_url = "https://nuevaoficinavirtual.shd.gov.co/bogota/es/descargaFacturaVA/buscarInfo"
            response = requests.post(form_url, data=data).json()
            
            if 'dataForm' in response and 'urlDownload' in response['dataForm'] and isinstance(response['dataForm']['urlDownload'],str):
                documento = f"https://nuevaoficinavirtual.shd.gov.co{response['dataForm']['urlDownload']}"
                numBP     = response['dataForm']['numBP'] if 'dataForm' in response and 'numBP' in response['dataForm'] else None
                
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    rr = requests.get(documento)
                    if rr.status_code == 200:
                        temp_pdf.write(rr.content)
                        temp_pdf_path = temp_pdf.name
                        
                if temp_pdf_path:
                    result_export = uploadpdf(chip,year,temp_pdf_path)
                    if 'url' in result_export and isinstance(result_export['url'],str):
                        pdf_document = fitz.open(temp_pdf_path)
                        page         = pdf_document.load_page(0)
                        resultado    = getinfo(page)
                        
                        resultado['numBP'] = numBP
                        resultado['url']   = result_export['url'] if 'url' in result_export and isinstance(result_export['url'],str) else None
                        resultado['year']  = year
                        if 'propietario' not in resultado:
                            resultado.update({'salida':1})
                            resultado = [resultado]
                        elif 'propietario' in resultado and resultado['propietario']==[]:
                            del resultado['propietario']
                            resultado.update({'salida':1})
                            resultado = [resultado]
                        else:
                            resultado.update({'salida':0})
                            resultado = datacleaning(resultado.copy())
                            resultado = resultado.to_dict(orient='records')
                            
                        # Guardar informacion en mysql
                        upload_data(resultado,year)
        return resultado
    except:
        return None
    
#-----------------------------------------------------------------------------#
# Lectura Predial PDF
#-----------------------------------------------------------------------------#
def getinfo(page):
    resultado = {}
    
    coordenadas_lista = []
    for cadena_coordenadas in page.get_bboxlog(0):
        _, coordenadas = eval(str(cadena_coordenadas))
        x0, y0, x1, y1 = coordenadas
        text_elements = page.get_text("text", clip=coordenadas).strip()
        coordenadas_lista.append({'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,'text_elements':text_elements})
    df  = pd.DataFrame(coordenadas_lista)
    idd = df['text_elements'].apply(lambda x: x.strip())==''
    df  = df[~idd]
    df  = df.sort_values(by='y0',ascending=True)
    df.index = range(len(df))
    
    df['grupo'] = None
    grupo = 1
    K     = 2
    for i in range(len(df)):
        idd = abs(df['y0'] - df['y0'].iloc[i])<K
        df.loc[idd,'grupo'] = grupo
        grupo += 1
    df        = df.sort_values(by=['grupo','x0'],ascending=True)
    w         = df.groupby('grupo')['y0'].count().reset_index()
    w.columns = ['grupo','conteo']
    df        = df.merge(w,on='grupo',how='left',validate='m:1')
    df.index  = range(len(df))
    
    # chip, direccion y matricula
    try:
        patron_busqueda = r'(?i)1\. *CHIP'
        idd         = df['text_elements'].str.contains(patron_busqueda)
        v           = df[df['grupo'].isin(df[idd]['grupo'])]
        idd         = df.index.isin(v.index)
        v.index     = range(len(v))
        v           = v[['text_elements']]
        nombres     = v['text_elements'][::2].str.extract(r'^[0-9]+\.\s([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+)$')[0].str.lower()
        valores     = v['text_elements'][1::2]
        result_dict = dict(zip(nombres, valores))
        resultado.update(result_dict)
    except: pass
    
    # Propietarios:
    try:
        df1             = df[df['conteo']==7]
        patron_busqueda = r'(?i)4\. *TIPO'
        idd             = df1['text_elements'].str.contains(patron_busqueda)
        idd             = df1['grupo'].isin(df1[idd]['grupo'])
        df1             = df1[~idd]
        
        json_prop = []
        conteo    = 1
        for grupo in df1['grupo'].unique():
            dd      = df1[df1['grupo']==grupo]
            nombres = ['tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'municipio']
            valores = dd['text_elements'].to_list()
            result_dict = dict(zip(nombres, valores))
            json_prop.append(result_dict)
            conteo +=1 
        resultado.update({'propietario':json_prop})
    except: pass

    # Avaluo catastral:
    try:
        df1             = df[df['conteo']==5]
        patron_busqueda = r'(?i)12\. *AVALÚO'
        idd             = df1['text_elements'].str.contains(patron_busqueda)
        idd             = df1['grupo'].isin(df1[idd]['grupo'])
        df1             = df1[~idd]
        nombres         = ['avaluo_catastral', 'destino_hacendario', 'tarifa', 'excencion', 'exclusion_parcial']
        valores         = df1['text_elements'].to_list()
        result_dict     = dict(zip(nombres, valores))
        resultado.update(result_dict)
    except: pass

    # Impuesto predial:
    try:
        patron_busqueda = '19. IMPUESTO AJUSTADO'
        idd             = df['text_elements']==patron_busqueda
        df1             = df[df.index>df[idd].index[0]]
        df1             = df1[df1['conteo']==3]
        df1             = df1[df1['grupo']==df1['grupo'].iloc[0]]
        nombres         = ['impuesto_predial','descuento','impuesto_ajustado']
        valores         = df1['text_elements'].to_list()
        result_dict     = dict(zip(nombres, valores))
        resultado.update(result_dict)
    except: pass
    
    return resultado

def datacleaning(inputvar):
    result = inputvar.copy()
    resultado = []
    if 'propietario' in result and result['propietario']!=[]:
        propietario = result['propietario'].copy()
        del result['propietario']
        for i in propietario:
            result.update(i)
            resultado.append(result.copy())
            
    if resultado:
        try: 
            resultado = pd.DataFrame(resultado)
        except: 
            try: 
                resultado = pd.DataFrame([resultado])
            except: pass
        
        if isinstance(resultado, pd.DataFrame):
            resultado['fecha_consulta'] = datetime.now().strftime('%Y-%m-%d')
            for i in ['avaluo_catastral', 'impuesto_predial','descuento','impuesto_ajustado']:
                if i in resultado:
                   resultado[i] = resultado[i].apply(lambda x: string2number(x))
            if 'copropiedad' in resultado:
                resultado['copropiedad'] = resultado['copropiedad'].apply(lambda x: porcentaje2number(x))
    return resultado

def porcentaje2number(x):
    try:
        x = re.sub('[^0-9,.]','',x)
        return float(x.replace(',','.'))
    except:
        try:
            return float(x)
        except:
            return None

def string2number(x):
    try:
        x = Price.fromstring(x).amount_float
    except: 
        try:
            x = float(x.replace('.', ''))
        except: 
            x = None
    return x

#-----------------------------------------------------------------------------#
# Exportar pdf
#-----------------------------------------------------------------------------#
def generar_codigo(x):
    hash_sha256 = hashlib.sha256(x.encode()).hexdigest()
    codigo      = hash_sha256[:12]
    return codigo

def uploadpdf(chip,year,temp_pdf_path):
    ACCESS_KEY  = 'DO00JMM7DR78LD2JAAEA'
    SECRET_KEY  = 'BxBRkj7i5D9TaWkV+CHeji7RKcCNz8myLsndmRadOyQ'
    REGION      = 'nyc3'
    BUCKET_NAME = 'prediales'
    
    try:
        session = boto3.session.Session()
        client  = session.client('s3', region_name=REGION, endpoint_url='https://nyc3.digitaloceanspaces.com',
                                aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    
        filename = generar_codigo(f'{year}{chip}{year}')
        filename = f'{filename.upper()}.pdf'
        
        with open(temp_pdf_path, 'rb') as f:
            client.upload_fileobj(f, BUCKET_NAME, filename, ExtraArgs={'ACL': 'public-read','ContentType': 'application/pdf'})
        result = {'chip':chip,'encriptado':filename,'year':year,'url': f'https://{BUCKET_NAME}.{REGION}.digitaloceanspaces.com/{filename}'}
    except: result = {'chip':None,'encriptado':None,'year':None,'url':None}
    return result

#-----------------------------------------------------------------------------#
# Guardar data
#-----------------------------------------------------------------------------#
def upload_data(result,year):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata"]
    schema   = st.secrets["schema_bigdata"]

    if isinstance(result,list) and result!=[]:
        w         = pd.DataFrame(result)
        w.rename(columns={'dirección':'direccion','matrícula inmobiliaria':'matriculainmobiliaria','matricula inmobiliaria':'matriculainmobiliaria'},inplace=True)
        engine    = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        variables = [x for x in ['salida','chip', 'direccion', 'matriculainmobiliaria', 'avaluo_catastral', 'destino_hacendario', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'municipio', 'fecha_consulta','numBP'] if x in list(w)]
        w         = w[variables]
        salida_0  = w[w['salida']==0]
        if not salida_0.empty:
            salida_0.index = range(len(salida_0))
            salida_0.rename(columns={'matrícula inmobiliaria':'matriculainmobiliaria','dirección':'direccion'},inplace=True)
            variables = [x for x in ['salida','vigencia','tipoimpuesto'] if x in salida_0]
            if variables:
                salida_0.drop(columns=variables,inplace=True)
            salida_0.to_sql(f'data_bogota_shd_{year}', engine, if_exists='append', index=False, chunksize=10)

        salida_error = w[w['salida'].isin([1,2])]
        if not salida_error.empty:
            salida_error.index = range(len(salida_error))
            variables = [x for x in ['chip','year','tipo','identificacion','salida'] if x in salida_error]
            salida_error  = salida_error[variables]
            salida_error['fecha_consulta'] = datetime.now().strftime('%Y-%m-%d')
            salida_error.to_sql(f'data_bogota_shd_{year}_error', engine, if_exists='append', index=False, chunksize=1000)
        engine.dispose()
        
def check_predial(chip=None, year=2025, check_propietarios=False):
    data = pd.DataFrame()
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    elif isinstance(chip,(float,int)):
        chip = [f'{chip}']
    if isinstance(chip,list) and chip!=[]:
        chip     = list(map(str, chip))
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata"]
        schema   = st.secrets["schema_bigdata"]
        
        lista  = "','".join(chip)
        query  = f" chip IN ('{lista}')"
        engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data   = pd.read_sql_query(f"SELECT * FROM  bigdata.data_bogota_shd_{year} WHERE {query}" , engine)
        engine.dispose()
        
        if check_propietarios and not data.empty:
            data, _, _ = getpropietarios(data,pd.DataFrame())
            data.rename(columns={'dirección':'direccion','matrícula inmobiliaria':'matriculainmobiliaria','matricula inmobiliaria':'matriculainmobiliaria'},inplace=True)
    
    return data
