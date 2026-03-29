
import streamlit as st

st.title("Button Color Test")

st.write("Testing button colors without emojis:")

if st.button("Add Task", type="primary"):
    st.success("Primary button clicked")

if st.button("Generate Schedule", type="primary"):
    st.success("Primary button clicked")

if st.button("Secondary Button", type="secondary"):
    st.success("Secondary button clicked")
