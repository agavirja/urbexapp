import streamlit as st
import re
import pandas as pd
import numpy as np
import pickle
import unicodedata
import math as mt
import boto3

@st.cache_data(show_spinner=False)
def main(inputvar):
    
    tipoinmueble   = inputvar['tipoinmueble'] if 'tipoinmueble' in inputvar and isinstance(inputvar['tipoinmueble'], str) else None
    scacodigo      = inputvar['scacodigo'] if 'scacodigo' in inputvar and isinstance(inputvar['scacodigo'], str) else None
    areaconstruida = inputvar['areaconstruida'] if 'areaconstruida' in inputvar and (isinstance(inputvar['areaconstruida'], float) or isinstance(inputvar['areaconstruida'], int)) else None
    habitaciones   = inputvar['habitaciones'] if 'habitaciones' in inputvar and (isinstance(inputvar['habitaciones'], float) or isinstance(inputvar['habitaciones'], int)) else None
    banos          = inputvar['banos'] if 'banos' in inputvar and (isinstance(inputvar['banos'], float) or isinstance(inputvar['banos'], int)) else None
    garajes        = inputvar['garajes'] if 'garajes' in inputvar and (isinstance(inputvar['garajes'], float) or isinstance(inputvar['garajes'], int)) else None

    ACCESS_KEY  = st.secrets["ACCESS_KEY_digitalocean"]
    SECRET_KEY  = st.secrets["SECRET_KEY_digitalocean"]
    REGION      = st.secrets["REGION_digitalocean"]
    BUCKET_NAME = 'model-result'
    
    session = boto3.session.Session()
    client  = session.client('s3', region_name=REGION, endpoint_url='https://nyc3.digitaloceanspaces.com',
                            aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    
    
    # Codigo: scacodigo
    response     = client.get_object(Bucket=BUCKET_NAME, Key='le_scacodigo.pkl')
    le_scacodigo = pickle.loads(response['Body'].read())

    for tiponegocio in ['venta','arriendo']:
        
        try:
            # ANN venta
            response  = client.get_object(Bucket=BUCKET_NAME, Key=f"ANN_{tiponegocio.lower()}_{tipoinmueble.lower()}.pkl")
            salida    = pickle.loads(response['Body'].read())
            r         = ANNforecast(inputvar,salida)
            inputvar[f'ann_forecast_{tiponegocio.lower()}']     = r['valorestimado']
            inputvar[f'ann_forecast_{tiponegocio.lower()}_mt2'] = r['valorestimado_mt2']
        except:
            inputvar[f'ann_forecast_{tiponegocio.lower()}']     = None
            inputvar[f'ann_forecast_{tiponegocio.lower()}_mt2'] = None
    
    
        inmueble = pd.DataFrame({'areaconstruida':[areaconstruida],
                                 'scacodigo':[le_scacodigo.transform([scacodigo])[0]], 
                                 'habitaciones':[habitaciones], 
                                 'banos':[banos], 
                                 'garajes':[garajes], 
                                 })
        
        # Variables
        response  = client.get_object(Bucket=BUCKET_NAME, Key=f"variables_{tiponegocio.lower()}_{tipoinmueble.lower()}.pkl")
        variables = pickle.loads(response['Body'].read())
        variables = [x for x in variables if x in inmueble]
        inmueble  = inmueble[variables]
        
        try:
            # XGBoosting
            response = client.get_object(Bucket=BUCKET_NAME, Key=f"xgboosting_{tiponegocio.lower()}_{tipoinmueble.lower()}.pkl")
            xgboosting_loaded_model = pickle.loads(response['Body'].read())
    
            log_prediccion                = xgboosting_loaded_model.predict(inmueble)
            prediccion                    = np.exp(log_prediccion)
            inputvar[f'xg_forecast_{tiponegocio.lower()}']     = float(prediccion[0])
            inputvar[f'xg_forecast_{tiponegocio.lower()}_mt2'] = prediccion[0]/areaconstruida
        except:
            inputvar[f'xg_forecast_{tiponegocio.lower()}']     = None
            inputvar[f'xg_forecast_{tiponegocio.lower()}_mt2'] = None

    return inputvar

def ANNforecast(inputvar,salida):
    
    delta         = 0
    options       = salida['options']
    varlist       = salida['varlist']
    coef          = salida['coef']
    minmax        = salida['minmax']
    variables     = pd.DataFrame(0, index=np.arange(1), columns=varlist)
    
    for i in inputvar:
        value = inputvar[i]
        idd   = [z==elimina_tildes(i) for z in varlist]
        if sum(idd)==0:
            try:
                idd = [re.findall(elimina_tildes(i)+'#'+str(int(value)), z)!=[] for z in varlist]
            except:
                try:
                    idd = [re.findall(elimina_tildes(i)+'#'+elimina_tildes(value), z)!=[] for z in varlist]
                except:
                    pass
            value = 1                   
        if sum(idd)>0:
            row                = [j for j, x in enumerate(idd) if x]
            varname            = varlist[row[0]]
            variables[varname] = value
            
    # Transform MinMax
    a = variables.iloc[0]
    a = a[a!=0]
    for i in a.index:
        mini         = minmax[i]['min']
        maxi         = minmax[i]['max']
        variables[i] = (variables[i]-mini)/(maxi-mini)
        
    x     = variables.values
    value = ForecastFun(coef,x.T,options)
    if options['ytrans']=='log':
        value = np.exp(value)
        
    value         = value*(1-delta)
    valorestimado = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2       = value/inputvar['areaconstruida']
    valortotal = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2    = valortotal/inputvar['areaconstruida']
    return {'valorestimado': valorestimado[0][0], 'valorestimado_mt2':valuem2[0][0]}

def ForecastFun(coef,x,options):

    hiddenlayers = options['hiddenlayers']
    lambdavalue  = options['lambdavalue']
    biasunit     = options['biasunit']
    tipofun      = options['tipofun']
    numvar       = x.shape[0]
    nodos        = [numvar]
    for i in hiddenlayers:
        nodos.append(i)
    nodos.append(1)
        
    k          = len(nodos)
    suma       = 0
    theta      = [[] for i in range(k-1)]
    lambdac    = [[] for i in range(k-1)]
    lambdavect = np.nan
    for i in range(k-1):
        theta[i]   = np.reshape(coef[0:(nodos[i]+suma)*nodos[i+1]], (nodos[i]+suma, nodos[i+1]), order='F').T
        lambdac[i] =lambdavalue*np.ones(theta[i].shape)
        coef       = coef[(nodos[i]+suma)*nodos[i+1]:]
        if biasunit=='on':
            suma = 1
            lambdac[i][:,0] = 0
        [fil,col]  = lambdac[i].shape
        lambdavect = np.c_[lambdavect,np.reshape(lambdac[i],(fil*col,1)).T ]
        
    lambdac = lambdavect[:,1:].T
        
    # Forward Propagation
    a    = [[] for i in range(k)]
    z    = [[] for i in range(k)]
    g    = [[] for i in range(k)]
    a[0] = x
    numN = x.shape[1]
    for i in range(k-1):
        z[i+1]      = np.dot(theta[i],a[i])
        [ai,g[i+1]] = ANNFun(z[i+1],tipofun)
        if ((i+1)!=(k-1)) & (biasunit=='on'):
            a[i+1] = np.vstack((np.ones((1,numN)),ai))
        else:
            a[i+1] = ai
    return a[-1]

def ANNFun(z, tipofun):
    z = np.asarray(z)
    if tipofun=='lineal':
        f = z
        g = 1
    if tipofun=='logistica':
        f = 1/(1+mt.exp(-z))
        g = f*(1-f)
    if tipofun=='exp':
        f = np.exp(z)
        g = np.exp(z)
    if tipofun=='cuadratica':
        f = z + 0.5*(z*z)
        g = 1 + z
    if tipofun=='cubica':
        f = z + 0.5*(z*z)+(1/3.0)*(z*z*z)
        g = 1 + z + z*z
    return [f,g]

def elimina_tildes(s):
    s = s.replace(' ','').lower().strip()
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))