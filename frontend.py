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
                    st.success("Ingestion Complete! Please wait a moment before chatting.")
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

    # [FEATURE 1] Suggested Questions
    st.write("### Suggested Questions")
    col1, col2, col3 = st.columns(3)
    
    # Button Logic: Just append the message. The auto-trigger below will handle the API call.
    if col1.button("Risk Summary"):
        st.session_state.messages.append({"role": "user", "content": "Summarize the primary Risk Factors."})
    
    if col2.button("Revenue Growth"):
        st.session_state.messages.append({"role": "user", "content": "How has revenue changed over the last 3 years?"})

    if col3.button("Supply Chain"):
        st.session_state.messages.append({"role": "user", "content": "What are the supply chain risks?"})

    st.divider()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input (Manual Entry)
    if prompt := st.chat_input("Ask about Revenue, Risks, or Net Income..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # Automatic Response Trigger (Handles both Buttons and Manual Input)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
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
                        # Save assistant message to history
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    else:
                        st.error(f"API Error: {response.status_code}")
                        
            except Exception as e:
                st.error(f"Connection Error: {e}")

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
                        # 1. Metric Cards
                        col1, col2, col3 = st.columns(3)
                        
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
                        
                        # [FEATURE 2] Visualizations (Line Charts)
                        st.subheader("📈 Financial Trends (3-Year View)")
                        chart_col1, chart_col2 = st.columns(2)
                        
                        # Container to hold data for CSV export
                        all_dfs = []

                        def plot_trend(column, data_key, title, color_hex):
                            items = data.get(data_key, [])
                            if items:
                                df = pd.DataFrame(items)
                                df["end"] = pd.to_datetime(df["end"])
                                df = df.sort_values("end")
                                
                                # Add to export list
                                df["Metric"] = title
                                all_dfs.append(df)
                                
                                with column:
                                    st.markdown(f"**{title}**")
                                    st.line_chart(df, x="end", y="val", color=color_hex)
                        
                        plot_trend(chart_col1, "Revenues", "Revenue Growth", "#2E8B57")
                        plot_trend(chart_col2, "NetIncome", "Net Income Growth", "#4682B4")

                        st.divider()
                        
                        # [FEATURE 3] CSV Export
                        if all_dfs:
                            combined_df = pd.concat(all_dfs, ignore_index=True)
                            # Select clean columns for the CSV
                            export_df = combined_df[["end", "val", "fy", "form", "Metric"]].sort_values(["Metric", "end"])
                            
                            csv = export_df.to_csv(index=False).encode('utf-8')
                            
                            st.download_button(
                                label="📥 Download Financial Data (CSV)",
                                data=csv,
                                file_name=f"{cik_input}_financial_summary.csv",
                                mime="text/csv",
                            )
                        
                        with st.expander("View Raw XBRL Data"):
                            st.json(data)
                else:
                    st.error("Failed to fetch KPIs")
            except Exception as e:
                st.error(f"Error: {e}")