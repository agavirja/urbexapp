import streamlit as st

def diccionario():
    formato = [
        {'tipoinmueble':'Local','lista':['003','004','006','007','039','040','041','042','094','095']},
        {'tipoinmueble':'Oficina','lista':['015','020','045','080','081','082','092']},
        {'tipoinmueble':'Bodega','lista':['008','025','033','091','093','097']},
        {'tipoinmueble':'Apartamento','lista':['002','038']},
        {'tipoinmueble':'Casa','lista':['001','037']},
        {'tipoinmueble':'Hotel','lista':['021','026','027','046']},
        ]
    return formato

@st.cache_data(show_spinner=False)
def inmueble2usosuelo(x):
    result  = []
    formato = diccionario()
    if isinstance(x, str):
        for i in formato:
            if x.lower() in i['tipoinmueble'].lower():
                result += i['lista']
                break
    elif isinstance(x, list):
        for j in x:
            for i in formato:
                if j.lower() in i['tipoinmueble'].lower():
                    result += i['lista']
    result = list(set(result))
    return result

@st.cache_data(show_spinner=False)
def usosuelo2inmueble(x):
    result  = []
    formato = diccionario()
    if isinstance(x, str):
        for i in formato:
            if x in i['lista']:
                result.append(i['tipoinmueble'])
                break
    elif isinstance(x, list):
        for j in x:
            for i in formato:
                if j in i['lista']:
                    result.append(i['tipoinmueble'])
    result = list(set(result))
    return result
