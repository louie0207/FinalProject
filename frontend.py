# ========================================================================
# frontend.py — Clean Working Version (Streaming-Safe + 3 Questions Per Mode)
# ========================================================================
import streamlit as st
import requests
import pandas as pd
import re

API_BASE = "http://localhost:8000"

def render_math(msg: str):
    # pattern for math sequences wrapped in \( ... \)
    pattern = r"\\\((.*?)\\\)"

    def repl(match):
        expr = match.group(1)
        return f"$$ {expr} $$"

    return re.sub(pattern, repl, msg)

# ========================================================================
# PAGE CONFIG
# ========================================================================
st.set_page_config(page_title="EDGAR Analyst Copilot", layout="wide")

st.title("🤖 EDGAR Analyst Copilot")
st.markdown("Financial Analysis grounded in **XBRL Data** and **SEC Filings**.")

# ========================================================================
# SIDEBAR
# ========================================================================
with st.sidebar:
    st.header("Configuration")

    mode = st.radio("Select Mode:", ["Single Company View", "Multi-Company Comparison"])
    st.divider()

    # ---------------- SINGLE COMPANY MODE ----------------
    if mode == "Single Company View":
        cik_input = st.text_input("Enter Company CIK or Ticker", value="COST")

        if st.button("Ingest / Refresh Data"):
            with st.spinner("Ingesting..."):
                try:
                    r = requests.post(
                        f"{API_BASE}/ingest",
                        json={"cik": cik_input, "form": "10-K", "limit_per_form": 1},
                        timeout=60
                    )
                    if r.status_code == 200:
                        st.success("Ingestion Complete!")
                    else:
                        st.error(r.text)
                except Exception as e:
                    st.error(f"Error: {e}")

    # ---------------- MULTI COMPANY MODE ----------------
    else:
        st.subheader("Companies to Compare")

        if "tickers" not in st.session_state:
            st.session_state.tickers = ["COST", "AMZN"]

        # Add company
        if st.button("➕ Add Company"):
            st.session_state.tickers.append("")

        # --- Render input fields WITHOUT removing blanks ---
        for i in range(len(st.session_state.tickers)):
            st.session_state.tickers[i] = st.text_input(
                f"Company {i+1}",
                value=st.session_state.tickers[i],
                key=f"t_{i}"
            )

        # --- NEW BUTTON: Remove Blank Lines ---
        if st.button("🧹 Remove Empty Rows"):
            st.session_state.tickers = [t for t in st.session_state.tickers if t.strip()]
            st.rerun()

        # --- Only ingest CLEAN tickers, do not overwrite session list ---
        clean_list = [t for t in st.session_state.tickers if t.strip()]

        if st.button("🚀 Ingest All Companies"):
            if not clean_list:
                st.error("No valid companies entered.")
            else:
                with st.spinner("Ingesting all companies..."):
                    try:
                        requests.post(
                            f"{API_BASE}/ingest_all",
                            json={"ciks": clean_list, "form": "10-K", "limit_per_form": 1},
                            timeout=120
                        )
                        st.success("All companies ingested!")
                        st.session_state.all_ingested = True
                    except Exception as e:
                        st.error(f"Error: {e}")


# ========================================================================
# MAIN TABS
# ========================================================================
if mode == "Single Company View":
    tab_chat, tab_kpi = st.tabs(["💬 Financial Chat", "📊 KPI Dashboard"])
else:
    tab_chat, tab_compare = st.tabs(["💬 Financial Chat", "📈 Comparison Dashboard"])


