from src.utils import DataLoader


loader = DataLoader(
    video_dir="assets/coloscopie_2021-06-17_10-09-32_Ludwig__1__all",
    labels=["Polyp", "Shaft", "Wire"]
)

print(loader.masks.keys())