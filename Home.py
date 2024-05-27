import streamlit as st

st.set_page_config(layout='wide',page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

# streamlit run D:\Dropbox\Empresa\Urbex\_APP_heroku\Home.py
# https://streamlit.io/
# pipreqs --encoding utf-8 "D:\Dropbox\Empresa\Urbex\_APP"

#------------#
# Powersheel #

# Archivos donde esta la palabra "urbextestapp\.streamlit\.app" o "urbextestapp\.streamlit\.app"
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object { if (Get-Content $_.FullName | Select-String -Pattern 'localhost:8501' -Quiet) { $_.FullName } }

# Reemplazar "localhost:8501" por "localhost:8501" o al reves en los archivos donde esta la palabra
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'localhost:8501', 'localhost:8501'} | Set-Content $_.FullName}

initialformat = {
    'botonlogin':False
    }
for key,value in initialformat.items():
    if key not in st.session_state: 
        st.session_state[key] = value
            
st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: #000;        
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

    button[data-testid="StyledFullScreenButton"] {{
        visibility: hidden; 
        height: 0%;
        
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.image('https://iconsapp.nyc3.digitaloceanspaces.com/Landing.png',use_column_width ='always')