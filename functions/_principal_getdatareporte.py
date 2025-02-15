import streamlit as st
import pandas as pd
import json
import concurrent.futures

from functions.getuso_destino import getuso_destino,usosuelo_class
from functions.getuso_tipoinmueble import usosuelo2inmueble
from functions.polygonunion import polygonunion

from data._principal_caracteristicas import datacaracteristicas,datadane,datapredios
from data._principal_prediales import dataprediales,estadisticas_prediales
from data._principal_transacciones import datatransacciones,data_anotaciones,estadisticas_transacciones
from data._principal_listings import data_ligtinsgs_barmanpre,datalistingsbarrio
from data._principal_pot import datapot
from data._principal_lotes import datalote, lotes_vecinos

from data.getdataCTL import main as getdataCTL
from data.getlicencias import getlicencias

@st.cache_data(show_spinner=False)
def main(grupo=None):
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_caracteristicas = executor.submit(datacaracteristicas, grupo=grupo)
        future_prediales       = executor.submit(dataprediales, grupo=grupo, seleccion=0)
        future_transacciones   = executor.submit(datatransacciones, grupo=grupo)
        future_listings        = executor.submit(data_ligtinsgs_barmanpre, grupo=grupo)
        future_pot             = executor.submit(datapot, grupo=grupo)
        future_datalote        = executor.submit(datalote, grupo=grupo)
        future_datapredios     = executor.submit(datapredios, grupo=grupo)
        future_dataanotaciones = executor.submit(data_anotaciones, grupo=grupo)
        future_lotesvecinos    = executor.submit(lotes_vecinos, grupo=grupo)

        
        data_general       = future_caracteristicas.result()
        data_prediales     = future_prediales.result()
        data_transacciones = future_transacciones.result()
        data_listings      = future_listings.result()
        data_pot           = future_pot.result()
        data_lote          = future_datalote.result()
        data_predios       = future_datapredios.result()
        data_transacciones_anotaciones   = future_dataanotaciones.result()
        data_lotes_completo = future_lotesvecinos.result()
        
    # Data prediales
    data_prediales.index      = range(len(data_prediales))
    data_prediales_actuales   = data_prediales.iloc[[0]] if not data_prediales.empty else pd.DataFrame(columns=['id', 'grupo', 'barmanpre', 'prediales', 'prediales_mt2', 'prediales_mt2_by_precuso', 'fecha_update'])
    data_prediales_historicos = data_prediales.iloc[[1]] if not data_prediales.empty and len(data_prediales)>1 else pd.DataFrame(columns=['id', 'grupo', 'barmanpre', 'prediales', 'prediales_mt2', 'prediales_mt2_by_precuso', 'fecha_update'])
    
    data_prediales_actuales.index   = range(len(data_prediales_actuales))
    data_prediales_historicos.index = range(len(data_prediales_historicos))

    # data ctl:
    datactl = getdataCTL(grupo=grupo)
    
    # data licencias: 
    barmanprelist = list(data_general['barmanpre'].unique()) if not data_general.empty and 'barmanpre' in data_general else []
    datalicencias = getlicencias(barmanpre=barmanprelist)
    
    try:    
        precusolist = list(pd.DataFrame(json.loads(data_general['catastro_byprecuso'].iloc[0]))['precuso'].unique())
        tipinmueble = usosuelo2inmueble(precusolist)
    except: 
        precusolist = []
        tipinmueble = []
    
    try:    data_listings = pd.DataFrame(data_listings['listings_data']['value'])    
    except: data_listings = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code', 'valormt2','direccion'])

    formato_outputs = []
    
    #-------------------------------------------------------------------------#
    # Ubicacion
    formato_outputs.append(ubicacion(data_general))
    #-------------------------------------------------------------------------#
    # Caracteristicas
    formato_outputs.append(caracteristicas(data_general))
    #-------------------------------------------------------------------------#
    # Terreno
    formato_outputs.append(terreno(data_general))
    #-------------------------------------------------------------------------#
    # Tipologias
    formato_outputs.append(tipologias(data_general))
    #-------------------------------------------------------------------------#
    # Predial
    formato_outputs.append(infopredial(data_prediales_actuales,data_general))
    #-------------------------------------------------------------------------#
    # Transacciones
    formato_outputs.append(transacciones(data_transacciones))
    #-------------------------------------------------------------------------#
    # Listings
    formato_venta,formato_arriendo = listings(data_listings)
    formato_outputs.append(formato_venta)
    formato_outputs.append(formato_arriendo)
    
    #-------------------------------------------------------------------------#
    # codigo y nombre del barrio
    scacodigo  = None
    prenbarrio = None
    if not data_general.empty:
        try:
            scacodigo  = json.loads(data_general['general_catastro'].iloc[0])[0]['precbarrio']
            prenbarrio = json.loads(data_general['general_catastro'].iloc[0])[0]['prenbarrio']
        except: pass
    
    #-------------------------------------------------------------------------#
    # Estadisticas del barrio
    if isinstance(scacodigo,str) and scacodigo!='':
        data_listings_barrio = datalistingsbarrio(scacodigo=scacodigo)
        
        try:
            data_estadisticas_barrio = pd.DataFrame(json.loads(data_listings_barrio[ 'valoresbarrio'].iloc[0]))
            data_estadisticas_barrio = data_estadisticas_barrio[data_estadisticas_barrio['tipoinmueble'].isin(tipinmueble)]
        except: 
            data_estadisticas_barrio = pd.DataFrame(columns=['tiponegocio', 'tipoinmueble', 'valormt2', 'obs'])
        try:
            data_valorizacion_barrio = pd.DataFrame(json.loads(data_listings_barrio['valorizacion'].iloc[0]))
            data_valorizacion_barrio = data_valorizacion_barrio[data_valorizacion_barrio['tipoinmueble'].isin(tipinmueble)]
            data_valorizacion_barrio = data_valorizacion_barrio.sort_values(by=['tipoinmueble','tiponegocio','trimestre'],ascending=False).drop_duplicates(subset=['tipoinmueble','tiponegocio'])
        except: 
            data_valorizacion_barrio = pd.DataFrame(columns=['tiponegocio', 'tipoinmueble', 'trimestre', 'valorizacion'])

        formato_salida = listings_estadisticas(data_estadisticas_barrio=data_estadisticas_barrio,data_valorizacion_barrio=data_valorizacion_barrio,barrio=prenbarrio)
        formato_outputs.append(formato_salida)
         
    #-------------------------------------------------------------------------#
    # POT
    formato_outputs.append(pot(data_pot))
    
    #-------------------------------------------------------------------------#
    # DANE
    if isinstance(scacodigo,str) and scacodigo!='':
        data_dane = datadane(scacodigo=scacodigo)
        formato_outputs.append(dane(data_dane,barrio=prenbarrio))

    #-------------------------------------------------------------------------#
    # Dejar 1 poligono: Si len(data_lote)>1 entonces hace la union, si len(data_lote)=1 lo deja como esta
    data_lote = polygonunion(data_lote)
    
    #-------------------------------------------------------------------------#
    # Estadisticas de transacciones:
    formato_estadisticas = {}
    data_transacciones_historicas = pd.DataFrame(columns=['docid', 'chip', 'codigo', 'cuantia', 'entidad', 'fecha_documento_publico', 'nombre', 'numero_documento_publico', 'oficina', 'preaconst', 'preaterre', 'precuso', 'predirecc', 'tipo_documento_publico', 'titular', 'email', 'tipo', 'nrodocumento', 'grupo', 'barmanpre'])
    if not data_transacciones_anotaciones.empty:
        df = data_transacciones_anotaciones.copy()
        if not df.empty:
            df = df[df['codigo'].isin(['125','126','164','168','169','0125','0126','0164','0168','0169'])]
        if not df.empty:
            dl    = usosuelo_class()
            lista = list(dl[dl['clasificacion'].isin(['Depósitos','Parqueadero'])]['precuso'].unique())
            if '050' in lista: lista.remove('050')
            idd   = df['precuso'].isin(lista)
            df    = df[~idd]
        if not df.empty:
            df = df.drop_duplicates()
        data_transacciones_historicas = df.copy()
    try:
        output_transacciones = estadisticas_transacciones(data=data_transacciones_historicas)
        formato_estadisticas.update(output_transacciones)
    except: pass

    #-------------------------------------------------------------------------#
    # Estadisticas de prediales:
    df = pd.DataFrame(columns=['chip', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'impuesto_total', 'fechaPresentacion', 'indPago', 'nomBanco', 'preaconst', 'preaterre', 'precuso', 'barmanpre'])
    if not data_prediales_historicos.empty and 'prediales' in data_prediales_historicos:
        
        df = pd.DataFrame(json.loads(data_prediales_historicos['prediales'].iloc[0]))
        if not df.empty:
            dl    = usosuelo_class()
            lista = list(dl[dl['clasificacion'].isin(['Depósitos','Parqueadero'])]['precuso'].unique())
            if '050' in lista: lista.remove('050')
            idd   = df['precuso'].isin(lista)
            df    = df[~idd]
    try:
        output_prediales = estadisticas_prediales(data=df)
        formato_estadisticas.update(output_prediales)
    except: pass

    #-------------------------------------------------------------------------#
    # Estadisticas de listing:
    df = pd.DataFrame(columns=['activo', 'tipoinmueble', 'tiponegocio', 'areaconstruida', 'habitaciones', 'banos', 'garajes', 'valor', 'fecha_inicial', 'inmobiliaria', 'url_img', 'latitud', 'longitud', 'code', 'valormt2'])
    if not data_listings.empty:
        df = data_listings.copy()
        df['fecha']      = pd.to_datetime(df['fecha_inicial'], unit='ms')
        df['year']       = df['fecha'].apply(lambda x: x.year)
        df               = df[(df['valor']>0)]
        df = df[df['year']>2020]
        if not df.empty:
            df1 = df[df['tiponegocio']=='Venta']
            if not df1.empty:
                df1         = df1.groupby('year').agg({'valormt2':['median','count']}).reset_index()
                df1.columns = ['year','valormt2','listings']
                df1         = df1.to_dict(orient='records')
                formato_estadisticas.update({'venta':{'label':'Histórico listings de venta','value':df1}})
            df1 = df[df['tiponegocio']=='Arriendo']
            if not df1.empty:
                df1         = df1.groupby('year').agg({'valormt2':['median','count']}).reset_index()
                df1.columns = ['year','valormt2','listings']
                df1         = df1.to_dict(orient='records')
                formato_estadisticas.update({'arriendo':{'label':'Histórico listings de arriendo','value':df1}})

    # Mapa en 3d
    data_construcciones = data_lotes_completo[1]

    return formato_outputs,data_lote,data_predios,data_transacciones_anotaciones,data_listings,datactl,datalicencias, formato_estadisticas,data_transacciones_historicas, data_construcciones


