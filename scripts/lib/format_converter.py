import os
import json
import cv2
import numpy as np
import OpenEXR, Imath
import shutil

class EXRImage:
    def __init__(self, path):
        self.exr = OpenEXR.InputFile(path)
        self.header = self.exr.header()

        dw = self.header['dataWindow']
        self.h = dw.max.y - dw.min.y + 1
        self.w = dw.max.x - dw.min.x + 1

        self.channels = list(self.header['channels'].keys())

    def get_channel(self, channel_name, dtype=Imath.PixelType(Imath.PixelType.FLOAT)):
        if channel_name not in self.channels:
            raise ValueError(f"Channel {channel_name} not found in EXR file. Available channels: {self.channels}")
        raw = self.exr.channel(channel_name, dtype)
        return np.frombuffer(raw, dtype=np.float32).reshape((self.h, self.w))
    
    def list_channels(self):
        return self.channels
    
def mask_to_polygon(mask, normalize=True):
    img_h, img_w = mask.shape
    contours = mask_to_contours(mask)
    if len(contours) == 0:
        return np.zeros((0, 2), dtype=float)

    contour = max(contours, key=cv2.contourArea)
    polygon = contour.reshape(-1, 2).astype(float)
    if normalize:
        polygon[:, 0] /= img_w   # x
        polygon[:, 1] /= img_h   # y
    
    return polygon

def mask_to_bbox(mask):
    contours = mask_to_contours(mask)
    if len(contours) == 0:
        return None
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    return x, y, w, h

def mask_to_contours(mask):
    """Find contours robustly even when shapes touch image borders.

    When a filled region touches the border, `cv2.findContours` can produce contours
    that ride the image boundary, which may look like a contour spanning the whole
    image. Padding with a 1px black border prevents that; we then shift coordinates
    back to the original image space.
    """
    # if mask is None:
    #     return []

    # if mask.dtype != np.uint8:
    #     # findContours expects an 8-bit single-channel image.
    #     mask_u8 = mask.astype(np.uint8)
    # else:
    #     mask_u8 = mask
        
    # padded = cv2.copyMakeBorder(mask_u8, 1, 1, 1, 1, borderType=cv2.BORDER_CONSTANT, value=0)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # if not contours:
    #     return []

    # # Shift contour coordinates back by removing the padding offset.
    # shifted = []
    # for c in contours:
    #     c2 = c.copy()
    #     c2[:, 0, 0] -= 1
    #     c2[:, 0, 1] -= 1
    #     shifted.append(c2)

    return contours

