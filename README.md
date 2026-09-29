# Meta & AI Tag Checker

Self-contained service for detecting AI and Meta provenance markers, C2PA manifests, IPTC digitalSourceType tags, and generation metadata.

## Run Locally
```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000).

## Run with Docker
```bash
docker build -t meta-ai-checker .
docker run -p 8000:8000 meta-ai-checker
```


```code
podman run --rm --net=host meta-ai-checker
```