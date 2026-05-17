from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class ImageComposer:
    @staticmethod
    def compose_scene_panorama(angle_images: dict[str, str], scene_name: str, output_path: str):
        """
        Compose 4 scene angle images into a 2x2 panorama.
        angle_images keys: "正视图", "左45度", "右45度", "鸟瞰图"
        """
        order = ["正视图", "左45度", "右45度", "鸟瞰图"]
        labels = ["正面", "左侧45°", "右侧45°", "俯视"]

        images = []
        for key in order:
            if key in angle_images:
                img = Image.open(angle_images[key]).convert("RGB")
                img = img.resize((1024, 1024))
                images.append(img)
            else:
                images.append(Image.new("RGB", (1024, 1024), (240, 240, 240)))

        canvas = Image.new("RGB", (2048, 2048), (255, 255, 255))
        positions = [(0, 0), (1024, 0), (0, 1024), (1024, 1024)]
        label_positions = [(10, 10), (1034, 10), (10, 1034), (1034, 1034)]

        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()

        for img, pos, label, lpos in zip(images, positions, labels, label_positions):
            canvas.paste(img, pos)
            draw.text(lpos, label, fill=(255, 255, 255), font=font)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, quality=95)

    @staticmethod
    def download_image(url: str, save_path: str):
        import requests
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(resp.content)
