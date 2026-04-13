# PDF Compressor Service

A lightweight FastAPI service that compresses PDFs using Ghostscript. Accepts a PDF upload and returns a compressed PDF.

## Endpoints

### `POST /compress`

Upload a PDF and receive a compressed version.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `level` | string | `ebook` | Compression preset: `screen`, `ebook`, `printer`, `prepress` |
| `dpi` | int | — | Override DPI (72–600). Overrides the level preset. |
| `color_image_resolution` | int | — | Override color/gray image resolution specifically (72–600). |

**Compression Levels:**

| Level | DPI | Use Case |
|---|---|---|
| `screen` | ~72 | Smallest file, lowest quality. Good for previews. |
| `ebook` | ~150 | Balanced. **Recommended for email attachments.** |
| `printer` | ~300 | High quality with moderate compression. |
| `prepress` | ~300 | Highest quality, least compression. |

**Response Headers:**

- `X-Original-Size-Bytes` — original file size
- `X-Compressed-Size-Bytes` — compressed file size
- `X-Size-Reduction-Percent` — percentage reduction

### `GET /health`

Returns service status and confirms Ghostscript is available.

---

## Example Usage

```bash
# Basic compression (ebook preset)
curl -X POST "https://your-service.railway.app/compress" \
  -F "file=@large_document.pdf" \
  -o compressed.pdf

# Aggressive compression for email
curl -X POST "https://your-service.railway.app/compress?level=screen" \
  -F "file=@large_document.pdf" \
  -o compressed.pdf

# Custom DPI
curl -X POST "https://your-service.railway.app/compress?dpi=120" \
  -F "file=@large_document.pdf" \
  -o compressed.pdf
```

---

## Deploy on Railway

1. Push this folder to a GitHub repo
2. Create a new project on [Railway](https://railway.app)
3. Connect your GitHub repo — Railway will auto-detect the Dockerfile
4. Deploy — your service will be live with a public URL

No environment variables required.
