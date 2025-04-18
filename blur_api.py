from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import List, NamedTuple
import blur, zipfile, uuid, json, queue, threading

class QueueItem(NamedTuple):
    id: uuid.UUID
    image_bytes_by_file_name: dict[str, bytes]
    blur_threshold: float
    highlight_threshold: float

class FinishedItem(NamedTuple):
    blurred_images: dict
    highlighted_images: dict

request_queue = queue.Queue()
finished_requests = {}

def queue_handler():
    print("Queue handler started, waiting...")
    while True:
        item: QueueItem = request_queue.get()
        print(f"handling item: {item.id}")
        file_names = item.image_bytes_by_file_name.keys()
        images = [Image.open(BytesIO(item.image_bytes_by_file_name[file_name])) for file_name in file_names]
        images_by_file_name = dict(zip(file_names, images))
        results_by_file_name = blur.detect_objects(images_by_file_name)
        rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(
            results_by_file_name, item.blur_threshold, item.highlight_threshold)

        blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
        highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

        # do we need to close?
        [image.close() for image in images]

        finished_requests[item.id] = FinishedItem(blurred_images, highlighted_images)

        request_queue.task_done()
        print(f"finished item: {item.id}")

threading.Thread(target=queue_handler, daemon=True).start()

app = FastAPI()

@app.get("/result")
def get_result_if_ready(application_name: str, application_guid: str, request_guid: str):
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
        res: FinishedItem = finished_requests.pop(id)
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
            compress_images_in_directory("high_certainty", res.blurred_images)
            compress_images_in_directory("low_certainty", res.highlighted_images)

        # do we need to close?
        [image.close() for image in res.blurred_images.values()]
        [image.close() for image in res.highlighted_images.values()]
        return StreamingResponse(iter([zipped_files.getvalue()]), media_type="application/x-zip-compressed", headers={ "Content-Disposition": f"attachment; filename=images.zip"})
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

    id = uuid.uuid4()
    images = [await image_file.read() for image_file in image_upload_files]
    file_names = [str(file.filename or id.hex) for file in image_upload_files]
    images_by_file_name = dict(zip(file_names, images))

    item = QueueItem(id, images_by_file_name, blur_threshold, highlight_threshold)
    request_queue.put(item)
    return id.hex
