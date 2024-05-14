import streamlit as st
import requests
import time 

API_URL = "http://127.0.0.1:8000/process"

background_image = """
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: linear-gradient(to bottom right, rgba(0,0,0,0.6), rgba(0,0,0,0.2)), url("https://img.freepik.com/free-vector/diagonal-motion-lines-white-background_1017-33198.jpg");
    background-size: cover;
    background-position: center;  
    background-repeat: no-repeat;
}
h1, h2, h3 {
    color: black; 
}
.report-frame {
    border: 2px solid blue;
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    padding: 20px;
    margin-top: 10px;
    border-radius: 10px;
    background-color: white;
}
.low-risk { background-color: #90EE90; color: black; }  /* Light green */
.medium-risk { background-color: yellow; color: black; }
.high-risk { background-color: red; color: white; }
</style>
"""

st.markdown(background_image, unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 3])
with col1:
    st.image("AI WebREPORT.png", width=100)  
with col2:
    st.markdown("<h1 style='text-align: center; color: black;'>KYC REPORT</h1>", unsafe_allow_html=True)
with col3:
    st.image("AI WebREPORT.png", width=100)  

with st.sidebar:
    st.title("KYC Report Tool")
    entity_name = st.text_input("Please enter the name of the entity:", "")


if st.sidebar.button("Generate KYC Report"):
    start_time = time.time()  
    if entity_name:
        data = {"entity_name": entity_name}
        with st.spinner('Generating KYC Report...'):
            response = requests.post(API_URL, json=data)
            if response.status_code == 200:
                summary = response.json()["summary"]
                risk_class = response.json()["class"]
                risk_style = "low-risk" if risk_class == "Low" else "medium-risk" if risk_class == "Medium" else "high-risk"
                #st.subheader("KYC Report:")
                st.markdown(f'<div class="report-frame {risk_style}">{summary}</div>', unsafe_allow_html=True)
            else:
                st.error(f"Error while summarizing. Status code: {response.status_code}")
            execution_time = time.time() - start_time 
            st.sidebar.write(f"Execution Time: {execution_time:.2f} seconds") 
    else:
        st.sidebar.error("Please enter the name of the entity to generate the KYC report.")
        
# python -m streamlit run c:/Users/abdlb/Downloads/testk-main/frontendstreamlit.py
