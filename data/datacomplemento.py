import streamlit as st
import pandas as pd
import shapely.wkt as wkt
from sqlalchemy import create_engine 
from shapely.geometry import Polygon
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
def main(barmanpre=None,latitud=None,longitud=None,direccion=None,polygon=None,precuso=None):
    
    outputs    = {}
    databarrio = pd.DataFrame()
    mpioccdgo  = None
    scacodigo  = None
    
    #-------------------------------------------------------------------------#
    # Latitud y Longitud 
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        
        #---------------------------------------------------------------------#
        # Municipio
        datampio = pd.read_sql_query(f"SELECT mpio_ccdgo as mpioccdgo  FROM  bigdata.data_municipios WHERE ST_CONTAINS(geometry,Point({longitud},{latitud})) LIMIT 1" , engine)
        if not datampio.empty:
            mpioccdgo = datampio['mpioccdgo'].iloc[0]
            outputs.update({'mpioccdgo':mpioccdgo})

        #---------------------------------------------------------------------#
        # Localidad
        datalocalidad = pd.read_sql_query(f"SELECT locnombre as localidad FROM  bigdata.data_bogota_localidades WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        if not datalocalidad.empty:
            outputs.update({'localidad':datalocalidad['localidad'].iloc[0]})

        #---------------------------------------------------------------------#
        # Barrio
        databarrio = pd.read_sql_query(f"SELECT scacodigo,scanombre FROM  bigdata.data_bogota_barriocatastro WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        if not databarrio.empty:
            scacodigo = databarrio['scacodigo'].iloc[0]
            outputs.update({'barrio':databarrio['scanombre'].iloc[0],'scacodigo':scacodigo})
            
        #---------------------------------------------------------------------#
        # UPL
        dataupl = pd.read_sql_query(f"SELECT codigoupl as codigoupl, nombre as upl FROM  pot.bogota_unidadplaneamientolocal WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        if not dataupl.empty:
            outputs.update(dataupl.iloc[0].to_dict())

        #---------------------------------------------------------------------#
        # POT        
        datapot = point2POT(latitud,longitud)
        outputs.update({'POT':datapot})
        
        #---------------------------------------------------------------------#
        # barrio        
        databarrio = pd.read_sql_query(f"SELECT scanombre as barrio,ST_AsText(geometry) as wkt FROM  bigdata.data_bogota_barriocatastro WHERE ST_CONTAINS(geometry,Point({longitud},{latitud}))" , engine)
        if not databarrio.empty and 'wkt' in databarrio:
            try: 
                polygon   = Polygon(wkt.loads(databarrio['wkt'].iloc[0]))
                polygon   = polygon.simplify(tolerance=0.1,preserve_topology = True)
                df        = censodane(str(polygon))
                variables = [x for x in ['Total personas','Total viviendas','Hogares','Hombres','Mujeres'] if x in df]
                if variables!=[]:
                    df = df[variables]
                    outputs.update({'dane':df.iloc[0].to_dict()})
            except: pass
        
        #---------------------------------------------------------------------#
        # Transmilenio 
        datatransmilenio = pd.read_sql_query(f"SELECT nombreest,latitud,longitud, ST_Distance_Sphere(geometry, Point({longitud},{latitud})) AS distance FROM bigdata.data_bogota_transmilenio ORDER BY distance", engine)
        if not datatransmilenio.empty:
            idd = datatransmilenio['distance']<1000
            if sum(idd)>0:
                datatransmilenio = datatransmilenio[idd]
            else: 
                datatransmilenio = datatransmilenio.iloc[0:2,:]
    
        if not datatransmilenio.empty:
            try: 
                datatransmilenio['distance'] = datatransmilenio['distance'].astype(int)
                datatransmilenio['match'] = datatransmilenio.apply(lambda x: f"{x['nombreest']} a {x['distance']} mt ",axis=1)
                outputs.update({'transmilenio':'| '.join(datatransmilenio['match'].unique())})
            except: 
                pass
            
        #---------------------------------------------------------------------#
        # SITP 
        datasitp = pd.read_sql_query(f"SELECT direccpar,latitud,longitud, ST_Distance_Sphere(geometry, Point({longitud},{latitud})) AS distance FROM bigdata.data_bogota_sitp HAVING distance < 501 ORDER BY distance ", engine)
        if not datasitp.empty:
            idd = datasitp['distance']<500
            if sum(idd)>0:
                datasitp = datasitp[idd].iloc[0:2,:]
            else: 
                datasitp = datasitp.iloc[0:2,:]
    
        if not datasitp.empty:
            try: 
                datasitp['distance'] = datasitp['distance'].astype(int)
                datasitp['match']    = datasitp.apply(lambda x: f"{x['direccpar']} a {x['distance']} mt ",axis=1)
                outputs.update({'sitp':'| '.join(datasitp['match'].unique())})
            except:  pass

    #-------------------------------------------------------------------------#
    # Barmanpre
    datalote    = pd.DataFrame()
    datafrente  = pd.DataFrame()
    direcciones = pd.DataFrame()
    if isinstance(barmanpre, str):
        datalote    = pd.read_sql_query(f"SELECT  esquinero, nombre, nombretipo, tipo_via FROM bigdata.bogota_via_lote WHERE barmanpre='{barmanpre}'" , engine)
        datafrente  = pd.read_sql_query(f"SELECT arealinea as areafrente, areapolygon as areaterreno FROM bigdata.bogota_frente_fondo_esquinero WHERE barmanpre='{barmanpre}'" , engine)
        direcciones = pd.read_sql_query(f"SELECT coddir, MIN(predirecc) as formato_direccion, MIN(preusoph) as preusoph FROM bigdata.data_bogota_catastro WHERE barmanpre='{barmanpre}' GROUP BY coddir" , engine)
    elif isinstance(barmanpre, list):
        query       = "','".join(barmanpre)
        query       = f" barmanpre IN ('{query}')"
        datalote    = pd.read_sql_query(f"SELECT  esquinero, nombre, nombretipo, tipo_via FROM bigdata.bogota_via_lote WHERE {query}" , engine)
        datafrente  = pd.read_sql_query(f"SELECT arealinea as areafrente, areapolygon as areaterreno FROM bigdata.bogota_frente_fondo_esquinero WHERE {query}" , engine)
        direcciones = pd.read_sql_query(f"SELECT coddir, MIN(predirecc) as formato_direccion, MIN(preusoph) as preusoph FROM bigdata.data_bogota_catastro WHERE {query} GROUP BY coddir" , engine)

    #-------------------------------------------------------------------------#
    # Altura maxima de lo construido en la manzana
    datamanzana   = pd.DataFrame()
    codigomanzana = None
    if isinstance(barmanpre, str):
        codigomanzana = [barmanpre[0:9]]
    elif isinstance(barmanpre, list):
        codigomanzana = [x[0:9] for x in barmanpre if isinstance(x,str)]
        codigomanzana = list(set(codigomanzana))
    
    if isinstance(codigomanzana,list): 
        query       = "','".join(codigomanzana)
        query       = f" mancodigo IN ('{query}')"
        datamanzana = pd.read_sql_query(f"SELECT max(connpisos) as alturamax FROM  bigdata.bogota_mancodigo_general WHERE {query}" , engine)
        if not datamanzana.empty:
            outputs.update({'alturamax':datamanzana['alturamax'].iloc[0]})
            
    #---------------------------------------------------------------------#
    # Vias
    if not datalote.empty:
        esquinero    = datalote['esquinero'].max()
        esquinero    = 'Si' if esquinero==1 else 'No'
        viaprincipal = 'No' 
        idd          = datalote['nombretipo'].str.lower().str.contains('principal')
        if sum(idd)>0: viaprincipal = 'Si' 
        outputs.update({'esquinero':esquinero,'viaprincipal':viaprincipal})
        
        vias = datalote[datalote['nombre'].notnull()]
        if not vias.empty:
            vias = "| ".join(vias['nombre'].astype(str).unique())
            outputs.update({'vias':vias})

    #---------------------------------------------------------------------#
    # Fondo
    if not datafrente.empty:
        try:    areapoligono = round(datafrente['areaterreno'].iloc[0],2)
        except: areapoligono = None
        try:    areafrente   = round(datafrente['areafrente'].iloc[0],2)
        except: areafrente   = None
        try:    areafondo    = round(areapoligono/areafrente,2)
        except: areafondo    = None
        outputs.update({'areapoligono':areapoligono,'areafrente':areafrente,'areafondo':areafondo})
                    
    #---------------------------------------------------------------------#
    # Direcciones
    if not direcciones.empty and len(direcciones)>1:
        direcciones['formato_direccion'] = direcciones['formato_direccion'].apply(lambda x: formato_direccion(x))
        direccion = list(direcciones['formato_direccion'].unique())
        outputs.update({'direccion':' | '.join(direccion)})
    
    #---------------------------------------------------------------------#
    # PH
    if not direcciones.empty:
        direcciones['preusophr'] = direcciones['preusoph'].replace({'S': 1, 'N': 0})
        direcciones['preusoph']  = direcciones['preusoph'].replace({'S': 'Si', 'N': 'No'})
        direcciones              = direcciones.sort_values(by='preusophr',ascending=False)
        direcciones.reset_index(drop=True, inplace=True)
        outputs.update({'ph':direcciones['preusoph'].iloc[0]})
        
    #-------------------------------------------------------------------------#
    # Direccion
    if isinstance(direccion, list):
        #---------------------------------------------------------------------#
        # Nombre de conjunto
        query = ''
        for i in direccion:
            query += f" OR coddir='{coddir(i)}'" 
        if query!='':
            query        = query.strip().strip('OR').strip()
            dataconjunto = pd.read_sql_query(f"SELECT nombre_conjunto FROM bigdata.bogota_nombre_conjuntos WHERE {query}" , engine)
            if not dataconjunto.empty:
                outputs.update({'nombre_conjunto' :' | '.join(dataconjunto['nombre_conjunto'].unique())})
        
    if isinstance(direccion, str):
        fcoddir = coddir(direccion)
        #---------------------------------------------------------------------#
        # Nombre de conjunto
        dataconjunto = pd.read_sql_query(f"SELECT nombre_conjunto FROM bigdata.bogota_nombre_conjuntos WHERE coddir='{fcoddir}'" , engine)
        if not dataconjunto.empty:
            outputs.update(dataconjunto.iloc[0].to_dict())
            

    #-------------------------------------------------------------------------#
    # Oferta en el edificio
    outputs = buildingMarketValues(outputs,direccion,precuso=precuso,mpioccdgo=mpioccdgo)

    #-------------------------------------------------------------------------#
    # Valorizacion
    #outputs = MarketValorizacion(outputs,latitud=latitud,longitud=longitud,precuso=precuso,areamin=0,areamax=0)
    if scacodigo is not None:
        query = f" scacodigo='{scacodigo}' "
        if precuso is not None:
            tipoinmueble = usosuelo2inmueble(precuso)
            tipoinmueble = "','".join(tipoinmueble)
            query       += f" AND tipoinmueble IN ('{tipoinmueble}')"
            
        trimestre_actual   = pd.Timestamp.now()
        trimestre_anterior = trimestre_actual - relativedelta(months=3)
        query             += f" AND trimestre IN ('{trimestre_actual.to_period('Q').strftime('%YQ%q')}','{trimestre_anterior.to_period('Q').strftime('%YQ%q')}')"
        datavalorizacion   = pd.read_sql_query(f"SELECT * FROM bigdata.data_bogota_valorizacion WHERE {query}" , engine)
        if not datavalorizacion.empty:
            datavalorizacion = datavalorizacion.sort_values(by=['tiponegocio', 'tipoinmueble', 'trimestre'],ascending=True)
            datavalorizacion = datavalorizacion[datavalorizacion['valorizacion'].notnull()]
            
            # Nos quedamos con el ultimo trimestre completo
            datavalorizacion = datavalorizacion.drop_duplicates(subset=['tiponegocio', 'tipoinmueble'],keep='first')
            datavalorizacion = datavalorizacion[['tiponegocio', 'tipoinmueble', 'valormt2', 'valorizacion']]
            outputs.update({'valorizacion':datavalorizacion.to_dict(orient='records')})

    engine.dispose()
    return outputs

@st.cache_data(show_spinner=False)
def buildingMarketValues(outputs,direccion,precuso=None,mpioccdgo=None):
    
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
        datamarketactivos   = pd.read_sql_query(f"SELECT code,valor,tiponegocio,areaconstruida,valoradministracion FROM bigdata.market_portales_activos WHERE {query}" , engine)
        datamarkethistorico = pd.read_sql_query(f"SELECT code,valor,tiponegocio,areaconstruida,valoradministracion FROM bigdata.market_portales_historico WHERE {query}" , engine)
        
        # Eliminar los inmuebles activos de la data historica para el analisis
        idd                 = datamarkethistorico['code'].isin(datamarketactivos['code'])
        datamarkethistorico = datamarkethistorico[~idd]
        
        #---------------------------------------------------------------------#
        # Administracion
        valoradministracion = []
        for jdata in [datamarketactivos,datamarkethistorico]:
            if jdata.empty:
                datapaso = jdata[jdata['valoradministracion'].notnull()]
                if not datapaso.empty:
                    datapaso['admonmt2'] = datapaso['valoradministracion']/datapaso['areaconstruida']
                    valoradministracion.append(datapaso['admonmt2'].median())
                    
        if valoradministracion!=[]:
            #if len(valoradministracion)==2: valoradministracion = 0.6*valoradministracion[0]+0.4*valoradministracion[1]
            #else: valoradministracion = valoradministracion[0]
            outputs.update({'administracion':valoradministracion[0]})

        #---------------------------------------------------------------------#
        # Ofertas en el mismo barmanpre
        if not datamarketactivos.empty:
            datamarketactivos['valormt2'] = datamarketactivos['valor']/datamarketactivos['areaconstruida']
            datamarketactivos = datamarketactivos.groupby(['tiponegocio']).agg({'valormt2':'median','areaconstruida':'count'}).reset_index()
            datamarketactivos.columns = ['tiponegocio','valor','obs']
            datamarketactivos['tipo'] = 'activos'
            datamarket = pd.concat([datamarket,datamarketactivos])

        if not datamarkethistorico.empty:
            datamarkethistorico['valormt2'] = datamarkethistorico['valor']/datamarkethistorico['areaconstruida']
            datamarkethistorico = datamarkethistorico.groupby(['tiponegocio']).agg({'valormt2':'median','areaconstruida':'count'}).reset_index()
            datamarkethistorico.columns = ['tiponegocio','valor','obs']
            datamarkethistorico['tipo'] = 'historico'
            datamarket = pd.concat([datamarket,datamarkethistorico])

    if not datamarket.empty:
        for i in ['Venta','Arriendo']:
            datapaso = datamarket[datamarket['tiponegocio']==i]
            del datapaso['tiponegocio']
            datapaso = datapaso.set_index('tipo')
            datapaso = datapaso.transpose()
            datapaso = datapaso.reset_index()
            outputs.update({f'market_{i.lower()}':datapaso.to_dict(orient='records')})

    return outputs
