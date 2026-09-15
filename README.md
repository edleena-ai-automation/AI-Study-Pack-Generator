# StudyPack AI

A Streamlit application that generates personalized study packs through a multi-stage AI workflow.

## AI Workflow

1. Planning
2. Content Generation
3. Assessment
4. Review
5. Refinement

The workflow passes structured state between stages, validates AI output with Pydantic, retries failed model calls, and sends failed reviews through a bounded refinement loop.

## Project Files

```text
ai-study-pack-generator/
├── app.py
├── workflow.py
├── models.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Deploy on Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload all files from this folder to the repository root.
3. Open Streamlit Community Cloud.
4. Create a new app from your GitHub repository.
5. Select `app.py` as the main file.
6. Open **Advanced settings → Secrets**.
7. Add your OpenAI API key:

```toml
OPENAI_API_KEY = "your-openai-api-key"
```

8. Deploy the app.

## Local Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Set the API key before running locally:

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
streamlit run app.py
```

### macOS / Linux

```bash
export OPENAI_API_KEY="your-openai-api-key"
streamlit run app.py
```

## Important

Never upload your API key to GitHub. Keep it in Streamlit Secrets.