class YoloExport:
    def __init__(self, dataset_dir, dest_dir, copy_images=False, img_ext=".png", exr_ext=".exr"):
        self.dataset_dir = dataset_dir
        self.dest_dir = dest_dir
        self.copy_images = copy_images
        self.img_ext = img_ext
        self.exr_ext = exr_ext

        # DATA
        self.annotations = {}
        self.has_color = False
        self.has_depth = False
        self.has_segmentation = False

        self.read_annotations()

    def read_annotations(self):
        splits = os.listdir(self.dataset_dir)
        anns_paths = {}

        for split in splits:
            if os.path.isdir(os.path.join(self.dataset_dir, split)):
                anns_path = os.path.join(self.dataset_dir, split, f'{split}_annotations.json')
                anns_paths[split] = anns_path
                try:
                    with open(anns_path, 'r') as f:
                        self.annotations[split] = json.load(f)
                except Exception as e:
                    print(f"Error reading annotations for split {split}: {e}, split will be ignored")

                subdirs = os.listdir(os.path.join(self.dataset_dir, split))
                if 'images' in subdirs:
                    self.has_color = True
                if 'depth' in subdirs:
                    self.has_depth = True
                if 'segmentation' in subdirs:
                    self.has_segmentation = True

    def create_split_dirs(self, split):
        dest_path = os.path.join(self.dest_dir)
        dest_imgs_path = os.path.join(dest_path, 'images', split)
        dest_labels_path = os.path.join(dest_path, 'labels', split)
        os.makedirs(dest_path, exist_ok=True)
        os.makedirs(dest_imgs_path, exist_ok=True)
        os.makedirs(dest_labels_path, exist_ok=True)

    def read_image(self, img_filename, split):
        if not img_filename.endswith(self.img_ext):
            img_filename = os.path.basename(img_filename) + self.img_ext

        assert self.has_color, "Cannot read color image, dataset has no 'images' directory"
        img_path = os.path.join(self.dataset_dir, split, 'images', img_filename)
        return cv2.imread(img_path)
    
    def read_depth(self, depth_filename, split):
        if not depth_filename.endswith(self.exr_ext):
            depth_filename = os.path.basename(depth_filename) + self.exr_ext

        depth_path = os.path.join(self.dataset_dir, split, 'depth', depth_filename)
        exr = EXRImage(depth_path)
        return exr.get_channel(exr.list_channels()[0])

    def read_segmentation(self, seg_filename, split):
        if not seg_filename.endswith(self.exr_ext):
            seg_filename = os.path.basename(seg_filename) + self.exr_ext

        assert self.has_segmentation, "Cannot read segmentation image, dataset has no 'segmentation' directory"
        seg_path = os.path.join(self.dataset_dir, split, 'segmentation', seg_filename)
        exr = EXRImage(seg_path)
        return exr.get_channel(exr.list_channels()[0])
    
    def get_segmentation_mask(self, seg_img, seg_id):
        return (seg_img == seg_id).astype(np.uint8) * 255

    def export_to_yolo_detection(self, use_segmentation_bboxes = False):
        for split, anns in self.annotations.items():
            self.create_split_dirs(split)

            for img_info in anns['images']:
                img_id = img_info['id']
                scene = anns["scenes"][img_id]
                file_basename = img_info['file_name']
                img_w, img_h = img_info['width'], img_info['height']
                label_txt = ""
                image_annotations = [ann for ann in anns['annotations'] if ann['image_id'] == img_id]
                for label in image_annotations:
                    obj_id = label['id']
                    obj_info = [obj for obj in scene["objects"] if obj['id'] == obj_id][0]
                    cat_id = label['category_id']

                    if use_segmentation_bboxes:
                        seg_img = self.read_segmentation(file_basename, split)
                        mask = self.get_segmentation_mask(seg_img, obj_info['segmentation_id'])
                        bbox = mask_to_bbox(mask)

                        if bbox is None:
                            continue

                        x, y, w, h = bbox
                    else:
                        x, y, w, h = label['bbox']

                    c_x, c_y = (2 * x + w) / 2, (2 * y + h) / 2

                    line = [0, c_x / img_w, c_y / img_h, w / img_w, h / img_h]
                    label_txt += (" ".join(map(str, line)) + "\n")

                with open(os.path.join(self.dest_dir, 'labels', split, f"{img_info['file_name'].split('.')[0]}.txt"), 'w') as f:
                    f.write(label_txt)

                if self.copy_images:
                    img_old_path = os.path.join(self.dataset_dir, split, 'images', file_basename + self.img_ext)
                    shutil.copy(img_old_path, os.path.join(self.dest_dir, 'images', split, file_basename + self.img_ext))

    def export_to_yolo_segmentation(self):
        for split, anns in self.annotations.items():
            self.create_split_dirs(split)

            basepath = os.path.join(self.dataset_dir, split)

            for img_info in anns['images']:
                img_id = img_info['id']
                scene = anns["scenes"][img_id]
                file_basename = img_info['file_name'].split('.')[0]

                label_txt = ""
                image_annotations = [ann for ann in anns['annotations'] if ann['image_id'] == img_id]
                for label in image_annotations:
                    obj_id = label['id']
                    obj_info = [obj for obj in scene["objects"] if obj['id'] == obj_id][0]
                    cat_id = label['category_id']

                    seg_img = self.read_segmentation(file_basename, split)
                    mask = self.get_segmentation_mask(seg_img, obj_info['segmentation_id'])
                    if np.sum(mask) == 0:
                        continue

                    polygon = mask_to_polygon(mask, normalize=True)
                    line = [cat_id]

                    for x, y in polygon:
                        line.extend([x, y])
                    
                    label_txt += (" ".join(map(str, line)) + "\n")

                with open(os.path.join(self.dest_dir, 'labels', split, f"{file_basename}.txt"), 'w') as f:
                    f.write(label_txt)

                if self.copy_images:
                    img_old_path = os.path.join(basepath, 'images', file_basename + self.img_ext)
                    shutil.copy(img_old_path, os.path.join(self.dest_dir, 'images', split, file_basename + self.img_ext))


