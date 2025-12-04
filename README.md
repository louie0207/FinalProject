🤖 EDGAR Analyst Copilot

Authors: Sangyeon Lee, Ronghao Zeng, Mingchen Yuan, Yuan Zhuang, Jinyu Li

Course: Applied Generative AI (Final Project)

The EDGAR Analyst Copilot is a specialized financial assistant designed to analyze SEC 10-K and 10-Q filings. Unlike generic LLMs, this system combines Text Retrieval (RAG) for narrative analysis with Structured XBRL Data for precise numerical reasoning.

🚀 Key Features

Finance-Aware Retrieval: Intelligently chunks filings to prioritize "Risk Factors" and "MD&A" sections.

Table-Grounded Reasoning: Fetches exact numbers (Revenue, Net Income) directly from SEC XBRL APIs to prevent math hallucinations.

Strict Citations: Every text-based answer includes a direct, clickable citation to the source filing on SEC.gov.

Visual Financial Trends: Automatically generates line charts for key financial metrics (Revenue, Net Income) over a 3-year period.

Data Export: Allows analysts to download structured financial data as a CSV file for further analysis in Excel.

Streaming Interface: Real-time typewriter-style responses for a better user experience.

📂 Project Structure

FinalProject/
├── app/                     # Backend API (FastAPI)
│   ├── __init__.py
│   ├── main.py              # API Entry point
│   └── rag_pipeline.py      # RAG + XBRL Logic
├── helper_lib/              # Core Utilities
│   ├── __init__.py
│   ├── edgar_parser.py      # SEC Downloader
│   ├── evaluator.py         # Evaluation metrics
│   ├── finetune.py          # Fine-tuning helpers
│   ├── retriever.py         # FAISS Vector Search
│   ├── utils.py             # Text cleaning & Ticker lookup
│   └── xbrl.py              # Structured Data Fetcher
├── data/                    # (Auto-generated) Stores filings & indexes
├── .dockerignore            # Docker exclusion list
├── .gitignore               # Git exclusion list
├── Dockerfile               # Container configuration
├── frontend.py              # User Interface (Streamlit)
├── pyproject.toml           # Project Configuration
├── README.md                # Documentation
└── requirements.txt         # Dependencies


🛠️ Setup & Installation

1. Clone the Repository

git clone https://github.com/louie0207/FinalProject.git
cd FinalProject


2. Configure Credentials

Security Warning: Never upload your API keys to GitHub.

Create a file named .env in the root folder.

Add your OpenAI API Key inside:

OPENAI_API_KEY=sk-your-key-here...


(Alternatively, you can export this key in your terminal session before running).

3. Create Virtual Environment & Install

# Create environment
python -m venv .venv-final

# Activate environment
# Mac/Linux:
source .venv-final/bin/activate
# Windows:
# .\.venv-final\Scripts\activate

# Install dependencies in editable mode
pip install -e .


🖥️ How to Run

You need two separate terminal windows to run this application.

Terminal 1: Backend API

This powers the brain of the copilot.

# Ensure you are in the project root and environment is active
source .venv-final/bin/activate

# Set API Key (if not using .env file)
export OPENAI_API_KEY="sk-..."

# Start the Server
uvicorn app.main:app --reload


Wait until you see: Application startup complete.

Terminal 2: Frontend UI

This launches the website.

# Ensure you are in the project root and environment is active
source .venv-final/bin/activate

# Run Streamlit
streamlit run frontend.py


The app should automatically open in your browser at http://localhost:8501.

🧪 Usage Guide

1. Ingest Data (The Foundation)

On the sidebar, enter a ticker (e.g., AAPL or TSLA).

Click "Ingest/Refresh Data".

Wait for the green success message. This downloads the latest 10-K and processes it for RAG.

2. View KPIs & Visuals (XBRL Dashboard)

Go to the "KPI Dashboard" tab.

Click "Load Metrics".

Charts: View interactive line charts for Revenue and Net Income trends over the last 3 years.

Export: Click the "📥 Download Financial Data (CSV)" button to get the raw data.

3. Chat with the Analyst (RAG)

Go to the "Financial Chat" tab.

Quick Start: Click one of the suggested questions like "Risk Summary" or "Revenue Growth".

Ask Custom Questions: "What does the management say about supply chain risks?"

Verify: Click the blue [Source: ...] links in the response to open the official SEC filing.

⚠️ Troubleshooting

Error: 404 Client Error ... CIK000000AAPL:

The system failed to convert Ticker to CIK. Ensure your internet is connected so it can fetch the SEC ticker map.

Error: 429 insufficient_quota:

Your OpenAI API key has run out of credits. Check your billing dashboard.

Error: ConnectionTimeout on Frontend:

Make sure Terminal 1 (Backend) is running! The website cannot work without the API server.

Plain Text Citations (Not Clickable):

This means you are using old data. Delete the data/ folder and click "Ingest" again to refresh the database with clickable link metadata.