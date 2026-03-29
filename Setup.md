# Setup Guide

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed (for local planner + critic agents)

---

## 1. Clone and install

```bash
git clone <your-repo-url>
cd travelmind
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure environment

```bash
cp .env.example .env
```

Create `.env` and fill in:

the environmental variables get idea from the **.env.example**

**No keys yet?** Enable mock mode in the app Settings page — you can run everything with fixture data.

## 3. Start Ollama (recommended)

```bash
# Install: https://ollama.com/download
ollama pull llama3.2      # ~2GB, recommended
# or:
ollama pull mistral       # lighter alternative

ollama serve              # starts the local server on port 11434
```

The planner and critic agents use Ollama. If Ollama is not running, they automatically fall back to Claude.

## 4. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## 5. Test without the UI

```bash
# Quick test with mock data (no API keys needed)
python run.py

# Live test with real APIs
python run.py --live --dest "Barcelona, Spain" --budget 2000
```