# ========================================================================
# =====================  CHAT TAB  ======================
# ========================================================================
with tab_chat:

    # chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ====================================================================
    # SUGGESTED QUESTIONS (correctly placed outside ask())
    # ====================================================================
    st.write("### Suggested Questions")

    def ask(q):
        st.session_state.messages.append({"role": "user", "content": q})
        st.rerun()

    # --------------------- SINGLE COMPANY ---------------------
    if mode == "Single Company View":
        T = cik_input.upper()

        col1, col2, col3 = st.columns(3)

        if col1.button("📉 Risk Summary"):
            ask(f"Summarize the main risk factors for {T}.")

        if col2.button("📈 Revenue Trend"):
            ask(f"How has {T}'s revenue changed over the last 3 years?")

        if col3.button("💰 Profitability"):
            ask(f"Explain {T}'s profitability and key financial drivers.")

    # --------------------- MULTI COMPANY ----------------------
    else:
        tickers = [t.upper() for t in st.session_state.tickers]
        pretty = ", ".join(tickers)

        col1, col2, col3 = st.columns(3)

        if col1.button("📊 Revenue Comparison"):
            ask(f"Compare the revenue growth of {pretty} over the last 3 years.")

        if col2.button("💰 Profitability Ranking"):
            ask(f"Which company among {pretty} is most profitable?")

        if col3.button("⚠ Risk Comparison"):
            ask(f"Compare the major risk factors across {pretty}.")

    st.divider()

    # Prevent chatting before ingesting data
    if mode == "Multi-Company Comparison" and "all_ingested" not in st.session_state:
        st.warning("⚠ Please ingest all companies first.")
        st.stop()

    # --- Display chat messages ---
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(render_math(m["content"]))

    # --- Chat input ---
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # ====================================================================
    # AUTO TRIGGER ASSISTANT RESPONSE
    # ====================================================================
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":

        # Build payload
        if mode == "Single Company View":
            endpoint = "/chat"
            payload = {
                "cik": cik_input,
                "messages": st.session_state.messages,
                "form": "10-K"
            }
        else:
            endpoint = "/chat_multi"
            payload = {
                "ciks": st.session_state.tickers,
                "messages": st.session_state.messages,
                "form": "10-K"
            }

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_reply = ""

            try:
                # --- STREAMING MODE ---
                with requests.post(
                    f"{API_BASE}{endpoint}",
                    json=payload,
                    stream=True,
                    timeout=120
                ) as r:
                    try:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                text = chunk.decode("utf-8")
                                full_reply += text

                                # render math safely while streaming
                                rendered = render_math(full_reply)
                                placeholder.markdown(rendered + "▌", unsafe_allow_html=True)

                        # final render when complete
                        placeholder.markdown(render_math(full_reply), unsafe_allow_html=True)

                    except requests.exceptions.ChunkedEncodingError:
                        # fallback to full text if streaming breaks
                        full_reply = r.text
                        placeholder.markdown(render_math(full_reply), unsafe_allow_html=True)

            except Exception:
                # --- NON-STREAMING FINAL FALLBACK ---
                r = requests.post(
                    f"{API_BASE}{endpoint}",
                    json=payload,
                    timeout=120
                )
                full_reply = r.text
                placeholder.markdown(render_math(full_reply), unsafe_allow_html=True)

            # save final assistant message (raw, not rendered)
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_reply
            })

            st.rerun()


# ========================================================================
# KPI TAB — SINGLE COMPANY ONLY
# ========================================================================
if mode == "Single Company View":
    with tab_kpi:

        st.subheader(f"📊 Financial KPIs — {cik_input}")

        if st.button("Load Metrics"):
            with st.spinner("Loading XBRL metrics..."):
                r = requests.get(f"{API_BASE}/kpi/{cik_input}")

            if r.status_code != 200:
                st.error("Failed to fetch KPIs")
                st.stop()

            data = r.json().get("kpis", {}).get("data", {})

            col1, col2, col3 = st.columns(3)

            def metric(col, label, key):
                if not data.get(key):
                    col.metric(label, "N/A")
                else:
                    val = data[key][0]["val"]
                    fy = data[key][0]["fy"]
                    col.metric(label, f"${val:,.0f}", f"FY {fy}")

            metric(col1, "Revenue", "Revenues")
            metric(col2, "Net Income", "NetIncome")
            metric(col3, "Assets", "Assets")

            st.divider()

            # Trends
            chart1, chart2 = st.columns(2)

            def trend(col, key, title):
                df = pd.DataFrame(data.get(key, []))
                if df.empty: return
                df["end"] = pd.to_datetime(df["end"])
                df = df.sort_values("end")
                with col:
                    st.markdown(f"**{title}**")
                    st.line_chart(df, x="end", y="val")

            trend(chart1, "Revenues", "Revenue Trend")
            trend(chart2, "NetIncome", "Net Income Trend")


# ========================================================================
# COMPARISON TAB — MULTI COMPANY
# ========================================================================
else:
    with tab_compare:

        tickers = st.session_state.tickers

        if len(tickers) < 2:
            st.warning("Add at least 2 companies.")
            st.stop()

        if st.button("Run Comparison"):
            with st.spinner("Fetching comparison..."):

                all_data = {}
                all_years = set()

                for t in tickers:
                    r = requests.get(f"{API_BASE}/compare_kpis", params={"cik1": t, "cik2": t})
                    comp = r.json()["company1"]
                    all_data[t] = comp
                    all_years |= set(comp["years"])

                years = sorted(all_years)

                def align(yrs, vals, master):
                    m = dict(zip(yrs, vals))
                    return [m.get(y, None) for y in master]

                # Revenue
                st.subheader("📊 Revenue Comparison")
                df_rev = {"Year": years}
                for t in tickers:
                    df_rev[t.upper()] = align(all_data[t]["years"], all_data[t]["revenue"], years)
                st.line_chart(pd.DataFrame(df_rev), x="Year")

                # Net Income
                st.subheader("📊 Net Income Comparison")
                df_ni = {"Year": years}
                for t in tickers:
                    df_ni[t.upper()] = align(all_data[t]["years"], all_data[t]["net_income"], years)
                st.line_chart(pd.DataFrame(df_ni), x="Year")
