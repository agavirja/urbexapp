import streamlit as st
import pandas as pd
import re
from datetime import datetime

@st.cache_data(show_spinner=False)
def main(data_prediales=pd.DataFrame(),data_anotaciones=pd.DataFrame(),datapropietarios=pd.DataFrame()):
    
    # Ejemplo:  grupo = 610954
    # data_predios, data_usosuelopredios, data_prediales, data_anotaciones, datapropietarios  = getadataunidades(grupo=grupo)
    maxid = 0
    if not data_prediales.empty:
        
        # Homologar data
        data_prediales['tipoDocumento']   = data_prediales.apply(lambda row: row['tipo'] if (pd.isna(row['tipoDocumento']) and isinstance(row['tipo'], str)) else row['tipoDocumento'], axis=1)
        data_prediales['tipoPropietario'] = data_prediales.apply(asignar_tipo_propietario, axis=1)
        idd = (data_prediales['tipo'].isnull()) & (data_prediales['tipoDocumento'].notnull()) if 'tipo' in data_prediales and 'tipoDocumento' in data_prediales else 0
        if sum(idd)>0:
            data_prediales.loc[idd,'tipo'] = data_prediales.loc[idd,'tipoDocumento'].apply( lambda x: re.sub('[^a-zA-Z]','',x) if isinstance(x,str) and x!='' else None)
        idd = data_prediales['identificacion'].notnull()
        if sum(idd)>0:
            data_prediales.loc[idd,'identificacion'] = data_prediales.loc[idd,'identificacion'].apply(lambda x: re.sub('[^0-9]','',x) if isinstance(x,str) and x!='' else None)
        
        # Data origen
        data_prediales['idunique'] = range(len(data_prediales))
        maxid = data_prediales['idunique'].max()
        data_prediales_origen      = data_prediales.copy()
        
        # Informacion predial del ultimo ano
        datagroup            = data_prediales.groupby(['chip'])['year'].max().reset_index()
        datagroup.columns    = ['chip','yearmax']
        data_prediales       = data_prediales.merge(datagroup,on='chip',how='left',validate='m:1')
        data_prediales       = data_prediales[data_prediales['year']==data_prediales['yearmax']]
        data_prediales.index = range(len(data_prediales))

        # Si no tiene propietarios en el ultimo ano
        datapaso = data_prediales_origen[(data_prediales_origen['tipoDocumento'].notnull()) | (data_prediales_origen['tipo'].notnull())  | (data_prediales_origen['identificacion'].notnull())]
        if not datapaso.empty:
            datapaso          = datapaso.sort_values(by=['chip','year'],ascending=False).drop_duplicates(subset=['chip','tipoDocumento','tipo','identificacion'],keep='first')
            datagroup         = datapaso.groupby(['chip'])['year'].max().reset_index()
            datagroup.columns = ['chip','yearmax']
            datapaso          = datapaso.merge(datagroup,on='chip',how='left',validate='m:1')
            datapaso          = datapaso[datapaso['year']==datapaso['yearmax']]

        # Datos con informacion de propietarios
        idd   = (data_prediales['tipoDocumento'].notnull()) | (data_prediales['tipo'].notnull())  | (data_prediales['identificacion'].notnull())
        data1 = data_prediales[idd]

        # Datos sin informacion de propietarios
        idd   = (data_prediales['tipoDocumento'].isnull()) | (data_prediales['tipo'].isnull())  | (data_prediales['identificacion'].isnull())
        data2 = data_prediales[idd]
        
        # Juntar informacion con datos pasados
        if not datapaso.empty:
            idd       = datapaso['chip'].isin(data2['chip'])
            datapaso  = datapaso[idd]
            variables = [x for x in ['chip', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'numBP', 'indPago', 'fechaPresentacion', 'nomBanco', 'tipoPropietario', 'tipoDocumento', 'telefonos', 'email', 'yearmax'] if x in datapaso]
            datapaso  = datapaso[variables]
        
            variables = [x for x in ['chip', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'impuesto_total', 'preaconst', 'preaterre', 'precuso', 'barmanpre','idunique'] if x in data2]
            data2     = data2[variables]
            data2     = data2.drop_duplicates(subset='chip',keep='first')
            data2     = datapaso.merge(data2,on=['chip'],how='left',validate='m:1')
            
        data_prediales = pd.concat([data1,data2])
      
        
    # Datos de nuevos propietarios
    if not data_prediales.empty and not data_anotaciones.empty:
        
        # Si tiene transacciones en el ultimo ano
        datapaso = data_anotaciones.copy()
        datapaso = datapaso[datapaso['codigo'].isin(['125','126','164','168','169','0125','0126','0164','0168','0169'])] 
        if not datapaso.empty:
            datapaso['fecha_documento_publico'] = pd.to_datetime(datapaso['fecha_documento_publico'], unit='ms')
            datapaso['year'] = datapaso['fecha_documento_publico'].apply(lambda x: x.year)
            datapaso         = datapaso[datapaso['year']>=datetime.now().year]
            
        if not datapaso.empty:
            datapaso = datapaso[((datapaso['tipoDocumento'].notnull()) | (datapaso['tipo'].notnull())) & (datapaso['nrodocumento'].notnull())]
            datapaso = datapaso.sort_values(by=['chip','fecha_documento_publico'],ascending=False).drop_duplicates(subset=['chip','tipoDocumento','tipo','nrodocumento'],keep='first')
            datapaso['tipo']           = datapaso['tipo'].apply(lambda x: re.sub('[^a-zA-Z]','',x) if isinstance(x,str) and x!='' else None)
            datapaso['identificacion'] = datapaso['nrodocumento'].apply(lambda x: re.sub('[^0-9]','',x) if isinstance(x,str) and x!='' else None)
            
        # Match con datapropietarios
        if not datapaso.empty and not datapropietarios.empty:
            w                   = datapropietarios.copy()
            w                   = w[['nroIdentificacion', 'tipoPropietario', 'tipoDocumento', 'telefonos', 'email', 'nombre']]
            w['tipo']           = w['tipoDocumento'].apply(lambda x: re.sub('[^a-zA-Z]','',x) if isinstance(x,str) and x!='' else None)
            w['identificacion'] = w['nroIdentificacion'].apply(lambda x: re.sub('[^0-9]','',x) if isinstance(x,str) and x!='' else None)

            datamerge  = w.drop_duplicates(subset=['tipo','identificacion'],keep='first')
            variables  = [x for x in list(datapaso) if x not in datamerge ]
            variables += ['tipo','identificacion']
            datapaso   = datapaso[variables].merge(datamerge,on=['tipo','identificacion'],how='left',validate='m:1')
            
        # Pegar las ultimas transacciones
        if not datapaso.empty:
            
            idd   = data_prediales['chip'].isin(datapaso['chip'])
            data1 = data_prediales[~idd]
            data2 = data_prediales[idd]
            
            # Juntar informacion con datos de transacciones
            idd   = datapaso['chip'].isin(data2['chip'])
            if sum(idd)>0:
                datapaso  = datapaso[idd]
                variables = [x for x in ['chip', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'numBP', 'indPago', 'fechaPresentacion', 'nomBanco', 'tipoPropietario', 'tipoDocumento', 'telefonos', 'email', 'yearmax'] if x in datapaso]
                datapaso  = datapaso[variables]
                
                if not data2.empty:
                    variables = [x for x in ['chip', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'impuesto_total', 'preaconst', 'preaterre', 'precuso', 'barmanpre','idunique'] if x in data2]
                    data2     = data2[variables]
                    data2     = data2.drop_duplicates(subset='chip',keep='first')
                    data2     = datapaso.merge(data2,on=['chip'],how='left',validate='m:1')
                    #data2['idunique'] = range(maxid+1,maxid+1+len(data2)) 
                    
            data_prediales = pd.concat([data1,data2])
            
    if not data_prediales.empty:
        
        idd                   = data_prediales_origen['idunique'].isin(data_prediales['idunique'])
        data_prediales_origen = data_prediales_origen[~idd]
        data_prediales        = pd.concat([data_prediales,data_prediales_origen]) 
        
        idd = (data_prediales['year'].notnull()) & (data_prediales['yearmax'].isnull()) if 'year' in data_prediales and 'yearmax' in data_prediales else 0
        if sum(idd)>0:
            data_prediales.loc[idd,'yearmax'] = data_prediales.loc[idd,'year']
            
    return data_prediales

def asignar_tipo_propietario(row):
    if pd.isna(row['tipoPropietario']) and isinstance(row['tipoDocumento'], str):
        tipo_doc = re.sub('[^a-zA-Z]', '', row['tipoDocumento']).upper()
        if tipo_doc in ['CC', 'TI', 'PA', 'CE']:
            return 'PERSONA NATURAL'
        elif tipo_doc in ['NIT', 'NI']:
            return 'PERSONA JURIDICA'
    return row['tipoPropietario']