import os
import subprocess
import tempfile
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from enum import Enum

app = FastAPI(
    title="PDF Compressor",
    description="Upload a PDF and get a compressed version back.",
    version="1.0.0"
)


class CompressionLevel(str, Enum):
    screen = "screen"      # ~72 DPI — smallest file, lowest quality
    ebook = "ebook"        # ~150 DPI — good balance (recommended)
    printer = "printer"    # ~300 DPI — high quality, moderate compression
    prepress = "prepress"  # ~300 DPI — highest quality, least compression


def ghostscript_available() -> bool:
    return shutil.which("gs") is not None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ghostscript": ghostscript_available()
    }


@app.post("/compress")
async def compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to compress"),
    level: CompressionLevel = Query(
        default=CompressionLevel.ebook,
        description="Compression level: screen < ebook < printer < prepress"
    ),
    dpi: int = Query(
        default=None,
        ge=72,
        le=600,
        description="Override DPI (optional). Overrides the level preset."
    ),
    color_image_resolution: int = Query(
        default=None,
        ge=72,
        le=600,
        description="Override color image resolution specifically (optional)."
    ),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

    if not ghostscript_available():
        raise HTTPException(
            status_code=500,
            detail="Ghostscript (gs) is not installed. Cannot compress PDF."
        )

    # Use persistent temp files — FileResponse streams AFTER the handler returns,
    # so a `with TemporaryDirectory()` block would delete files too early.
    tmpdir = tempfile.mkdtemp()

    def cleanup():
        shutil.rmtree(tmpdir, ignore_errors=True)

    try:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "compressed.pdf")

        # Save uploaded file
        contents = await file.read()
        with open(input_path, "wb") as f:
            f.write(contents)

        input_size = os.path.getsize(input_path)

        # Build Ghostscript command
        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{level.value}",
            "-dNEWSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-dQUIET",
        ]

        if dpi:
            cmd += [f"-r{dpi}"]

        if color_image_resolution:
            cmd += [
                f"-dColorImageResolution={color_image_resolution}",
                f"-dGrayImageResolution={color_image_resolution}",
            ]

        cmd += [f"-sOutputFile={output_path}", input_path]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            cleanup()
            raise HTTPException(
                status_code=500,
                detail=f"Ghostscript error: {result.stderr.strip()}"
            )

        if not os.path.exists(output_path):
            cleanup()
            raise HTTPException(status_code=500, detail="Compression produced no output.")

        output_size = os.path.getsize(output_path)
        reduction = round((1 - output_size / input_size) * 100, 1) if input_size > 0 else 0

        stem = os.path.splitext(file.filename)[0]
        out_filename = f"{stem}_compressed_{level.value}.pdf"

        # Schedule cleanup AFTER the response has been fully sent
        background_tasks.add_task(cleanup)

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=out_filename,
            headers={
                "X-Original-Size-Bytes": str(input_size),
                "X-Compressed-Size-Bytes": str(output_size),
                "X-Size-Reduction-Percent": str(reduction),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        cleanup()
        raise HTTPException(status_code=500, detail=str(e))
