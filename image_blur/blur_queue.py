from PIL import Image
from io import BytesIO
from typing import NamedTuple
import blur, zipfile, uuid, queue, threading, os, time, shutil

class QueueItem(NamedTuple):
    id: uuid.UUID
    blur_threshold: float
    highlight_threshold: float

request_queue = queue.Queue()
HOURS_BEFORE_DELETE = 168 # 1 week
MINUTES_BEFORE_DELETE = HOURS_BEFORE_DELETE * 60
SECONDS_BEFORE_DELETE = MINUTES_BEFORE_DELETE * 60

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50mb

def queue_handler():
    print("Queue handler started, waiting...")
    while True:
        item: QueueItem = request_queue.get()
        print(f"handling item: {item.id}")

        # getting the files for this request
        file_names = os.listdir(f"files/{item.id.hex}")

        # removing files that exceed the size limit, putting them aside
        invalid_files_too_large = []
        for file_name in file_names:
            file_size = os.path.getsize(f"files/{item.id.hex}/{file_name}")
            if file_size > MAX_FILE_SIZE:
                print(f"file: {file_name} with size: {file_size} too large (max: {MAX_FILE_SIZE})")
                invalid_files_too_large.append(file_name)
                file_names.remove(file_name)

        # attempt to open the files as images, putting aside files that fail to be read as an image
        images = []
        invalid_files_invalid_format = []
        for file_name in file_names:
            try:
                image = Image.open(f"files/{item.id.hex}/{file_name}").convert("RGB")
                images.append(image)
                print(f"file: {file_name} sucessfully opened")
            except:
                print(f"file: {file_name} could not be opened as image")
                invalid_files_invalid_format.append(file_name)
                file_names.remove(file_name)

        # let the model detect the objects, then get the rectangles containing people. Returns two lists;
        # one with a low threshold and one with a high threshold
        images_by_file_name = dict(zip(file_names, images))

        results_by_file_name = blur.detect_objects(images_by_file_name)

        rects_by_file_name_high_certainty, rects_by_file_name_low_certainty = blur.get_rects(
            results_by_file_name, item.blur_threshold, item.highlight_threshold)

        # blur the rectangles in the list with high certainty, and highlight the rectangles in the list with low certainty
        blurred_images = blur.blur_rects_in_images(images_by_file_name, rects_by_file_name_high_certainty)
        highlighted_images = blur.highlight_rects_in_images(images_by_file_name, rects_by_file_name_low_certainty)

        # result_images contains every input file that was successfully handled, with the blurred version for those images where a person was
        # detected with high certainty.
        # Files that were not handled (too large, or couldn't be opened), are not part of this list, as they require manual review.
        result_images = images_by_file_name
        for key in blurred_images.keys():
            result_images[key] = blurred_images[key]

        # create compressed files containing all results in different directories:
        # result:
        #   all sucessfully handled images
        # highlighted_images_for_manual_review:
        #   images containing one or more rectangles above the low threshold but below the high threshold.
        #   Rectangles are highlighted with green
        # unhandled_files_too_large:
        #   files that were not handled due to exceeding the size limit.
        # unhandled_files_invalid_format:
        #   files that were not handled due to being unable to be opened by PIL.
        with zipfile.ZipFile(f"files/{item.id.hex}.zip", mode="w", compression=zipfile.ZIP_DEFLATED) as temp:
            def compress_images_in_directory(directory_name, imgs_by_file_name):
                temp.mkdir(directory_name)
                for file_name in imgs_by_file_name.keys():
                    image: Image.Image = imgs_by_file_name[file_name]
                    image_as_bytes = BytesIO()

                    # we attempt to determine the file format based on the file extension. If we can't then we save it as png
                    file_name_without_ext, file_extension = os.path.splitext(file_name)
                    try:
                        format = Image.EXTENSION[file_extension]
                    except:
                        format = "png"
                    image.save(image_as_bytes, format)

                    image_as_bytes.seek(0)
                    if format == "png":
                        save_name = f"{file_name_without_ext}.png"
                    else:
                        save_name = f"{file_name_without_ext}{file_extension}"

                    temp.writestr(f"{directory_name}/{save_name}", image_as_bytes.getvalue())
            compress_images_in_directory("result", result_images)
            compress_images_in_directory("highlighted_images_for_manual_review", highlighted_images)

            temp.mkdir("unhandled_files_too_large")
            for file_name in invalid_files_too_large:
                temp.write(f"files/{item.id.hex}/{file_name}", f"unhandled_files_too_large/{file_name}")
            temp.mkdir("unhandled_files_invalid_format")
            for file_name in invalid_files_invalid_format:
                temp.write(f"files/{item.id.hex}/{file_name}", f"unhandled_files_invalid_format/{file_name}")
            for file_name in rects_by_file_name_low_certainty.keys():
                rects = [','.join(map(str, rect.tolist())) for rect in rects_by_file_name_low_certainty[file_name]]
                file = '\n'.join(rects)
                temp.writestr(f"highlighted_images_for_manual_review/{os.path.splitext(file_name)[0]}.txt", file)

        # do we need to close?
        [image.close() for image in images]

        # remove the directory of this request
        shutil.rmtree(f"files/{item.id.hex}")

        request_queue.task_done()
        print(f"finished item: {item.id}")

def file_delete_handler():
    while(True):
        dir = "files"
        print("Checking for files to delete")
        for file in os.listdir(dir):
            if file.endswith(".zip"):
                if os.path.getmtime(f"files/{file}") + SECONDS_BEFORE_DELETE < time.time():
                    print(f"File: {file} too old, deleting")
                    os.remove(f"files/{file}")
        time.sleep(12 * 60 * 60)

threading.Thread(target=file_delete_handler, daemon=True).start()
threading.Thread(target=queue_handler, daemon=True).start()
