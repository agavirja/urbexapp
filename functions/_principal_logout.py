import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

def main():
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
                'login':True,
                'signin':False,
                'forgot':False,
                'access':False,
                'token':None,
                'forgot_codigo':False,
               }
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    #-------------------------------------------------------------------------#
    # Cookie
    COOKIES_SECRET_KEY = "88506c8c7b625c574f7db4efa5906dafa3490c0e7149594b"
    controller         = EncryptedCookieManager(prefix="streamlit_cookies", password=COOKIES_SECRET_KEY)

    #-------------------------------------------------------------------------#
    # Logout
    if st.session_state.access  and st.session_state.access and controller.ready():
        colf1,colf2,colf3 = st.columns([6,1,1])
        with colf2:
            if st.button('logout'):
                controller["session_token"] = ''
                controller.save() 
                
                st.session_state.access = False
                st.session_state.login  = True
                st.session_state.signin = False
                st.session_state.forgot = False
                st.session_state.token  = None
                st.rerun()