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
    images_by_file_name = dict(zip(file_names, images))

    results = blur.detect_objects(images)

    rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(file_names, results, threshold, 0.3)

    blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
    highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

    # (blurred_images, uncertain_images) = blur.blur_images(images, file_names, results, threshold)

    zipped_files = BytesIO()
    with zipfile.ZipFile(zipped_files, mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
        temp.mkdir("high_certainty")
        for file_name in blurred_images.keys():
            image = blurred_images[file_name]
            image_as_bytes = BytesIO()
            image.save(image_as_bytes, "jpeg")
            image_as_bytes.seek(0)
            temp.writestr(f"high_certainty/{file_name}", image_as_bytes.getvalue())
        temp.mkdir("low_certainty")
        for file_name in highlighted_images.keys():
            image = highlighted_images[file_name]
            image_as_bytes = BytesIO()
            image.save(image_as_bytes, "jpeg")
            image_as_bytes.seek(0)
            temp.writestr(f"low_certainty/uncertain_{file_name}", image_as_bytes.getvalue())
    return StreamingResponse(iter([zipped_files.getvalue()]), media_type="application/x-zip-compressed", headers={ "Content-Disposition": f"attachment; filename=images.zip"})
