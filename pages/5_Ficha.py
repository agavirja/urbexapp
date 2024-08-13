import streamlit as st
import warnings
from modulos._ficha_default  import main as _ficha_default
from modulos._ficha_report  import main as _ficha_report

from display.style_white import style 

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide",initial_sidebar_state="collapsed",page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

style()

formato = {
           'code':None,
           }

for key,value in formato.items():
    if key not in st.session_state: 
        st.session_state[key] = value
 
if 'code' in st.query_params: 
    st.session_state.code = st.query_params['code']

if st.session_state.code is None:
    _ficha_default()
elif isinstance(st.session_state.code, str):
    _ficha_report(st.session_state.code)
