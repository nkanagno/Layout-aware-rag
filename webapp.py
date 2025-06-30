
from app.tabs.chatbot import chatbot_interface
from streamlit_option_menu import option_menu
from app.tabs.layout_analysis import layout_analysis_interface
import streamlit as st
import os

pdf_file = st.sidebar.file_uploader("PDF file:", type=["pdf"])

if pdf_file is not None:
    tabs = ["Layout analysis", "chatbot"]
    icons = ["bi-box-arrow-in-right"] + ["person-fill"] + ["person-fill"]
else:   
    st.stop()

with st.sidebar:
    selected_tab = option_menu(
        menu_title="Select a tab",
        options=tabs,
        default_index=0,
        icons=icons,
        orientation="vertical",
    )



if selected_tab == "Layout analysis":
    layout_analysis_interface(pdf_file)
elif selected_tab =="chatbot":
    chatbot_interface(pdf_file)

