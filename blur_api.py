from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import List
from PIL import Image
import blur_queue, blur, uuid, json, os, io

app = FastAPI()

# TODO: we should probably only allow the application that made the request to get the result back. As it is now, any app with access to the filename
# could get the result.
@app.get("/result")
async def get_result_if_ready(application_name: str, application_guid: str, request_guid: str):
    with open("auth_test_data.json", mode="r") as json_file:
        authorized_apps = json.load(json_file)
    try:
        app_guid = authorized_apps[application_name]
    except:
        raise HTTPException(status_code=400, detail="application_name invalid")

    try:
        attempted_auth_guid = uuid.UUID(application_guid)
    except:
        raise HTTPException(status_code=400, detail="application_guid invalid")

    if(uuid.UUID(app_guid) != attempted_auth_guid):
        raise HTTPException(status_code=401)

    try:
        id = uuid.UUID(request_guid)
    except:
        raise HTTPException(status_code=400, detail="request_guid invalid")

    # NOTE: maybe there is a __slight__ risk here that the thread responsible for deleting files deletes this file right after the check but
    # before it has been returned.
    path = f"files/{id.hex}"
    if os.path.isdir(path):
        return "Item not ready" 
    elif os.path.isfile(f"{path}.zip"):
        return FileResponse(f"{path}.zip", media_type="application/x-zip-compressed", filename="result.zip")
    else:
        raise HTTPException(status_code=400, detail="request_guid not representing an item in the queue")

@app.post("/enqueue")
async def enqueue_images(application_name: str, application_guid: str, blur_threshold: float, highlight_threshold: float, image_upload_files: List[UploadFile] = File(...)):
    with open("auth_test_data.json", mode="r") as auth_file:
        authorized_apps = json.load(auth_file)
    try:
        app_guid = authorized_apps[application_name]
    except:
        raise HTTPException(status_code=400, detail="application_name invalid")

    try:
        attempted_auth_guid = uuid.UUID(application_guid)
    except:
        raise HTTPException(status_code=400, detail="application_guid invalid")

    if(uuid.UUID(app_guid) != attempted_auth_guid):
        raise HTTPException(status_code=401)

    if(blur_threshold <= highlight_threshold):
        raise HTTPException(status_code=400, detail="highlight_threshold must be lower than blur_threshold")

    id = uuid.uuid4()
    dir_path = f"files/{id.hex}"
    os.mkdir(dir_path)
    for image_file in image_upload_files:
        print(image_file.content_type)
        file_path = f"{dir_path}/{str(image_file.filename or uuid.uuid4())}"
        with open(file_path, "wb+") as file_obj:
            file_obj.write(image_file.file.read())

    item = blur_queue.QueueItem(id, blur_threshold, highlight_threshold)
    blur_queue.request_queue.put(item)
    return id.hex

@app.post("/blur_rect")
async def blur_rect(application_name: str, application_guid: str, rect_file: UploadFile = File(...), image_file: UploadFile = File(...)):
    with open("auth_test_data.json", mode="r") as auth_file:
        authorized_apps = json.load(auth_file)
    try:
        app_guid = authorized_apps[application_name]
    except:
        raise HTTPException(status_code=400, detail="application_name invalid")

    try:
        attempted_auth_guid = uuid.UUID(application_guid)
    except:
        raise HTTPException(status_code=400, detail="application_guid invalid")

    if(uuid.UUID(app_guid) != attempted_auth_guid):
        raise HTTPException(status_code=401)

    image_by_file_name = {}
    image_by_file_name[image_file.filename] = Image.open(image_file.file).convert("RGB")

    rect_as_strings = (await rect_file.read()).decode().splitlines()
    rects = []
    for rect_as_string in rect_as_strings:
        rect_coords_as_strings = rect_as_string.split(',')
        rect_coords = [float(coord_as_str) for coord_as_str in rect_coords_as_strings]
        rects.append(rect_coords)

    boxes_by_file_name = {}
    boxes_by_file_name[image_file.filename] = rects
    blurred_img = blur.blur_rects_in_images(image_by_file_name, boxes_by_file_name)[image_file.filename]

    return_file = io.BytesIO()
    blurred_img.save(return_file, "JPEG")
    return_file.seek(0)
    return StreamingResponse(return_file, media_type="image/jpeg")
