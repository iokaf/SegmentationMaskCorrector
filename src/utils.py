from collections import defaultdict
from pathlib import Path

# Import dataclasses

import cv2

from dataclasses import dataclass, field
from typing import Dict, List, Any

import pandas as pd

@dataclass
class ImageMasks:
    labels: List[str]
    image_index: int = None
    save_name: Any = None
    masks: Dict[str, Any] = field(init=False)

    def __post_init__(self):
        if not self.labels:
            raise ValueError("labels list must be non-empty")
        # Initialize all labels with None
        self.masks = {label: None for label in self.labels}

    def set_index(self, image_index: int):
        self.image_index = image_index

    def set(self, mask: Any, label: str):
        if label not in self.masks:
            return
        self.masks[label] = mask

    def get(self, label: str):
        return self.masks.get(label, None)

    def get_index(self):
        return self.image_index

    def get_all(self) -> Dict[str, Any]:
        """Returns all label-mask pairs."""
        return self.masks

    def set_save_name(self, save_name: str):
        self.save_name = save_name

    def get_save_name(self):
        return self.save_name


class DataLoader:
    def __init__(self, labels: list):
        assert len(labels) > 0, "Labels list cannot be empty."

        self.masks = defaultdict(lambda: ImageMasks(labels=labels))
        self.labels = labels
        self.max_index = None
        self.output_dir_name = None

    def set_output_dir_name(self, dir_name: str):
        self.output_dir_name = dir_name

    def get_output_dir_name(self):
        return self.output_dir_name

    # Define the load_data and get_datapoint methods to be overridden by subclasses
    def set_max_index(self, max_index: int):
        if max_index <= 0:
            raise ValueError("max_index must be a positive integer.")
        self.max_index = max_index

    def get_max_index(self):
        return self.max_index
    
    def load_data(self):
        raise NotImplementedError("Subclasses should implement this method.")
    
    def get_datapoint(self, index: int):
        raise NotImplementedError("Subclasses should implement this method.")


    def delete_mask(self, index: int, label: str):
        if index < 0 or index >= self.max_index:
            raise ValueError(f"Index {index} is out of range.")

        mask = self.masks.get(index, ImageMasks(labels=self.labels))
        mask.set(mask=None, label=label)
        self.masks[index] = mask


    def get_masks(self, index: int):
        if index < 0 or index >= self.max_index:
            raise ValueError(f"Index {index} is out of range.")

        mask = self.masks.get(index, ImageMasks(labels=self.labels))
        return mask

    def set_frame_masks(self, index: int, mask: ImageMasks):
        if index < 0 or index >= self.max_index:
            raise ValueError(f"Index {index} is out of range.")

        self.masks[index] = mask

    def save_all_masks(self, folder: str):
        if not Path(folder).exists():
            raise ValueError(f"Directory {folder} does not exist.")
        if not Path(folder).is_dir():
            raise ValueError(f"{folder} is not a directory.")
        for index, mask in self.masks.items():
            for label in self.labels:
                mask_img = mask.get(label)
                if mask_img is not None:
                    filename = f"{mask.get_save_name()}__{label}.png"
                    cv2.imwrite(str(Path(folder) / filename), mask_img)


class VideoDataLoader(DataLoader):
    def __init__(self, video_dir: str, labels: list):
        assert Path(video_dir).exists(), f"Directory {video_dir} does not exist."
        assert Path(video_dir).is_dir(), f"{video_dir} is not a directory."
        assert len(labels) > 0, "Labels list cannot be empty."

        self.video_dir = Path(video_dir)

        self.video_path = None
        self.video = None
        self.max_index = None
        self.masks = defaultdict(lambda: ImageMasks(labels=labels))
        self.data = self.load_data()
        self.labels = labels

    def load_data(self):
        video_name = self.video_dir.stem
        self.video_path = self.video_dir / f"{video_name}.mp4"

        self.set_output_dir_name(video_name)

        self.video = cv2.VideoCapture(str(self.video_path))
        if not self.video.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")
        
        # Get the number of frames in the video
        self.set_max_index(int(self.video.get(cv2.CAP_PROP_FRAME_COUNT)))

        masks_dir = self.video_dir / video_name / "masks"
        masks = masks_dir.glob("*.png")

        for mask in masks:
            mask_name = mask.stem
            
            fnum, label = mask_name.split("__")
            fnum = int(fnum)
            
            mask = cv2.imread(str(mask), cv2.IMREAD_GRAYSCALE)

            self.masks[fnum].set(
                mask=mask, 
                label=label
                )
            
            self.masks[fnum].set_index(fnum)
            self.masks[fnum].set_save_name(f"{fnum:07d}")

    def get_datapoint(self, frame_number: int):
        if frame_number < 0 or frame_number >= self.max_index:
            raise ValueError(f"Frame number {frame_number} is out of range.")
        
        self.video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.video.read()
        if not ret:
            raise ValueError(f"Could not read frame {frame_number} from video.")
        
        return frame
    

class ImageDataLoader(DataLoader):
    def __init__(self, annotations_file: str, labels: list):
        assert Path(annotations_file).exists(), f"File {annotations_file} does not exist."
        assert Path(annotations_file).is_file(), f"{annotations_file} is not a file."
        assert len(labels) > 0, "Labels list cannot be empty."

        self.annotations_file = Path(annotations_file)
        self.labels = labels
        self.masks = defaultdict(lambda: ImageMasks(labels=labels))


        self.data = self.load_data()
        self.max_index = len(self.data)

    def load_data(self):

        self.set_output_dir_name(self.annotations_file.stem)
        
        df = pd.read_csv(self.annotations_file)

        for idx, row in df.iterrows():
            image_path = row['image']
            image_name = Path(image_path).stem
            for label in self.labels:
                if not label in row or pd.isna(row[label]):
                    continue

                mask_path = row[label]
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
                self.masks[idx].set(
                    mask=mask, 
                    label=label
                        )
                
            self.masks[idx].set_index(idx)
            self.masks[idx].set_save_name(image_name)
                
        return df

    def get_datapoint(self, index: int):
        if index < 0 or index >= self.max_index:
            raise ValueError(f"Index {index} is out of range.")

        row = self.data.iloc[index]
        image_path = row['image']
        if not Path(image_path).exists():
            raise ValueError(f"Image file {image_path} does not exist.")
        if not Path(image_path).is_file():
            raise ValueError(f"{image_path} is not a file.")
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image file {image_path}.")

        return image