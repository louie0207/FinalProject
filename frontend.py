import streamlit as st
import requests
import json
import pandas as pd

# API Configuration
API_BASE = "http://localhost:8000"

st.set_page_config(page_title="EDGAR Analyst Copilot", layout="wide")

st.title("🤖 EDGAR Analyst Copilot")
st.markdown("Financial Analysis grounded in **XBRL Data** and **SEC Filings**.")

# Sidebar for Setup
with st.sidebar:
    st.header("Configuration")
    cik_input = st.text_input("Enter Company CIK or Ticker", value="AAPL")
    
    if st.button("Ingest/Refresh Data"):
        with st.spinner(f"Ingesting data for {cik_input}..."):
            try:
                # 1. Ingest Documents (RAG)
                r = requests.post(f"{API_BASE}/ingest", json={
                    "cik": cik_input,
                    "form": "10-K",
                    "limit_per_form": 1
                })
                if r.status_code == 200:
                    st.success("Ingestion Complete!")
                else:
                    st.error(f"Error: {r.text}")
            except Exception as e:
                st.error(f"Connection Failed: {e}")

# Main Layout: Tabs for Chat and Data
tab1, tab2 = st.tabs(["💬 Financial Chat", "📊 KPI Dashboard"])

# --- TAB 1: CHAT INTERFACE ---
with tab1:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about Revenue, Risks, or Net Income..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Stream Assistant Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Prepare payload with history
                payload = {
                    "cik": cik_input,
                    "messages": st.session_state.messages,
                    "form": "10-K"
                }
                
                # Request streaming response
                with requests.post(f"{API_BASE}/chat", json=payload, stream=True) as response:
                    if response.status_code == 200:
                        for chunk in response.iter_content(chunk_size=None):
                            if chunk:
                                content = chunk.decode("utf-8")
                                full_response += content
                                message_placeholder.markdown(full_response + "▌")
                        
                        message_placeholder.markdown(full_response)
                    else:
                        st.error(f"API Error: {response.status_code}")
                        
            except Exception as e:
                st.error(f"Connection Error: {e}")

        # Save assistant message to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- TAB 2: KPI DASHBOARD (XBRL) ---
with tab2:
    st.subheader(f"Financial KPIs for {cik_input}")
    if st.button("Load Metrics"):
        with st.spinner("Fetching XBRL Data..."):
            try:
                r = requests.get(f"{API_BASE}/kpi/{cik_input}")
                if r.status_code == 200:
                    data = r.json().get("kpis", {}).get("data", {})
                    
                    if not data:
                        st.warning("No XBRL data found.")
                    else:
                        # Create 3 columns for key metrics
                        col1, col2, col3 = st.columns(3)
                        
                        # Helper to display metrics
                        def show_metric(col, label, key):
                            items = data.get(key, [])
                            if items:
                                latest = items[0]
                                val = latest['val']
                                # Format large numbers
                                if val > 1_000_000_000:
                                    val_str = f"${val/1_000_000_000:.2f} B"
                                elif val > 1_000_000:
                                    val_str = f"${val/1_000_000:.2f} M"
                                else:
                                    val_str = f"${val:,.0f}"
                                col.metric(label, val_str, f"FY {latest['fy']}")
                            else:
                                col.metric(label, "N/A")

                        show_metric(col1, "Revenue", "Revenues")
                        show_metric(col2, "Net Income", "NetIncome")
                        show_metric(col3, "Total Assets", "Assets")
                        
                        st.divider()
                        st.write("### Raw Data View")
                        st.json(data)
                else:
                    st.error("Failed to fetch KPIs")
            except Exception as e:
                st.error(f"Error: {e}")