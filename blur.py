from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
import cv2
from PIL import Image
import numpy as np

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", revision="no_timm")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", revision="no_timm")

def pil_to_cv2(pil_img):
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def cv2_to_pil(cv2_img):
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))

def detect_objects(images):
    inputs = processor(images=images, return_tensors="pt")
    outputs = model(**inputs)

    sizes = [image.size[::-1] for image in images]

    target_sizes = torch.tensor(sizes)

    results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.1)
    return results

# extracts the rectangles that contain a person into two dictionaries with file_name as key and a list of rectangles as values;
# one of high certainty where the score > threshold, and one of low where score <= threshold but > lower_bound
def get_rects(file_names: list[str], results, threshold: float, lower_bound: float) -> tuple[dict[str, list], dict[str, list]]:
    boxes_by_file_name_high_certainty = dict.fromkeys(file_names, [])
    boxes_by_file_name_low_certainty = dict.fromkeys(file_names, [])

    for file_name, result in zip(file_names, results):
        for box, label, score in zip(result["boxes"], result["labels"], result["scores"]):

            if(model.config.id2label[label.item()] == "person"):
                if(score.item() > threshold):
                    boxes_by_file_name_high_certainty[file_name].append(box)

                elif(score.item() > lower_bound):
                    boxes_by_file_name_low_certainty[file_name].append(box)

    return boxes_by_file_name_high_certainty, boxes_by_file_name_low_certainty

def blur_rects_in_images(images_by_file_name, boxes_by_file_name):
    blurred_images = {}
    ksize = (30, 30)

    for image_file_name in boxes_by_file_name.keys():
        image = pil_to_cv2(images_by_file_name[image_file_name])

        print(f"{len(boxes_by_file_name[image_file_name])} rects in image: {image_file_name}")
        for box in boxes_by_file_name[image_file_name]:
            box = [max(round(i), 0) for i in box.tolist()]
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
            print(f"x1:{x1} y1:{y1} x2:{x2} y2:{y2}")
            # rectangle to blur from image
            roi = image[y1:y2, x1:x2]
            print(f"{roi}")
            blur = cv2.blur(roi, ksize)
            image[y1:y2, x1:x2] = blur

        blurred_images[image_file_name] = cv2_to_pil(image)

    return blurred_images

def highlight_rects_in_images(images_by_file_name, boxes_by_file_name):
    highlighted_images = {}

    for image_file_name in boxes_by_file_name.keys():
        image = pil_to_cv2(images_by_file_name[image_file_name])

        for box in boxes_by_file_name[image_file_name]:
            box = [max(round(i), 0) for i in box.tolist()]
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
            start_point = (x1, y1); end_point = (x2, y2); color = (0, 255, 0); thickness = 2
            cv2.rectangle(image, start_point, end_point, color, thickness)
            # rectangle to blur from image

        highlighted_images[image_file_name] = cv2_to_pil(image)

    return highlighted_images

# def blur_images(images, file_names, results, threshold):
#     blurred_images = []
#     uncertain_images = []
#     for result, image, file_name in zip(results, images, file_names):
#         cv2_image = pil_to_cv2(image)
#         ksize = (30, 30)
#         uncertain_image = cv2_image.copy()
#         uncertain_rect_added = False;
#         for box, label, score in zip(result["boxes"], result["labels"], result["scores"]):
#             if(model.config.id2label[label.item()] == "person"):
#                 print( f"Detected {model.config.id2label[label.item()]} with confidence" f"{round(score.item(), 3)} at location {box}")
#                 # NOTE: for some reason the model sometimes spits out negative coordinates at low confidence levels, this seems to trigger an
#                 # assertion later in cv2.blur, we therefor use max() to clamp the values to at least zero
#                 box = [max(round(i), 0) for i in box.tolist()]
#                 x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
#                 # rectangle to blur from image
#                 roi = cv2_image[y1:y2, x1:x2]
#                 if(score.item() > threshold):
#                     print(f"confidence {score.item()} higher than threshold {threshold}. Blurring rectangle")
#                     # extract coordinates and round from box
#                     # apply blur to rectangle
#                     blur = cv2.blur(roi, ksize)
#                     # insert blur back into image
#                     cv2_image[y1:y2, x1:x2] = blur
#                 elif(score.item() > 0.3):
#                     uncertain_rect_added = True
#                     print(f"confidence {score.item()} lower than threshold {threshold}. higlighting rectangle")
#                     start_point = (x1, y1); end_point = (x2, y2); color = (0, 255, 0); thickness = 2
#                     cv2.rectangle(uncertain_image, start_point, end_point, color, thickness)
#         if(uncertain_rect_added):
#             uncertain_images.append((cv2_to_pil(uncertain_image), file_name))
#         blurred_images.append((cv2_to_pil(cv2_image), file_name))
#     return (blurred_images, uncertain_images)
