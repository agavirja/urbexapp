import streamlit as st
import pandas as pd
import hashlib
import time
from datetime import datetime
from sqlalchemy import create_engine

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata"]
schema   = 'urbex'

def main():

    formato = {
                'login':True,
                'signin':False,
                'access':False,
                'token':''
               }
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.access is False:
        
        style()
        
        col1, col3 = st.columns(2)
        with col1:
            st.markdown('<div class="centered-image"><img src="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_positivo.png" width="350"></div>', unsafe_allow_html=True)
    
        if st.session_state.login:
            with col3:
                st.button('Sign in',on_click=button_signin)
                
        if st.session_state.signin:
            with col3:
                st.button('Log in ',on_click=button_login)
            
        col1, col2 = st.columns(2)
        if st.session_state.login:
            with col2:
                with st.form("login form"):
                    st.markdown("#### Log in")
                    email      = st.text_input("Email")
                    contrasena = st.text_input("Password", type="password")
                    submit     = st.form_submit_button("Login")
            
                if submit:
                    with st.spinner('Verificando'):
                        if verificar_contrasena(email, contrasena):
                            datos_usuario(email)
                            st.session_state.access = True
                            st.session_state.login  = False
                            st.session_state.signin = False
                            st.rerun()
                        else:
                            st.error("Error en la contraseña o email, o usuario no activo")
        
        if st.session_state.signin:
            with col2:
                with st.form("signin form"):
                    st.markdown("#### Registro")
                    email      = st.text_input("Email").strip()
                    contrasena = st.text_input("Password", type="password").strip()
                    contrasena = encriptar_contrasena(contrasena)
                    nombre   = st.text_input("Nombre Completo").strip().title()
                    telefono = st.text_input("Celular",max_chars =10).strip()
                    
                    token = hashlib.md5()
                    token.update(email.encode('utf-8'))
                    st.session_state.token = token.hexdigest()
                     
                    submit = st.form_submit_button("Registrarse")
                    if submit:
                        registro         = pd.DataFrame([{'email':email,'nombre':nombre,'telefono':telefono,'password':contrasena,'token':st.session_state.token,'fecha_creacion':datetime.now().strftime('%Y-%m-%d'),'fecha_modificacion':datetime.now().strftime('%Y-%m-%d')}])
                        response,success = user_register(registro,email)
                        if success:
                            with st.spinner('Proceso'):
                                st.success(response)
                                st.session_state.login  = True
                                st.session_state.signin = False
                                st.rerun()
                        else:
                            st.error(response)

def style():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(to right, #000 50%, #FFF 50%);
        }}
                                        
        .centered-image {{
            display: flex;
            justify-content: center;
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
        
        a[href="#log-in"] {{
            display: none;
            visibility: hidden; 
            height: 0%;
            fill: transparent;
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
        
        .stButton button {{
                background-color: #00FFFF;
                font-weight: bold;
                width: 30%;
                border: 2px solid #00FFFF;
                
            }}
        
        .stButton button:hover {{
            background-color: #00FFFF;
            color: black;
            border: #00FFFF;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
def encriptar_contrasena(contrasena_plana):
    token = hashlib.md5()
    token.update(contrasena_plana.encode('utf-8'))
    contrasena_plana = token.hexdigest()
    return contrasena_plana

def verificar_contrasena(email, contrasena):
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df     =  pd.read_sql_query(f"""SELECT password  FROM {schema}.users WHERE email='{email}'  AND validate_email=1;""" , engine)
    engine.dispose()
    if df.empty:
        return False
    contrasenastock = df['password'].iloc[0]
    contrasenanew   = encriptar_contrasena(contrasena)
    if contrasenanew==contrasenastock:
        return True
    else:
        return False

def user_register(data,email):
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df       =  pd.read_sql_query(f"""SELECT * FROM {schema}.users WHERE email='{email}';""" , engine)
    if df.empty:
        try:
            data.to_sql('users', engine, if_exists='append', index=False, chunksize=1)
            response = 'Usuario registrado exitosamente'
            success  = True
        except:
            response = 'Por favor volver a registrarse'
            success  = False
    else:
        response = 'Usuario ya está registrado'
        success  = False
    engine.dispose()
    return response,success
        
def datos_usuario(email):
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df     =  pd.read_sql_query(f"""SELECT email,nombre,telefono,logo,token  FROM {schema}.users WHERE email='{email}';""" , engine)
    engine.dispose()
    if df.empty is False:
        for i in ['email','nombre','telefono','logo','token']:
            st.session_state[i] = df[i].iloc[0]
            
def button_login():
    st.session_state.login  = True
    st.session_state.signin = False

def button_signin():
    st.session_state.login  = False
    st.session_state.signin = True
    
if __name__ == "__main__":
    main()