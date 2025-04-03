from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image
import torch
import sys
import cv2
import datetime
import os

def get_file_extension(file_name):
    reversed_file_name = file_name[::-1]
    last_dot_index = reversed_file_name.find(".")
    reversed_file_extension = reversed_file_name[:last_dot_index]
    return reversed_file_extension[::-1]

# TODO: hantera exceptions
image_file_paths = sys.argv[1::]
images = [Image.open(arg) for arg in sys.argv[1::]]

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", revision="no_timm")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", revision="no_timm")

inputs = processor(images=images, return_tensors="pt")
outputs = model(**inputs)

sizes = [image.size[::-1] for image in images]

target_sizes = torch.tensor(sizes)

results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.5)

os.makedirs("./results", exist_ok=True)
for result, image_path in zip(results, image_file_paths):
    image = cv2.imread(image_path)
    ksize = (30, 30)
    for box, label in zip(result["boxes"], result["labels"]):
        if(model.config.id2label[label.item()] == "person"):
            # extract coordinates and round from box
            box = [round(i) for i in box.tolist()]
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
            # rectangle to blur from image
            roi = image[y1:y2, x1:x2]
            # apply blur to rectangle
            blur = cv2.blur(roi, ksize)
            # insert blur back into image
            image[y1:y2, x1:x2] = blur
    now = datetime.datetime.now()
    file_name = f"./results/{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-{now.second}-{now.microsecond}.{get_file_extension(image_path)}"
    cv2.imwrite(file_name, image)
    print(file_name)
