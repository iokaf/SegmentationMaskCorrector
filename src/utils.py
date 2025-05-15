from collections import defaultdict
from pathlib import Path

# Import dataclasses
from dataclasses import dataclass

import cv2


@dataclass
class FrameMasks:
    frame_number: int = None
    polyp: str = None
    shaft: str = None
    wire: str = None

    def set_fnum(self, frame_number):
        self.frame_number = frame_number

    def set(self, mask, label):
        
        if label == "Polyp":
            self.polyp = mask
        elif label == "Shaft":
            self.shaft = mask
        elif label == "Wire":
            self.wire = mask
        else:
            raise ValueError(f"Unknown label: {label}")
    
    def get(self, key):
        return {
            "Polyp": self.polyp,
            "Shaft": self.shaft,
            "Wire": self.wire
        }.get(key, None)

    def get_fnum(self): 
        return self.frame_number
    
    def get_polyp(self):
        return self.polyp
    
    def get_shaft(self):
        return self.shaft
    
    def get_wire(self):
        return self.wire
    

class DataLoader:
    def __init__(self, video_dir: str, labels: list):
        assert Path(video_dir).exists(), f"Directory {video_dir} does not exist."
        assert Path(video_dir).is_dir(), f"{video_dir} is not a directory."
        assert len(labels) > 0, "Labels list cannot be empty."

        self.video_dir = Path(video_dir)

        self.video_path = None
        self.video = None
        self.frame_count = None
        self.masks = defaultdict(lambda: FrameMasks())
        self.data = self.load_data()
        self.labels = labels

    def load_data(self):
        video_name = self.video_dir.stem
        self.video_path = self.video_dir / f"{video_name}.mp4"

        self.video = cv2.VideoCapture(str(self.video_path))
        if not self.video.isOpened():
            raise ValueError(f"Could not open video file: {self.video_path}")
        
        # Get the number of frames in the video
        self.frame_count = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))

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


    def get_frame(self, frame_number: int):
        if frame_number < 0 or frame_number >= self.frame_count:
            raise ValueError(f"Frame number {frame_number} is out of range.")
        
        self.video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.video.read()
        if not ret:
            raise ValueError(f"Could not read frame {frame_number} from video.")
        
        return frame
    
    def get_masks(self, frame_number: int):
        if frame_number < 0 or frame_number >= self.frame_count:
            raise ValueError(f"Frame number {frame_number} is out of range.")
        
        mask = self.masks.get(frame_number, FrameMasks())
        return mask
    
    def set_frame_masks(self, frame_number: int, mask: FrameMasks):
        if frame_number < 0 or frame_number >= self.frame_count:
            raise ValueError(f"Frame number {frame_number} is out of range.")
        
        self.masks[frame_number] = mask


    def save_all_masks(self, folder: str):
        if not Path(folder).exists():
            raise ValueError(f"Directory {folder} does not exist.")
        
        for frame_number, mask in self.masks.items():
            for label in self.labels:
                mask_img = mask.get(label)
                if mask_img is not None:
                    print(frame_number, label)
                    filename = f"{frame_number:07d}__{label}.png"
                    cv2.imwrite(str(Path(folder) / filename), mask_img)