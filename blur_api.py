from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List
import blur_queue, uuid, json, os

app = FastAPI()

# TODO: we should probably only allow the application that made the request to get the result back. As it is now, anyone with access to the filename
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

    # NOTE: there is a __slight__ risk here that the thread responsible for deleting files deletes this file right after the check but before
    # it has been returned.
    path = f"files/{id.hex}.zip"
    if os.path.isfile(path):
        return FileResponse(path, media_type="application/x-zip-compressed", filename="images.zip")
    else:
        return "Item not ready or invalid GUID"

@app.post("/enqueue")
async def enqueue_images(application_name: str, application_guid: str, blur_threshold: float, highlight_threshold: float, image_upload_files: List[UploadFile] = File(...)):
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

    file_names = [str(file.filename or id.hex) for file in image_upload_files]
    item = blur_queue.QueueItem(id, file_names, blur_threshold, highlight_threshold)
    blur_queue.request_queue.put(item)
    return id.hex
