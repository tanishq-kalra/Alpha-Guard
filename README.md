# Alpha-Guard 🛡️

**Forensic Credit Risk Platform**

Alpha-Guard is an institutional-grade financial forensics platform that combines traditional financial modeling (Altman Z-Score, Monte Carlo simulations) with advanced AI linguistic stress analysis to detect deception and assess credit risk in publicly traded companies.

Built by [Tanishq Kalra](https://tanishq-kalra.github.io/portfoliotanishq/) as a demonstration of full-stack engineering, financial modeling, and AI integration capabilities.

---

## 🎯 The Mission

To build a professional-grade forensic credit risk platform that reads between the lines of financial reports. Alpha-Guard doesn't just crunch numbers—it analyzes the semantic sentiment of management discussions to uncover hidden red flags and "Truth Scores."

---

## 🏗️ Architecture Flow

```mermaid
graph TD
    A[Frontend Dashboard<br/>Next.js + Tailwind] -->|Requests Analysis| B(FastAPI Backend)
    B -->|Fetches 10-K Data| C[SEC EDGAR API]
    B -->|Fallback| D[Yahoo Finance Scraper]
    C --> B
    D --> B
    B -->|Calculates Math| E[Risk Engine]
    E -->|Z-Score| B
    E -->|Monte Carlo GBM| B
    B -->|Extracts MD&A + Risk Factors| F[Gemini AI]
    F -->|Linguistic Analysis| F
    F -->|Detects Deception| B
    B -->|Generates PDF| G[ReportLab Engine]
    B -->|Returns JSON| A
```

1. **Data Ingestion**: Pulls XBRL financial facts from SEC EDGAR, with every metric aligned to the same fiscal year-end, plus market capitalisation from Yahoo Finance (SEC public float as fallback). International tickers use Yahoo Finance.
2. **Financial Engine**: Calculates the Altman Z-Score, choosing the right model variant for the company, and runs a Geometric Brownian Motion (GBM) Monte Carlo simulation to stress-test future revenue.
3. **Forensic AI Layer**: Extracts the MD&A and Risk Factors sections from the latest 10-K (skipping the table of contents and cross-references) and sends the MD&A to Gemini for sentiment and red-flag detection. Every quote Gemini returns is checked against the filing text.
4. **Synthesis**: Combines hedging/evasion density, verified red flags and the gap between management's tone and the Z-Score into a Truth Score, and raises a deception alert when a bullish narrative meets a Distress-zone balance sheet.
5. **Reporting**: Generates a branded executive PDF report from the same pipeline.

### How the scores work

**Altman Z-Score** — the model is picked automatically:

| Company | Model | Formula | Zones (Distress / Safe) |
|---|---|---|---|
| US manufacturer (SIC 2000–3999) | Altman Z (1968) | 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5, X4 = market cap / liabilities | < 1.81 / > 2.99 |
| Non-manufacturer, international, or no market cap | Altman Z'' (1995) | 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4, X4 = book equity / liabilities | < 1.10 / > 2.60 |
| Bank, insurer, investment firm (SIC 6000–6799) | — | Not applicable; the API says so instead of returning a misleading score | — |

**Truth Score** = 100 − penalties (0–100, shown with its breakdown):

| Penalty | Rule | Cap |
|---|---|---|
| Hedging | 1 point per hedging-score point above 15 (normal MD&A prose sits around 13–27) | 30 |
| Evasion | 2 points per evasion-score point above 2 | 25 |
| Red flags | 0.75 × total severity of Gemini's flagged sentences **whose quotes were found in the filing** | 30 |
| Sentiment gap | 15 for mild optimism bias, 40 for a bullish narrative from a Distress-zone company | 40 |

> **Demo mode (default):** with `TRUTH_SCORE_MODE=demo` the Truth Score is a simulated value derived from a SHA-256 hash of the ticker (range 30–95). It is identical on every run, needs no API, and is labelled **DEMO** in the UI and PDF. Set `TRUTH_SCORE_MODE=computed` to use the analysis below.

≥ 70 Credible · 40–69 Suspicious · < 40 Deceptive. Without a Gemini key the score uses the lexicon penalties only (labelled "heuristic"). If the MD&A can't be located (fewer than 300 words, as with some non-standard 10-K layouts) no score is given.

---

## 🚀 Key Features

*   **Smart Ticker Search**: Real-time autosuggestion for global market access.
*   **Altman Z-Score**: Original Z or Z'' chosen per company, with component breakdown and Safe / Gray / Distress zones.
*   **Forensic AI Audit**: Gemini-powered linguistic analysis with verified quotes, hedging and evasion scores, and a transparent "Truth Score".
*   **Monte Carlo Stress Test**: 1,000-path revenue simulation (configurable up to 100,000) using GBM to visualize 5-year percentile bands and decline probabilities.
*   **Executive PDF Reports**: One-click professional report generation via ReportLab.
*   **Premium UI**: "Bloomberg Terminal" aesthetic with glassmorphism, Framer Motion animations, and neon styling.

---

## 💻 Tech Stack

*   **Frontend**: Next.js 16, React 19, Tailwind CSS 4, Framer Motion, Recharts
*   **Backend**: Python, FastAPI, Uvicorn, httpx, ReportLab, Pydantic, NumPy, yfinance
*   **AI & Integrations**: Google Gemini API (`google-genai`), SEC EDGAR XBRL & full-text filings, Yahoo Finance

---

## ⚙️ Installation & Setup

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/Alpha-Guard.git
cd Alpha-Guard
```

**2. Backend Setup (Python 3.10+)**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```
*Create a `.env` file in the `backend/` directory:*
```ini
GEMINI_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SEC_USER_AGENT="Your Name your.email@example.com"   # SEC requires a real contact
ALLOWED_ORIGINS=http://localhost:3000                # comma-separated; "*" allows any
RATE_LIMIT_PER_MINUTE=10                             # audits/PDFs per IP per minute
TRUTH_SCORE_MODE=demo                                # demo (simulated) or computed
```
See `backend/.env.example` for details.

*Run the tests (no network access needed):*
```bash
pytest
```
*Start the backend server:*
```bash
uvicorn main:app --reload
```
*(The backend runs on `http://localhost:8000`)*

**3. Frontend Setup (Node.js)**
```bash
cd ../frontend
npm install
npm run dev
```
*Set `NEXT_PUBLIC_API_URL=http://localhost:8000` (e.g. in `frontend/.env.local`) to use a local backend; otherwise the deployed Render API is used.*
*(The frontend runs on `http://localhost:3000`)*

**4. Access the Platform**
Open `http://localhost:3000` in your browser.

---

*Disclaimer: Alpha-Guard is a conceptual tool for educational and demonstration purposes. It does not provide financial advice.*
