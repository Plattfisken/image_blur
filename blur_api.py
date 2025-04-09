import blur
from PIL import Image
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import List
import zipfile

app = FastAPI()

@app.post("/")
def blur_image(threshold: float, image_files: List[UploadFile] = File(...)):
    images = [Image.open(image_file.file) for image_file in image_files]
    results = blur.detect_objects(images, threshold)
    blurred_images = blur.blur_images(images, results)

    zipped_files = BytesIO()
    with zipfile.ZipFile(zipped_files, mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
        for image, blurred_image in zip(image_files, blurred_images):
            image_as_bytes = BytesIO()
            blurred_image.save(image_as_bytes, "jpeg")
            image_as_bytes.seek(0)
            temp.writestr(image.filename, image_as_bytes.getvalue())
    return StreamingResponse(iter([zipped_files.getvalue()]), media_type="application/x-zip-compressed", headers={ "Content-Disposition": f"attachment; filename=images.zip"})
