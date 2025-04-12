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
    print(file_names)
    images_by_file_name = dict(zip(file_names, images))
    print(images_by_file_name)

    results = blur.detect_objects(images)
    results_by_file_name = dict(zip(file_names, results))

    rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(results_by_file_name, blur_threshold, highlight_threshold)

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
