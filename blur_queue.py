from PIL import Image
from io import BytesIO
from typing import NamedTuple
import blur, zipfile, uuid, queue, threading, os, time, shutil

class QueueItem(NamedTuple):
    id: uuid.UUID
    image_file_names: list[str]
    blur_threshold: float
    highlight_threshold: float

request_queue = queue.Queue()
HOURS_BEFORE_DELETE = 168 # 1 week
MINUTES_BEFORE_DELETE = HOURS_BEFORE_DELETE * 60
SECONDS_BEFORE_DELETE = MINUTES_BEFORE_DELETE * 60

def queue_handler():
    print("Queue handler started, waiting...")
    while True:
        item: QueueItem = request_queue.get()
        print(f"handling item: {item.id}")
        images = [Image.open(f"files/{item.id.hex}/{file_name}").convert("RGB") for file_name in item.image_file_names]
        images_by_file_name = dict(zip(item.image_file_names, images))
        results_by_file_name = blur.detect_objects(images_by_file_name)
        rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(
            results_by_file_name, item.blur_threshold, item.highlight_threshold)

        blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
        highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

        with zipfile.ZipFile(f"files/{item.id.hex}.zip", mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
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

        shutil.rmtree(f"files/{item.id.hex}")

        request_queue.task_done()
        print(f"finished item: {item.id}")

def file_delete_handler():
    while(True):
        dir = "files"
        print("Checking for files to delete")
        for file in os.listdir(dir):
            print(file)
            if file.endswith(".zip"):
                print("correct file format")
                if os.path.getmtime(f"files/{file}") + SECONDS_BEFORE_DELETE < time.time():
                    print("File too old, deleting")
                    os.remove(f"files/{file}")
                else:
                    print("File not too old")
        time.sleep(60)

threading.Thread(target=file_delete_handler, daemon=True).start()
threading.Thread(target=queue_handler, daemon=True).start()
