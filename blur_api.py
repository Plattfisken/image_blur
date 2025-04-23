from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from io import BytesIO
from typing import List, NamedTuple
import blur, zipfile, uuid, json, queue, threading, math, os, datetime as dt

class QueueItem(NamedTuple):
    id: uuid.UUID
    image_file_names: list[str]
    blur_threshold: float
    highlight_threshold: float

class FinishedItem(NamedTuple):
    # blurred_images: dict
    # highlighted_images: dict
    zip_file_name: str
    added_time: dt.datetime

request_queue = queue.Queue()
finished_requests = {}
HOURS_BEFORE_DELETE = 168 # 1 week

def queue_handler():
    print("Queue handler started, waiting...")
    while True:
        item: QueueItem = request_queue.get()
        print(f"handling item: {item.id}")
        images = [Image.open(f"files/{file_name}") for file_name in item.image_file_names]
        images_by_file_name = dict(zip(item.image_file_names, images))
        results_by_file_name = blur.detect_objects(images_by_file_name)
        rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(
            results_by_file_name, item.blur_threshold, item.highlight_threshold)

        blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
        highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

        with zipfile.ZipFile(f"files/{item.id}.zip", mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
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

        # do we need to close?
        [image.close() for image in images]
        [os.remove(f"files/{file_name}") for file_name in item.image_file_names]

        finished_requests[item.id] = FinishedItem(f"{item.id}.zip", dt.datetime.now())

        request_queue.task_done()
        print(f"finished item: {item.id}")

threading.Thread(target=queue_handler, daemon=True).start()

app = FastAPI()

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

    if id in finished_requests:
        res: FinishedItem = finished_requests[id]

        print("removing old requests")
        now = dt.datetime.now()
        for key in finished_requests.keys():
            added_time: dt.datetime = finished_requests[key].added_time
            print(f"{key}: added {added_time}")
            time_diff = now - added_time
            hours = math.floor((time_diff.total_seconds() / 60) / 60)
            print(f"{hours} hours since creation")
            if hours > HOURS_BEFORE_DELETE:
                print("deleting item")
                os.remove(f"files/{finished_requests[key].zip_file_name}")
                finished_requests.pop(key)

            else:
                print("item too young, keeping")

        return FileResponse(f"files/{res.zip_file_name}", media_type="application/x-zip-compressed", filename="images.zip")
    else:
        return "Item not ready"

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


    # images = [await image_file.read() for image_file in image_upload_files]
    # images_by_file_name = dict(zip(file_names, images))

    id = uuid.uuid4()
    for image_file in image_upload_files:
        print(image_file.content_type)
        file_path = f"files/{str(image_file.filename or id.hex)}"
        with open(file_path, "wb+") as file_obj:
            file_obj.write(image_file.file.read())

    file_names = [str(file.filename or id.hex) for file in image_upload_files]
    item = QueueItem(id, file_names, blur_threshold, highlight_threshold)
    request_queue.put(item)
    return id.hex
