def generate_image(image_description, output_filename):
    """
    Simulate image generation.
    Replace this function with your actual image generator API call.
    For now, we create a simple image using Pillow that contains the description.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Please install Pillow: pip install Pillow")
        sys.exit(1)

    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()

    text = f"Image for: {image_description}"
    draw.text((10, 10), text, fill=(0, 0, 0), font=font)
    img.save(output_filename)
    print(f"Generated image saved to {output_filename}")
    return output_filename
