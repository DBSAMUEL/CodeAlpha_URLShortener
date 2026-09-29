# CodeAlpha_URLShortener

Task 1 of the CodeAlpha Backend Development Internship: a simple URL shortener built with **Flask** and **SQLite**.

## Features
- `POST /api/shorten` accepts a long URL and returns a unique 6-character short code
- Short code and original URL stored in SQLite
- `GET /<code>` redirects to the original URL and counts the click
- `GET /api/stats/<code>` returns click count and creation time
- Basic frontend at `/`
- Input validation (http/https only), duplicate URLs reuse the same code, collision-safe code generation

## Run locally
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## API
```bash
curl -X POST http://127.0.0.1:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/some/long/path"}'
```
Response:
```json
{"short_code": "aB3xY9", "short_url": "http://127.0.0.1:5000/aB3xY9", "original_url": "https://example.com/some/long/path"}
```
