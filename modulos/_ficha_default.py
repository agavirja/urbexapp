import streamlit as st
import streamlit.components.v1 as components

from modulos._ficha_report  import main as _ficha_report
from display.style_white import style 

def main():
    
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'codigo':'',
               'fichaactiva':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1,col2 = st.columns(2)
    with col1:
        st.session_state.codigo = st.text_input('Código:',value="")
    
    if isinstance(st.session_state.codigo, str) and st.session_state.codigo!="":
        with col1:
            st.write('')
            st.write('')
            if st.button('Buscar'):
                st.session_state.fichaactiva = True
                st.rerun()
                
    if st.session_state.fichaactiva:
        _ficha_report(st.session_state.codigo)
    else:
        style()