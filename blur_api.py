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
    file_names = [file.filename for file in image_files]
    results = blur.detect_objects(images)
    (blurred_images, uncertain_images) = blur.blur_images(images, file_names, results, threshold)

    zipped_files = BytesIO()
    with zipfile.ZipFile(zipped_files, mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
        temp.mkdir("high_certainty")
        for blurred_image in blurred_images:
            image = blurred_image[0]
            file_name = blurred_image[1]
            image_as_bytes = BytesIO()
            image.save(image_as_bytes, "jpeg")
            image_as_bytes.seek(0)
            temp.writestr(f"high_certainty/{file_name}", image_as_bytes.getvalue())
        temp.mkdir("low_certainty")
        for uncertain_image in uncertain_images:
            image = uncertain_image[0]
            file_name = uncertain_image[1]
            image_as_bytes = BytesIO()
            image.save(image_as_bytes, "jpeg")
            image_as_bytes.seek(0)
            temp.writestr(f"low_certainty/uncertain_{file_name}", image_as_bytes.getvalue())
    return StreamingResponse(iter([zipped_files.getvalue()]), media_type="application/x-zip-compressed", headers={ "Content-Disposition": f"attachment; filename=images.zip"})
