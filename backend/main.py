from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from PIL import Image
import os, uuid

from backend.image_tools import process_images, process_assembled_image

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Max upload limit (50 MB per request)
MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_IMAGE_WIDTH = 3500
MAX_IMAGE_HEIGHT = 15000

# Middleware to block oversized files
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "File too large. Max size is 200MB."}
            )
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)

@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    session_id = str(uuid.uuid4())
    folder = f"/tmp/{session_id}"
    os.makedirs(folder, exist_ok=True)

    for i, file in enumerate(files):
        if file.content_type not in ["image/jpeg", "image/png"]:
            return JSONResponse(status_code=400, content={"detail": f"Unsupported file type: {file.content_type}"})
        
        path = os.path.join(folder, f"{i+1:03d}.jpg")
        with open(path, "wb") as f:
            f.write(await file.read())

    zip_path = process_images(folder, mode="grid")
    return FileResponse(zip_path, filename="instagram_feed.zip")


@app.post("/api/upload-assembled")
async def upload_assembled(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    folder = f"/tmp/{session_id}"
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, "assembled.jpg")
    contents = await file.read()
    
    if len(contents) > MAX_UPLOAD_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Image too large. Max file size is 50MB."})

    with open(path, "wb") as f:
        f.write(contents)

    try:
        with Image.open(path) as img:
            if img.width > MAX_IMAGE_WIDTH or img.height > MAX_IMAGE_HEIGHT:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Image dimensions too large. Max allowed: {MAX_IMAGE_WIDTH} x {MAX_IMAGE_HEIGHT}px."}
                )
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Invalid image: {str(e)}"})

    zip_path = process_assembled_image(path)
    return FileResponse(zip_path, filename="instagram_feed.zip")


# Serve frontend
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.abspath(os.path.join(current_dir, "../frontend"))
print(f"Serving frontend from: {frontend_path}")

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
