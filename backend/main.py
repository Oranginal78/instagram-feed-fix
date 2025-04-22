from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, uuid
from backend.image_tools import process_images, process_assembled_image


app = FastAPI()

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "File too large. Maximum allowed is 200MB."}
            )
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)



# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define API endpoints first (before mounting static files)
@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    # Create a unique session folder
    session_id = str(uuid.uuid4())
    folder = f"/tmp/{session_id}"
    os.makedirs(folder, exist_ok=True)
    
    # Save uploaded files
    for i, file in enumerate(files):
        path = os.path.join(folder, f"{i+1:03d}.jpg")
        with open(path, "wb") as f:
            f.write(await file.read())
    
    # Process the images
    zip_path = process_images(folder, mode="grid")
    
    # Return the ZIP file
    return FileResponse(zip_path, filename="instagram_feed.zip")

@app.post("/api/upload-assembled")
async def upload_assembled(file: UploadFile = File(...)):
    # Create a unique session folder
    session_id = str(uuid.uuid4())
    folder = f"/tmp/{session_id}"
    os.makedirs(folder, exist_ok=True)
    
    # Save the uploaded file
    path = os.path.join(folder, "assembled.jpg")
    with open(path, "wb") as f:
        f.write(await file.read())
    
    # Process the assembled image
    zip_path = process_assembled_image(path)
    
    # Return the ZIP file
    return FileResponse(zip_path, filename="instagram_feed.zip")

# Define the absolute path to the frontend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.abspath(os.path.join(current_dir, "../frontend"))
print(f"Serving frontend from: {frontend_path}")

# Mount the static files directory AFTER defining API routes
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
