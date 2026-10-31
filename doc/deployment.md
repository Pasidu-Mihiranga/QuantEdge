# Deploying the app

The booklet requires Streamlit as the interface and accepts an app that is deployed or runnable locally with one command. `make run` meets the second; a public link is the safer choice for judges.

## Streamlit Community Cloud (recommended, free)

1. Merge the work into the branch you want to deploy and push it to GitHub.
2. Sign in at https://share.streamlit.io with a GitHub account that can see the repository.
3. Choose **Create app**, then the repository, the branch and the main file `app/Home.py`.
4. Under **Advanced settings**, choose **Python 3.12**. The packages come from `requirements.txt`.
5. Deploy, then open every page once and check the verdict on the first page.

The app reads `data/artifacts/` only: it needs no secrets, API keys or network data, and it does not need the git tag. An idle app sleeps and wakes on the next visit, so open it shortly before judging.

## Any other host (AWS and others)

Any host works if it runs the same command, so Streamlit stays the interface. On a small Linux server with Python 3.12:

```
pip install -r requirements.txt
python -m streamlit run app/Home.py --server.port 8501 --server.address 0.0.0.0
```

Open port 8501 to the web, or put a reverse proxy in front for HTTPS. AWS is not free in the long run, and the booklet treats a free-tier toolkit as a fairness requirement, so Community Cloud is the better fit here.
