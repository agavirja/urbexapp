import streamlit as st
def style():
    #FAFAFA
    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #fff;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #000;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-black.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="collapsedControl"] button {{
            background-color: transparent;
            border: none;
            cursor: pointer;
            padding: 0;
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
    
        #MainMenu {{
        visibility: hidden; 
        height: 0%;
        }}
        
        header {{
            visibility: hidden; 
            height:
                0%;
            }}
            
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        
        div[data-testid="stSpinner"] {{
            color: #000000;
            background-color: #F0F0F0; 
            padding: 10px; 
            border-radius: 5px;
            }}
        
        a[href="#responsive-table"] {{
            visibility: hidden; 
            height: 0%;
            }}
        
        a[href^="#"] {{
            /* Estilos para todos los elementos <a> con href que comienza con "#" */
            visibility: hidden; 
            height: 0%;
            overflow-y: hidden;
        }}

        div[class="table-scroll"] {{
            background-color: #a6c53b;
            visibility: hidden;
            overflow-x: hidden;
            }}
            
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
        }}
        
        .stButton button {{
                background-color: #A16CFF;
                font-weight: bold;
                width: 100%;
                border: 2px solid #A16CFF;
                color:white;
            }}
        
        .stButton button:hover {{
            background-color: #A16CFF;
            color: white;
            border: #A16CFF;
        }}
        
        .stButton button:active {{
            background-color: #FFF;
            color: #A16CFF;
            border: 2px solid #FFF;
            outline: none;
        }}
    
        [data-testid="stMultiSelect"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-baseweb="select"] > div {{
            background-color: #fff;
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
    
    
        [data-testid="stSelectbox"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;  
        }}
        
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
            
        }}

        [data-testid="stNumberInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;
        }}
        
        [data-baseweb="input"] > div {{
            background-color: #fff;
        }}
        
        div[data-testid="stNumberInput-StepUp"]:hover {{
            background-color: #A16CFF;
        }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: 14px;
            font-weight: bold;
            color: #3C3840;
            font-family: 'Aptos Narrow';
        }}
        
        span[data-baseweb="tag"] {{
          background-color: #5F59EB;
        }}
        
        [data-testid="stDateInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
            
        .stDownloadButton button {{
            background-color: #DAE8D8;
            font-weight: bold;
            width: 100%;
            border: 2px solid #DAE8D8;
            color: black;
        }}
        .stDownloadButton button:hover {{
            background-color: #DAE8D8;
            color: black;
            border: #DAE8D8;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )