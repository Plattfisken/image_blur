import blur
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import List
import zipfile

app = FastAPI()

@app.post("/")
def blur_image(blur_threshold: float, highlight_threshold: float, image_files: List[UploadFile] = File(...)):
    if(blur_threshold <= highlight_threshold):
        raise HTTPException(status_code=400, detail="highlight_threshold must be lower than blur_threshold")

    images = [Image.open(image_file.file) for image_file in image_files]
    file_names = [file.filename for file in image_files]
    images_by_file_name = dict(zip(file_names, images))

    results = blur.detect_objects(images)
    results_by_file_name = dict(zip(file_names, results))

    rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(results_by_file_name, blur_threshold, highlight_threshold)

    blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
    highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

    zipped_files = BytesIO()
    with zipfile.ZipFile(zipped_files, mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
        def compress_images_in_directory(directory_name, imgs_by_file_name):
            temp.mkdir(directory_name)
            for file_name in imgs_by_file_name.keys():
                image = imgs_by_file_name[file_name]
                image_as_bytes = BytesIO()
                image.save(image_as_bytes, "jpeg")
                image_as_bytes.seek(0)
                temp.writestr(f"{directory_name}/{file_name}", image_as_bytes.getvalue())
        compress_images_in_directory("high_certainty", blurred_images)
        compress_images_in_directory("low_certainty", highlighted_images)
    return StreamingResponse(iter([zipped_files.getvalue()]), media_type="application/x-zip-compressed", headers={ "Content-Disposition": f"attachment; filename=images.zip"})
