🤖 EDGAR Analyst Copilot
Authors: Sangyeon Lee, Ronghao Zeng, Mingchen Yuan, Yuan Zhuang, Jinyu Li

Course: Applied Generative AI (Final Project)

The EDGAR Analyst Copilot is a specialized financial assistant designed to analyze SEC 10-K and 10-Q filings. Unlike generic LLMs, this system combines Text Retrieval (RAG) for narrative analysis with Structured XBRL Data for precise numerical reasoning.





🚀 Key Features
Finance-Aware Retrieval: Intelligently chunks filings to prioritize "Risk Factors" and "MD&A" sections.

Table-Grounded Reasoning: Fetches exact numbers (Revenue, Net Income) directly from SEC XBRL APIs to prevent math hallucinations.


Strict Citations: Every text-based answer includes a direct citation to the source filing (Accession Number).

Streaming Interface: Real-time typewriter-style responses for a better user experience.

📂 Project Structure
Plaintext
Final_Project/
├── app/                 # Backend API (FastAPI)
│   ├── main.py          # API Entry point
│   └── rag_pipeline.py  # RAG + XBRL Logic
├── helper_lib/          # Core Utilities
│   ├── edgar_parser.py  # SEC Downloader
│   ├── retriever.py     # FAISS Vector Search
│   └── xbrl.py          # Structured Data Fetcher
├── data/                # (Auto-generated) Stores filings & indexes
├── frontend.py          # User Interface (Streamlit)
├── pyproject.toml       # Project Configuration
└── requirements.txt     # Dependencies
🛠️ Setup & Installation
1. Clone the Repository

Bash
git clone https://github.com/louie0207/FinalProject.git
cd Final_Project
2. Configure Credentials

Security Warning: Never upload your API keys to GitHub.

Create a file named .env in the Final_Project folder.

Add your OpenAI API Key inside:

Plaintext
OPENAI_API_KEY=sk-your-key-here...
(Alternatively, you can export this key in your terminal session before running).

3. Create Virtual Environment & Install

Bash
# Create environment
python -m venv .venv

# Activate environment
# Mac/Linux:
source .venv/bin/activate
# Windows:
# .\.venv\Scripts\activate

# Install dependencies in editable mode
pip install -e .
🖥️ How to Run
You need two separate terminal windows to run this application.

Terminal 1: Backend API

This powers the brain of the copilot.

Bash
# Ensure you are in /Final_Project and environment is active
source .venv/bin/activate

# Set API Key (if not using .env file)
export OPENAI_API_KEY="sk-..."

# Start the Server
uvicorn app.main:app --reload
Wait until you see: Application startup complete.

Terminal 2: Frontend UI

This launches the website.

Bash
# Ensure you are in /Final_Project and environment is active
source .venv/bin/activate

# Run Streamlit
streamlit run frontend.py
The app should automatically open in your browser at http://localhost:8501.

🧪 Usage Guide
Ingest Data:

On the sidebar, enter a ticker (e.g., AAPL or TSLA).

Click "Ingest/Refresh Data".

Wait for the green success message.

View KPIs (XBRL):

Go to the "KPI Dashboard" tab.

Click "Load Metrics" to see exact Revenue/Asset numbers from the SEC.

Chat (RAG):

Go to the "Financial Chat" tab.

Ask: "What are the primary risk factors?" or "How did revenue change last year?"

Verify: Check the [Source: ...] citations in the response.

⚠️ Troubleshooting
Error: 404 Client Error ... CIK000000AAPL:

The system failed to convert Ticker to CIK. Ensure your internet is connected so it can fetch the SEC ticker map.

Error: 429 insufficient_quota:

Your OpenAI API key has run out of credits. Check your billing dashboard.

Error: ConnectionTimeout on Frontend:

Make sure Terminal 1 (Backend) is running! The website cannot work without the API server.