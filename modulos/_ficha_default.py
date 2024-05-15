import streamlit as st
import streamlit.components.v1 as components

from modulos._ficha_report  import main as _ficha_report

def main():
    
    formato = {
               'codigo':'',
               'fichaactiva':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png',width=200)
        
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
        
def style():
    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #3C3840;        
            opacity: 1;
            background-size: cover;
        }}
    
        header {{
            visibility: hidden; 
            height: 0%;
            }}
        
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-white.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="stToolbar"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stDecoration"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stStatusWidget"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: 14px;
            font-weight: bold;
            color: #05edff;
            font-family: 'Roboto', sans-serif;
        }}
                
        span[data-baseweb="tag"] {{
          background-color: #007bff;
        }}
        
        .stButton button {{
                background-color: #05edff;
                font-weight: bold;
                width: 100%;
                border: 2px solid #05edff;
                
            }}
        
        .stButton button:hover {{
            background-color: #05edff;
            color: black;
            border: #05edff;
        }}
        
        div[data-testid="stSpinner"] {{
            color: #fff;
            }}
        
        [data-testid="stNumberInput"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stMultiSelect"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px; 
            padding: 5px;
        }}
        
        [data-testid="stMultiSelect"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-testid="stSelectbox"] {{
            border: 5px solid #2B2D31;
            background-color: #2B2D31;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
            
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
