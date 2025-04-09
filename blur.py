from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
import cv2
from PIL import Image
import numpy as np

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", revision="no_timm")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", revision="no_timm")

def pil_to_cv2(pil_images):
    return [cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR) for pil_img in pil_images]

def cv2_to_pil(cv2_images):
    return [Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)) for cv2_img in cv2_images]

def detect_objects(images):
    inputs = processor(images=images, return_tensors="pt")
    outputs = model(**inputs)

    sizes = [image.size[::-1] for image in images]

    target_sizes = torch.tensor(sizes)

    results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)
    return results

def blur_images(images, results, threshold):
    blurred_images = []
    for result, cv2_image in zip(results, pil_to_cv2(images)):
        ksize = (30, 30)
        for box, label, score in zip(result["boxes"], result["labels"], result["scores"]):
            if(model.config.id2label[label.item()] == "person"):
                print( f"Detected {model.config.id2label[label.item()]} with confidence" f"{round(score.item(), 3)} at location {box}")
                if(score.item() > threshold):
                    # extract coordinates and round from box
                    box = [round(i) for i in box.tolist()]
                    x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                    # rectangle to blur from image
                    roi = cv2_image[y1:y2, x1:x2]
                    # apply blur to rectangle
                    blur = cv2.blur(roi, ksize)
                    # insert blur back into image
                    cv2_image[y1:y2, x1:x2] = blur
        blurred_images.append(cv2_image)
    return cv2_to_pil(blurred_images)