@st.cache_data(show_spinner=False)
def ubicacion(datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Ubicacion
    dataresultado = pd.DataFrame()
    if not datageneral.empty:
        data      = datageneral.copy()
        datamerge = data[['grupo','barmanpre']]
        formato   = [
            {'column':'general_catastro','variables':['barmanpre','formato_direccion', 'prenbarrio','estrato']},
            {'column':'nombre_ph','variables':['barmanpre','nombre_conjunto']},
            {'column':'localizacion','variables':['barmanpre','locnombre','codigoupl','nombreupl']}
                     ]
        
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[['barmanpre',item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
                df         = pd.DataFrame(df)
                if not df.empty:
                    df.columns = ['formato']
                    df         = pd.json_normalize(df['formato'])
                    if isinstance(variables,list) and variables!=[]:
                        variables = [x for x in variables if x in df]
                        df        = df[variables]
                    datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
                        
        dataresultado = data[['grupo','barmanpre']]
        if not datamerge.empty:
            vargroup      = {'prenbarrio': 'first', 'estrato': 'max', 'locnombre': 'first','codigoupl': 'first','nombreupl': 'first' } 
            vargroup      = {k: v for k, v in vargroup.items() if k in datamerge.columns}
            datapaso      = datamerge.groupby('barmanpre').agg(vargroup).reset_index()
            dataresultado = datapaso.merge(dataresultado,on='barmanpre',how='left',validate='1:1')
            
            for j in ['formato_direccion','nombre_conjunto']:
                if j in datamerge:
                    datapaso         = datamerge[datamerge[j].notnull()]
                    datapaso         = datapaso.drop_duplicates(subset=['barmanpre',j],keep='first')
                    datapaso         = datapaso[['barmanpre',j]]
                    datapaso         = datapaso.groupby('barmanpre')[j].agg(lambda x: ' | '.join(x)).reset_index()
                    datapaso.columns = ['barmanpre',j]
                    dataresultado    = dataresultado.merge(datapaso,on='barmanpre',how='left',validate='1:1')
                    
        #---------------------------------------------------------------------#
        # Agregar resultados cuando hay mas de un lote:
        if not dataresultado.empty and len(dataresultado)>1:
            dataresultado['idmerge'] = 1
            datamerge1 = dataresultado.astype(str).groupby('idmerge')[['barmanpre','grupo','prenbarrio', 'locnombre', 'codigoupl', 'nombreupl', 'formato_direccion']].agg(lambda x: ' | '.join(set(x))).reset_index()
            datamerge2 = dataresultado.groupby('idmerge').agg({'estrato':'max'}).reset_index()
            datamerge1['idmerge'] = datamerge1['idmerge'].astype(int)
            datamerge2['idmerge'] = datamerge2['idmerge'].astype(int)
            dataresultado = datamerge1.merge(datamerge2,on='idmerge',how='outer')
            dataresultado.drop(columns=['idmerge'],inplace=True)
            
        #---------------------------------------------------------------------#
        # Froamto para exportar:
        dataresultado = dataresultado.drop_duplicates(subset='barmanpre',keep='first')
        stdiccionario = diccionario()
        dataresultado = dataresultado.rename(columns=stdiccionario)
        dataresultado = dataresultado.melt(var_name='titulo', value_name='valor')
    
    for i in ["Localidad","UPL","Barrio","Edificio"]:
        if i in dataresultado:
            try: dataresultado[i] = dataresultado[i].apply(lambda x: x.upper())
            except: pass
        
    orden   = {"Dirección":'str',"Localidad":'str',"UPL":'str',"Código UPL":'str',"Barrio":'str',"Barrio catastral":'str',"Estrato":'int',"Edificio":'str'}
    formato = {
    "seccion": "Ubicación",
    "items": []
    }
    if not dataresultado.empty:
        for variable,value in orden.items():
            datapaso = dataresultado[dataresultado['titulo']==variable]
            if not datapaso.empty:
                valor = datapaso['valor'].iloc[0]
                if 'int' in value:
                    try:    valor = f'{int(valor)}'
                    except: pass
                if pd.notna(valor):
                    formato['items'].append({
                        "titulo": f'{variable}:',
                        "valor": valor
                    })
                
    return formato

    
@st.cache_data(show_spinner=False)
def caracteristicas(datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Caracteristicas
    dataresultado = pd.DataFrame()
    if not datageneral.empty:

        data      = datageneral.copy()
        datamerge = data[['grupo','barmanpre']]
        formato   = [
            {'column':'general_catastro','variables':['barmanpre','preaconst', 'predios','connpisos','connsotano','preusoph','prevetustzmin']},
                     ]
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[['barmanpre',item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
                df         = pd.DataFrame(df)
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                if isinstance(variables,list) and variables!=[]:
                    variables = [x for x in variables if x in df]
                    df        = df[variables]
                datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
                        
        dataresultado = data[['grupo','barmanpre']]
        if not datamerge.empty:
            vargroup      = {'preaconst': 'sum', 'predios': 'sum', 'connpisos': 'max','connsotano': 'max','preusoph': 'first','prevetustzmin':'min'} 
            vargroup      = {k: v for k, v in vargroup.items() if k in datamerge.columns}
            datapaso      = datamerge.groupby('barmanpre').agg(vargroup).reset_index()
            dataresultado = datapaso.merge(dataresultado,on='barmanpre',how='left',validate='1:1')
    
        if 'preusoph' in dataresultado: dataresultado['preusoph'] = dataresultado['preusoph'].replace(['S','N'],['Si','No'])

        #---------------------------------------------------------------------#
        # Agregar resultados cuando hay mas de un lote:
        if not dataresultado.empty and len(dataresultado)>1:
            dataresultado['idmerge'] = 1
            datamerge1 = dataresultado.astype(str).groupby('idmerge')[['barmanpre','grupo','preusoph']].agg(lambda x: ' | '.join(set(x))).reset_index()
            datamerge2 = dataresultado.groupby('idmerge').agg({'preaconst':'sum','predios':'sum','connpisos':'max','connsotano':'max','prevetustzmin':['min','max']}).reset_index()
            datamerge2.columns = ['idmerge','preaconst','predios','connpisos','connsotano','prevetustzmin','prevetustzmax']
            datamerge1['idmerge'] = datamerge1['idmerge'].astype(int)
            datamerge2['idmerge'] = datamerge2['idmerge'].astype(int)
            dataresultado = datamerge1.merge(datamerge2,on='idmerge',how='outer')
            dataresultado.drop(columns=['idmerge'],inplace=True)
            dataresultado.rename(columns={'prevetustzmin':'prevetustzmin_min','prevetustzmax':'prevetustzmax_max'},inplace=True)

        #---------------------------------------------------------------------#
        # Froamto para exportar:
        dataresultado = dataresultado.drop_duplicates(subset='barmanpre',keep='first')
        stdiccionario = diccionario()
        dataresultado = dataresultado.rename(columns=stdiccionario)
        dataresultado = dataresultado.melt(var_name='titulo', value_name='valor')
    
    orden   = {'Predios [matrículas independientes]':'int','Pisos':'int', 'Sotanos':'int', 'Área total construida':'miles', 'Antigüedad':'int','Antigüedad mínima':'int', 'Antigüedad máxima':'int', 'PH':'str'}
    formato = {
    "seccion": "Caracteristicas",
    "items": []
    }
    if not dataresultado.empty:
        for variable,value in orden.items():
            datapaso = dataresultado[dataresultado['titulo']==variable]
            if not datapaso.empty:
                valor = datapaso['valor'].iloc[0]
                if 'int' in value:
                    try:    valor = f'{int(valor)}'
                    except: pass
                elif 'miles' in value:
                    try:    valor = "{:,.2f}".format(valor)
                    except: pass
                if pd.notna(valor):
                    formato['items'].append({
                        "titulo": f'{variable}:',
                        "valor": valor
                    })
                
    return formato

@st.cache_data(show_spinner=False)
def terreno(datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Terreno
    dataresultado = pd.DataFrame()
    if not datageneral.empty:
        data      = datageneral.copy()
        datamerge = data[['grupo','barmanpre']]
        formato   = [
            {'column':'info_terreno','variables':['barmanpre','areapolygon', 'frente','esquinero','tipovia']},
            {'column':'general_catastro','variables':['barmanpre','preaterre']},
                     ]
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[['barmanpre',item]]
                df         = df[df[item].notnull()]
                if not df.empty:
                    df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                    df         = df[df[item].notnull()]
                    df         = df.explode(item)
                    df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
                    df         = pd.DataFrame(df)
                    df.columns = ['formato']
                    df         = pd.json_normalize(df['formato'])
                    if isinstance(variables,list) and variables!=[]:
                        variables = [x for x in variables if x in df]
                        df        = df[variables]
                    datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
                        
        if 'areapolygon' in datamerge and 'frente' in datamerge:
            datamerge['fondo'] = datamerge['areapolygon']/datamerge['frente']
            
        dataresultado = data[['grupo','barmanpre']]
        if not datamerge.empty:
            vargroup      = {'areapolygon': 'sum', 'frente': 'sum', 'fondo': 'sum','esquinero': 'max','tipovia': 'min','preaterre':'sum'} 
            vargroup      = {k: v for k, v in vargroup.items() if k in datamerge.columns}
            datapaso      = datamerge.groupby('barmanpre').agg(vargroup).reset_index()
            dataresultado = datapaso.merge(dataresultado,on='barmanpre',how='left',validate='1:1')
    
        if not dataresultado.empty and 'frente' in dataresultado and 'fondo' in dataresultado:
            dataresultado['frente'] = dataresultado['frente'].apply(lambda x: "{:,.1f}".format(x))
            dataresultado['fondo']  = dataresultado['fondo'].apply(lambda x: "{:,.1f}".format(x))
            dataresultado['Frente x Fondo'] = dataresultado.apply(lambda x: f"{x['frente']} x {x['fondo']}",axis=1)
            
        if 'esquinero' in dataresultado:
            idd = dataresultado['esquinero']==1
            dataresultado.loc[idd,'esquinero']  = 'Si'
            dataresultado.loc[~idd,'esquinero'] = 'No'
        if 'tipovia' in dataresultado:
            idd = dataresultado['tipovia']==1
            dataresultado.loc[idd,'tipovia']  = 'Si'
            dataresultado.loc[~idd,'tipovia'] = 'No'
            
            
        #---------------------------------------------------------------------#
        # Agregar resultados cuando hay mas de un lote:
        if not dataresultado.empty and len(dataresultado)>1:
            dataresultado['idmerge'] = 1
            numlotes   = len(dataresultado)
            datamerge1 = dataresultado.astype(str).groupby('idmerge')[['barmanpre','grupo']].agg(lambda x: ' | '.join(set(x))).reset_index()
            datamerge2 = dataresultado.groupby('idmerge').agg({'areapolygon':'sum','preaterre':'sum'}).reset_index()
            datamerge2.columns = ['idmerge','areapolygon','preaterre']
            datamerge1['idmerge'] = datamerge1['idmerge'].astype(int)
            datamerge2['idmerge'] = datamerge2['idmerge'].astype(int)
            
            datamerge3 = pd.DataFrame([{'idmerge':1,
                                        'esquinero': 'Si' if not dataresultado.empty and 'esquinero' in dataresultado and any([x for x in dataresultado['esquinero'].unique() if 'si' in x.lower()]) else 'No' , 
                                        'tipovia': 'Si' if not dataresultado.empty and 'tipovia' in dataresultado and any([x for x in dataresultado['tipovia'].unique() if 'si' in x.lower()]) else 'No' , 
                                        }])
            dataresultado = datamerge1.merge(datamerge2,on='idmerge',how='outer').merge(datamerge3,on='idmerge',how='outer')
            dataresultado.drop(columns=['idmerge'],inplace=True)
            dataresultado['Número de lotes'] = numlotes
            
        #---------------------------------------------------------------------#
        # Froamto para exportar:
        dataresultado = dataresultado.drop_duplicates(subset='barmanpre',keep='first')
        stdiccionario = diccionario()
        dataresultado = dataresultado.rename(columns=stdiccionario)
        dataresultado = dataresultado.melt(var_name='titulo', value_name='valor')
         
    orden   = {'Área del terreno':'miles','Esquinero':'str', 'Vía principal':'str','Frente x Fondo':'str', 'Área del poligono':'miles','Número de lotes':'int'}
    formato = {
    "seccion": "Terreno",
    "items": []
    }
    
    if not dataresultado.empty:
        for variable,value in orden.items():
            datapaso = dataresultado[dataresultado['titulo']==variable]
            if not datapaso.empty:
                valor = datapaso['valor'].iloc[0]
                if 'miles' in value:
                    try:    valor = "{:,.2f}".format(valor)
                    except: pass
                elif 'int' in value:
                    try:    valor = "{:,.0f}".format(valor)
                    except: pass
                if pd.notna(valor):
                    formato['items'].append({
                        "titulo": f'{variable}:',
                        "valor": valor
                    })
    return formato

@st.cache_data(show_spinner=False)
def tipologias(datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Tipologias
    if not datageneral.empty:
        data      = datageneral.copy()
        datamerge = data[['grupo','barmanpre']]
        formato   = [
            {'column':'catastro_byprecuso','variables':['barmanpre','precuso', 'predios_precuso','preaconst_precuso','preaterre_precuso']},
                     ]
        
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[['barmanpre',item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item]), 'barmanpre': x['barmanpre']}, axis=1)
                df         = pd.DataFrame(df)
                df.columns = ['formato']
                df         = pd.json_normalize(df['formato'])
                if isinstance(variables,list) and variables!=[]:
                    variables = [x for x in variables if x in df]
                    df        = df[variables]
                datamerge  = datamerge.merge(df,on='barmanpre',how='outer')
                      
        if not datamerge.empty:
            datamerge               = datamerge.drop_duplicates(subset=['barmanpre','precuso'],keep='first')
            datamerge['proporcion'] = datamerge['preaconst_precuso']/datamerge['preaconst_precuso'].sum()
            datauso,_ = getuso_destino()
            datauso.rename(columns={'codigo':'precuso','tipo':'usosuelo'},inplace=True)
            datauso   = datauso.drop_duplicates(subset='precuso')
            datamerge = datamerge.merge(datauso[['precuso','usosuelo']],on='precuso',how='left',validate='m:1')

    if 'predios_precuso' in datamerge:
        datamerge['predios_precuso'] = datamerge['predios_precuso'].apply(lambda x: int(x) if isinstance(x,(int,float)) else '')
    if 'preaconst_precuso' in datamerge:
        datamerge['preaconst_precuso'] = datamerge['preaconst_precuso'].apply(lambda x: "{:,.1f}".format(x) if isinstance(x,(int,float)) else '')
    if 'proporcion' in datamerge:
        datamerge['proporcion'] = datamerge['proporcion'].apply(lambda x: "{:.2f}%".format(x * 100) if isinstance(x,(int,float)) else '')
    if 'preaterre_precuso' in datamerge:
        datamerge['preaterre_precuso'] = datamerge['preaterre_precuso'].apply(lambda x: "{:,.1f}".format(x) if isinstance(x,(int,float)) else '')

    formato = {
            "seccion": "Tipología",
            "items": []
        }
    if not datamerge.empty:
        datamerge.index = range(len(datamerge))
        formato = {
                "seccion": "Tipología",
                "items": [{
                    "titulo": ' ',
                    "valor": ['Predios','Área construida','Proporción','Área de terreno'],  # Convertimos la columna en una lista
                    }]
            }
        for _,items in datamerge.iterrows():
            item = {
                "titulo": items['usosuelo'],
                "valor": [items['predios_precuso'],items['preaconst_precuso'],items['proporcion'],items['preaterre_precuso']]  # Convertimos la columna en una lista
            }
            formato["items"].append(item)
 
    return formato

@st.cache_data(show_spinner=False)
def infopredial(datapredialesactuales,datageneral):
    #-------------------------------------------------------------------------#
    # Seccion: Informacion Predial
    datapaso1 = pd.DataFrame(columns = ['barmanpre', 'avaluomt2_const', 'predialmt2_const', 'avaluomt2_terre', 'predialmt2_terre'])
    if not datapredialesactuales.empty:
        try:
            df         = datapredialesactuales.copy()
            df['prediales_mt2'] = df['prediales_mt2'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df['prediales_mt2'].notnull()]
            df         = df.explode('prediales_mt2')
            df         = df.apply(lambda x: {**(x['prediales_mt2']), 'barmanpre': x['barmanpre']}, axis=1)
            df         = pd.DataFrame(df)
            df.columns = ['formato']
            datapaso1  = pd.json_normalize(df['formato'])
        except: pass

    datapaso2 = pd.DataFrame(columns = ['barmanpre', 'propietarios', 'avaluo_catastral', 'impuesto_predial', 'avaluomt2const', 'predialmt2const', 'avaluomt2terre', 'predialmt2terre'])
    if not datageneral.empty:
        try:
            df         = datageneral.copy()
            df['infopredial'] = df['infopredial'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
            df         = df[df['infopredial'].notnull()]
            df         = df.explode('infopredial')
            df         = df.apply(lambda x: {**(x['infopredial']), 'barmanpre': x['barmanpre']}, axis=1)
            df         = pd.DataFrame(df)
            df.columns = ['formato']
            datapaso2  = pd.json_normalize(df['formato'])
        except: pass
    datapaso         = datapaso1.merge(datapaso2,on='barmanpre',how='outer')
    columnas_excluir = ['barmanpre','grupo']
    for col in datapaso1.columns:
        if col not in columnas_excluir and col in datapaso2.columns:
            if f'{col}_x' and f'{col}_y':
                datapaso[col] = datapaso[f'{col}_x'].fillna(datapaso[f'{col}_y'])
                datapaso.drop(columns=[f'{col}_x', f'{col}_y'], inplace=True)
    
    #---------------------------------------------------------------------#
    # Agregar resultados cuando hay mas de un lote:
    if not datapaso.empty and len(datapaso)>1:
        datapaso['idmerge'] = 1
        
        jsonvar = {'avaluo_catastral':'sum','impuesto_predial':'sum','propietarios':'sum','avaluomt2_const':'max','predialmt2_const':'max','avaluomt2_terre':'max','predialmt2_terre':'max','avaluomt2const':'max','predialmt2const':'max','avaluomt2terre':'max','predialmt2terre':'max'}
        jsonvar = {k: v for k, v in jsonvar.items() if k in list(datapaso)}
        
        datamerge1 = datapaso.astype(str).groupby('idmerge')[['barmanpre']].agg(lambda x: ' | '.join(set(x))).reset_index()
        datamerge2 = datapaso.groupby('idmerge').agg(jsonvar).reset_index()
        variables  = [x for x in ['idmerge','avaluo_catastral','impuesto_predial','propietarios','avaluomt2_const','predialmt2_const','avaluomt2_terre','predialmt2_terre','avaluomt2const', 'predialmt2const', 'avaluomt2terre', 'predialmt2terre'] if x in datamerge2]
        datamerge2 = datamerge2[variables] 
        datamerge1['idmerge'] = datamerge1['idmerge'].astype(int)
        datamerge2['idmerge'] = datamerge2['idmerge'].astype(int)
        datapaso              = datamerge1.merge(datamerge2,on='idmerge',how='outer')
        datapaso.drop(columns=['idmerge'],inplace=True)

    dataresultado = pd.DataFrame()
    if not datapaso.empty:
        for i in ['avaluomt2_const', 'predialmt2_const', 'avaluomt2_terre', 'predialmt2_terre','avaluomt2const', 'predialmt2const', 'avaluomt2terre', 'predialmt2terre']:
            if i not in datapaso: datapaso[i] = None
            
        datapaso['avaluomt2const']  = datapaso.apply(lambda x: getmaxitem(x['avaluomt2const'],x['avaluomt2_const']),axis=1)
        datapaso['predialmt2const'] = datapaso.apply(lambda x: getmaxitem(x['predialmt2const'],x['predialmt2_const']),axis=1)
        datapaso['avaluomt2terre']  = datapaso.apply(lambda x: getmaxitem(x['avaluomt2terre'],x['avaluomt2_terre']),axis=1)
        datapaso['predialmt2terre'] = datapaso.apply(lambda x: getmaxitem(x['predialmt2terre'],x['predialmt2_terre']),axis=1)
        datapaso                    = datapaso.groupby('barmanpre').agg({'propietarios':'sum','avaluomt2const':'max','predialmt2const':'max','avaluomt2terre':'max','predialmt2terre':'max','avaluo_catastral':'max','impuesto_predial':'max'}).reset_index()
        
        for i in ['avaluomt2const', 'predialmt2const', 'avaluomt2terre', 'predialmt2terre', 'avaluo_catastral', 'impuesto_predial']:
            if i in datapaso:
                datapaso[i] = datapaso[i].apply(lambda x: "${:,.0f}".format(x) if isinstance(x,(float,int)) else '')
        for i in ['propietarios']:
            if i in datapaso:
                datapaso[i] = datapaso[i].apply(lambda x: int(x) if isinstance(x,(float,int)) else '')
               
        #---------------------------------------------------------------------#
        # Froamto para exportar:
        dataresultado = datapaso.drop_duplicates(subset='barmanpre',keep='first')
        stdiccionario = diccionario()
        dataresultado = dataresultado.rename(columns=stdiccionario)
        dataresultado = dataresultado.melt(var_name='titulo', value_name='valor')
        
    orden   = ['Avalúo catastral por m²','Predial por m²','Propietarios','Avalúo catastral total','Impuesto predial total','Avalúo catastral del suelo por m²','Predial del suelo por m²']
    formato = {
    "seccion": "Información Predial",
    "items": []
    }
    
    # Iteramos sobre la lista de variables deseadas
    if not dataresultado.empty:
        for variable in orden:
            datapaso = dataresultado[dataresultado['titulo']==variable]
            if not datapaso.empty:
                valor = datapaso['valor'].iloc[0]
                if pd.notna(valor):
                    formato['items'].append({
                        "titulo": f'{variable}:',
                        "valor": valor
                    })
                
    return formato

@st.cache_data(show_spinner=False)
def transacciones(datatransacciones):
    
    #-------------------------------------------------------------------------#
    # Seccion: Terreno
    formato = {
    "seccion": "Transacciones",
    "items": []
    }
    try:
        df                      = datatransacciones.copy()
        df['transacciones_12m'] = df['transacciones_12m'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df.explode('transacciones_12m')
        df         = df.apply(lambda x: {**(x['transacciones_12m'])}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
        formato['items'].append({'titulo': 'Último año', 'valor': ''})
        formato['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(df['cuantiamt2'].median())  if 'cuantiamt2' in df  else 'Sin información'})
        formato['items'].append({'titulo': 'Total compraventas y/o leasing:', 'valor': "{:,.0f}".format(int(df['conteo'].sum()))  })
    except: 
        formato['items'].append({'titulo': 'Último año', 'valor': ''})
        formato['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
        formato['items'].append({'titulo': 'Total compraventas y/o leasing:', 'valor': 'Sin información'})

    try:
        df                             = datatransacciones.copy()
        df['transacciones_historicas'] = df['transacciones_historicas'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df.explode('transacciones_historicas')
        df         = df.apply(lambda x: {**(x['transacciones_historicas'])}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
        formato['items'].append({'titulo': 'Desde el 2019 a la fecha', 'valor': ''})
        formato['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(df['cuantiamt2'].median())  if 'cuantiamt2' in df else 'Sin información'})
        formato['items'].append({'titulo': 'Total compraventas y/o leasing:', 'valor': "{:,.0f}".format(int(df['conteo'].sum()))})
    except: 
        formato['items'].append({'titulo': 'Desde el 2019 a la fecha', 'valor': ''})
        formato['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
        formato['items'].append({'titulo': 'Total compraventas y/o leasing:', 'valor': 'Sin información'})

    return formato

@st.cache_data(show_spinner=False)
def pot(data):
    #-------------------------------------------------------------------------#
    # Seccion: POT
    formato = {
    "seccion": "P.O.T",
    "items": []
    }
    try:
        df         = data.copy()
        df['POT']  = df['POT'].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
        df         = df.explode('POT')
        df         = df.apply(lambda x: {**(x['POT'])}, axis=1)
        df         = pd.DataFrame(df)
        df.columns = ['formato']
        df         = pd.json_normalize(df['formato'])
    except: df = pd.DataFrame()
    
    formatovar = [
        {'label':'Tratamiento Urbanistico:','variable':'tratamiento_urbanistico','lista':[{'label':'Tipo de tratamiento','variable':'nombretra'},{'label':'Tipología','variable':'tipologia'},{'label':'Altura máx','variable':'alturamax'},{'label':'Acto admin','variable':'numeroact'}],'defecto':'Sin información' },
        {'label':'Área de actividad:','variable':'area_actividad','lista':[{'label':'Nombre','variable':'nombreare'}],'defecto':'No aplica'},
        {'label':'Actuación Estratégica:','variable':'actuacion_estrategica','lista':[{'label':'Nombre','variable':'nombre'},{'label':'Priorización','variable':'priorizaci'}],'defecto':'No aplica'},
        {'label':'Antejardín:','variable':'antejardin','lista':[{'label':'Dimensión','variable':'dimension'},{'label':'Observación','variable':'observacio'}],'defecto':'Sin información'}             
        ]
    
    for i in formatovar:
        lista = i['lista']
        if i['variable'] in df:
            try:
                try: 
                    inputs         = df[[i['variable']]].copy()
                    inputs         = inputs.explode(i['variable'])
                    inputs         = inputs.apply(lambda x: {**(x[i['variable']])}, axis=1)
                    inputs         = pd.DataFrame(inputs)
                    inputs.columns = ['formato']
                    inputs         = pd.json_normalize(inputs['formato'])
                    inputs['idmerge'] = 1
                    inputs         = inputs.astype(str).groupby('idmerge').agg(lambda x: ' | '.join(set([w for w in x if not pd.isna(w)]))).reset_index()
                    inputs         = inputs.to_dict(orient='records')
                except:
                    try:  inputs = df[i['variable']].iloc[0]
                    except: 
                        try: inputs = json.loads(df[i['variable']].iloc[0])
                        except: inputs = None
                if isinstance(inputs, list) or isinstance(inputs, dict):
                    formato['items'].append({'titulo': f"{i['label']}", 'valor': ''})
                    for j in inputs: 
                        for s in lista: 
                            w = [x for x in list(j) if s['variable'] in x]
                            if isinstance(w,list) and w!=[]:
                                if not pd.isna(j[w[0]]):
                                    formato['items'].append({'titulo':s['label'], 'valor': j[w[0]]})
                                else: 
                                    formato['items'].append({'titulo':s['label'], 'valor': 'No aplica'})
                else:
                    respdefecto = i['defecto']
                    formato['items'].append({'titulo': f"{i['label']}", 'valor': respdefecto})
            except: 
                respdefecto = i['defecto']
                formato['items'].append({'titulo': f"{i['label']}", 'valor': respdefecto})
        else:
            respdefecto = i['defecto']
            formato['items'].append({'titulo': f"{i['label']}", 'valor': respdefecto})
        
    formato =  limpiar_json(formato)
    return formato

@st.cache_data(show_spinner=False)
def listings(data):
            
    formato_venta = {
    "seccion": "Precios de Referencia en Venta",
    "items": []
    }
    if not data.empty:
        data             = data.sort_values(by=['code','activo'],ascending=False).drop_duplicates(subset='code',keep='first')
        data['valormt2'] = data['valor']/data['areaconstruida']
        dataactivo       = data[(data['activo']==1) & (data['tiponegocio']=='Venta')]
        datahistorico    = data[(data['activo']==0) & (data['tiponegocio']=='Venta')]
        if not dataactivo.empty:
            formato_venta['items'].append({'titulo': 'Listings Activos:', 'valor': ''})
            formato_venta['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(dataactivo['valormt2'].median()) if 'valormt2' in dataactivo and isinstance(dataactivo['valormt2'].median(),(float,int)) and dataactivo['valormt2'].median()>0 else  'Sin información'})
            formato_venta['items'].append({'titulo': '# de listings:', 'valor': int(len(dataactivo)) if len(dataactivo)>0 else 'Sin información'})
            
        else:
            formato_venta['items'].append({'titulo': 'Listings Activos:', 'valor': ''})
            formato_venta['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
            formato_venta['items'].append({'titulo': '# de listings:', 'valor': 'Sin información'})

        if not datahistorico.empty:
            formato_venta['items'].append({'titulo': 'Listings No Activoss:', 'valor': ''})
            formato_venta['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(datahistorico['valormt2'].median()) if 'valormt2' in datahistorico and isinstance(datahistorico['valormt2'].median(),(float,int))  and datahistorico['valormt2'].median()>0 else  'Sin información'})
            formato_venta['items'].append({'titulo': '# de listings:', 'valor': int(len(datahistorico)) if len(datahistorico)>0 else 'Sin información' })
            
        else:
            formato_venta['items'].append({'titulo': 'Listings No Activoss:', 'valor': ''})
            formato_venta['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
            formato_venta['items'].append({'titulo': '# de listings:', 'valor': 'Sin información'})

    formato_arriendo = {
    "seccion": "Precios de Referencia en Arriendo",
    "items": []
    }
    if not data.empty:
        dataactivo    = data[(data['activo']==1) & (data['tiponegocio']=='Arriendo')]
        datahistorico = data[(data['activo']==0) & (data['tiponegocio']=='Arriendo')]
        if not dataactivo.empty:
            formato_arriendo['items'].append({'titulo': 'Listings Activos:', 'valor': ''})
            formato_arriendo['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(dataactivo['valormt2'].median()) if 'valormt2' in dataactivo and isinstance(dataactivo['valormt2'].median(),(float,int)) and dataactivo['valormt2'].median()>0 else  'Sin información'})
            formato_arriendo['items'].append({'titulo': '# de listings:', 'valor': len(dataactivo) if len(dataactivo)>0 else 'Sin información'})
            
        else:
            formato_arriendo['items'].append({'titulo': 'Listings Activos:', 'valor': ''})
            formato_arriendo['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
            formato_arriendo['items'].append({'titulo': '# de listings:', 'valor': 'Sin información'})

        if not datahistorico.empty:
            formato_arriendo['items'].append({'titulo': 'Listings No Activoss:', 'valor': ''})
            formato_arriendo['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(datahistorico['valormt2'].median()) if 'valormt2' in datahistorico and isinstance(datahistorico['valormt2'].median(),(float,int))  and datahistorico['valormt2'].median()>0 else  'Sin información'})
            formato_arriendo['items'].append({'titulo': '# de listings:', 'valor': int(len(datahistorico)) if len(datahistorico)>0 else 'Sin información'})
            
        else:
            formato_arriendo['items'].append({'titulo': 'Listings No Activoss:', 'valor': ''})
            formato_arriendo['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
            formato_arriendo['items'].append({'titulo': '# de listings:', 'valor': 'Sin información'})
            
    return formato_venta,formato_arriendo
    
@st.cache_data(show_spinner=False)
def listings_estadisticas(data_estadisticas_barrio=pd.DataFrame(),data_valorizacion_barrio=pd.DataFrame(),barrio=None):
            
    formato_salida = {
    "seccion": f"Valores de referencia ({barrio})" if isinstance(barrio,str) and barrio!='' else "Valores de referencia",
    "items": []
    }
    datavalue        = data_estadisticas_barrio[data_estadisticas_barrio['tiponegocio']=='Venta']
    datavalorizacion = data_valorizacion_barrio[data_valorizacion_barrio['tiponegocio']=='Venta']
    formato_salida['items'].append({'titulo': 'Venta:', 'valor': ''})

    if not datavalue.empty:
        formato_salida['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(datavalue['valormt2'].iloc[0]) if 'valormt2' in datavalue and isinstance(datavalue['valormt2'].iloc[0],(float,int)) and datavalue['valormt2'].iloc[0]>0 else  'Sin información'})
    else:
        formato_salida['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
        
    if not datavalorizacion.empty:
        formato_salida['items'].append({'titulo': 'Valorización:', 'valor': "{:.2f}%".format(datavalorizacion['valorizacion'].iloc[0]*100) if 'valorizacion' in datavalorizacion and isinstance(datavalorizacion['valorizacion'].iloc[0],(float,int))  else  'Sin información'})
    else:
        formato_salida['items'].append({'titulo': 'Valorización:', 'valor': 'Sin información'})
 
    datavalue        = data_estadisticas_barrio[data_estadisticas_barrio['tiponegocio']=='Arriendo']
    datavalorizacion = data_valorizacion_barrio[data_valorizacion_barrio['tiponegocio']=='Arriendo']
    formato_salida['items'].append({'titulo': 'Arriendo:', 'valor': ''})

    if not datavalue.empty:
        formato_salida['items'].append({'titulo': 'Valor promedio m²:', 'valor': "${:,.0f}".format(datavalue['valormt2'].iloc[0]) if 'valormt2' in datavalue and isinstance(datavalue['valormt2'].iloc[0],(float,int)) and datavalue['valormt2'].iloc[0]>0 else  'Sin información'})
    else:
        formato_salida['items'].append({'titulo': 'Valor promedio m²:', 'valor': 'Sin información'})
        
    if not datavalorizacion.empty:
        formato_salida['items'].append({'titulo': 'Valorización:', 'valor': "{:.2f}%".format(datavalorizacion['valorizacion'].iloc[0]*100) if 'valorizacion' in datavalorizacion and isinstance(datavalorizacion['valorizacion'].iloc[0],(float,int))  else  'Sin información'})
    else:
        formato_salida['items'].append({'titulo': 'Valorización:', 'valor': 'Sin información'})
 
    return formato_salida

@st.cache_data(show_spinner=False)
def dane(datadane,barrio=None):
    #-------------------------------------------------------------------------#
    # Seccion: Ubicacion
    dataresultado = pd.DataFrame()
    if not datadane.empty:
        data      = datadane.copy()
        formato   = [
            {'column':'dane','variables':['barmanpre','Total personas','Total viviendas','Hogares', 'Hombres','Mujeres']},
                     ]
        dataresultado = pd.DataFrame()
        for i in formato:
            item       = i['column']
            variables  = i['variables']
            if item in data:
                df         = data[[item]]
                df         = df[df[item].notnull()]
                df[item]   = df[item].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
                df         = df[df[item].notnull()]
                df         = df.explode(item)
                df         = df.apply(lambda x: {**(x[item])}, axis=1)
                df         = pd.DataFrame(df)
                if not df.empty:
                    df.columns = ['formato']
                    df         = pd.json_normalize(df['formato'])
                    if isinstance(variables,list) and variables!=[]:
                        variables     = [x for x in variables if x in df]
                        dataresultado = df[variables]
                        dataresultado.index = range(len(dataresultado))
                        
                        factor_expansion = 1.08 # Chatgpt: estoy trabajando con la data del dane de colombia del censo poblacional, pero como es del 2018 queria saber si sabes que factor de expansion le puedo hacer para e l2024, se que el dane tiene esas cifras, necesito un unico valor, un proxi para poder calcular la poblacion en un radio, ya tengo el valor de la poblacion de 2018 para ese radio pero quiero una proyeccion, las tienes? 
                        for j in list(dataresultado):
                            valor = dataresultado[j].iloc[0]
                            if isinstance(valor,(float,int)): 
                                dataresultado.loc[0,j] = valor*factor_expansion
                            elif  isinstance(valor,str):
                                try:
                                    valor = int(valor)*factor_expansion
                                    dataresultado.loc[0,j] = int(valor)
                                except: pass
                            
    orden   = ['Total personas', 'Total viviendas', 'Hogares', 'Hombres', 'Mujeres']
    formato = {
    "seccion": f"Información Demográfica ({barrio})" if isinstance(barrio,str) and barrio!='' else "Información Demográfica",
    "items": []
    }
    if not dataresultado.empty:
        dataresultado = dataresultado.melt(var_name='titulo', value_name='valor')
        for variable in orden:
            datapaso = dataresultado[dataresultado['titulo']==variable]
            if not datapaso.empty:
                valor = datapaso['valor'].iloc[0]
                if pd.notna(valor):
                    formato['items'].append({
                        "titulo": f'{variable}:',
                        "valor": "{:,.0f}".format(valor) if isinstance(valor,(int,float)) else 'Sin información'
                    })
                
    return formato

@st.cache_data(show_spinner=False)
def diccionario():
    
    stdiccionario = {
    'formato_direccion': 'Dirección',
    'nombre_conjunto': 'Edificio',   
    'locnombre':'Localidad',
    'prenbarrio': 'Barrio catastral',
    'estrato':'Estrato',
    'codigoupl':'Código UPL',
    'nombreupl':'UPL',
    'preaconst':'Área total construida',
    'predios':'Predios [matrículas independientes]',
    'connpisos':'Pisos',
    'connsotano':'Sotanos',
    'preusoph':'PH',
    'prevetustzmin':'Antigüedad',
    'prevetustzmax':'Antigüedad',
    'prevetustzmin_min':'Antigüedad mínima',
    'prevetustzmax_max':'Antigüedad máxima',
    'areapolygon':'Área del poligono',
    'frente':'Frente',
    'fondo':'Fondo',
    'esquinero':'Esquinero',
    'tipovia':'Vía principal',
    'preaterre':'Área del terreno',
    'avaluomt2const':'Avalúo catastral por m²',
    'predialmt2const':'Predial por m²',
    'avaluomt2terre':'Avalúo catastral del suelo por m²',
    'predialmt2terre':'Predial del suelo por m²',
    'avaluo_catastral':'Avalúo catastral total',
    'impuesto_predial':'Impuesto predial total',
    'propietarios':'Propietarios',
    }
    
    return stdiccionario

def getmaxitem(x1,x2): 
    if pd.api.types.is_numeric_dtype(type(x1)) and pd.api.types.is_numeric_dtype(type(x2)):
        if not pd.isna(x1) and not pd.isna(x2):
            return max(x1, x2)
        elif not pd.isna(x1): 
            return x1
        elif not pd.isna(x2):
            return x2
    elif pd.api.types.is_numeric_dtype(type(x1)) and not pd.isna(x1):  # Solo x1 es numérico
        return x1
    elif pd.api.types.is_numeric_dtype(type(x2)) and not pd.isna(x2):  # Solo x2 es numérico
        return x2
    return None


def limpiar_json(data):
    valores_nulos = {'none', 'n/a', 'nan', 'null'}
    if isinstance(data, dict):
        return {key: limpiar_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [limpiar_json(item) for item in data]
    else:
        str_value = str(data).lower().strip()
        if str_value in valores_nulos:
            return "No aplica"
        return data
    