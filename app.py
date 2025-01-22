import cv2
import numpy as np
import os
from PIL import Image, ExifTags
from datetime import datetime
import sqlite3
import streamlit as st

# Database setup
DB_PATH = "tree_data.db"

def create_database():
    """Create the database tables for Trees and Images."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Trees (
        tree_id INTEGER PRIMARY KEY,
        species TEXT,
        height REAL,
        width REAL,
        focal_length REAL,
        image_path TEXT UNIQUE,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def extract_focal_length(image_path):
    """Extract focal length from the image's EXIF data."""
    try:
        image = Image.open(image_path)
        exif = {ExifTags.TAGS[k]: v for k, v in image._getexif().items() if k in ExifTags.TAGS}
        focal_length = exif.get("FocalLength", 50)  # Default to 50mm if not available
        return focal_length if isinstance(focal_length, float) else focal_length[0] / focal_length[1]
    except Exception:
        return 50.0  # Default focal length if EXIF data is unavailable

def validate_tree_centering(bbox, img_width, img_height):
    """Validate if the tree is centered with space around the edges."""
    x_min, y_min, x_max, y_max = bbox
    space_threshold = 0.1  # At least 10% space on all sides
    left_space = x_min / img_width
    right_space = (img_width - x_max) / img_width
    top_space = y_min / img_height
    bottom_space = (img_height - y_max) / img_height

    return all(space >= space_threshold for space in [left_space, right_space, top_space, bottom_space])

def process_image_with_validation(image_path):
    """Process the image in the backend: validate centering and process."""
    image = cv2.imread(image_path)
    height, width, _ = image.shape

    # Mock detection logic (replace with real detection logic using YOLO or similar)
    bbox = [int(width * 0.2), int(height * 0.1), int(width * 0.8), int(height * 0.9)]  # Mocked bounding box

    # Validate centering
    is_centered = validate_tree_centering(bbox, width, height)
    if not is_centered:
        return False, "Tree is not centered or lacks space on all sides. Please recapture.", None

    # Blur the background
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(mask, (bbox[0], bbox[1]), (bbox[2], bbox[3]), 255, -1)
    blurred = cv2.GaussianBlur(image, (51, 51), 30)
    image = np.where(mask[:, :, None] == 255, image, blurred)

    # Annotate dimensions
    tree_width = (bbox[2] - bbox[0]) / width * 100
    tree_height = (bbox[3] - bbox[1]) / height * 100
    cv2.putText(image, f"Height: {tree_height:.2f}% of image", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(image, f"Width: {tree_width:.2f}% of image", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Draw guidelines
    cv2.line(image, (width // 2, 0), (width // 2, height), (0, 255, 0), 2)  # Vertical
    cv2.line(image, (0, height // 2), (width, height // 2), (0, 255, 0), 2)  # Horizontal

    # Save processed image
    processed_image_path = image_path.replace(".jpg", "_processed.jpg")
    cv2.imwrite(processed_image_path, image)

    return True, None, processed_image_path

def save_tree_to_database(species, height, width, focal_length, image_path):
    """Save tree details to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Trees (species, height, width, focal_length, image_path)
    VALUES (?, ?, ?, ?, ?)
    """, (species, height, width, focal_length, image_path))
    conn.commit()
    conn.close()

def main():
    st.title("Tree Capture and Measurement")
    st.write("Capture a tree image, validate its presence, and measure its dimensions.")

    create_database()

    st.header("Capture or Upload Tree Image")
    img_data = st.camera_input("Take a picture of the tree")

    if img_data:
        # Save uploaded image
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())
        st.success(f"Image saved: {img_path}")

        # Extract focal length
        focal_length = extract_focal_length(img_path)

        # Process image and validate
        is_valid, error_msg, processed_image_path = process_image_with_validation(img_path)

        if not is_valid:
            st.error(error_msg)
            return

        # Display the processed image
        st.image(processed_image_path, caption="Processed Image with Dimensions and Guidelines")
        st.success("Tree is properly centered and processed!")

        # Save to database
        species = st.text_input("Enter tree species (optional):", value="Unknown Species")
        if st.button("Save to Database"):
            tree_width, tree_height = 50, 80  # Mocked values; replace with actual tree dimensions
            save_tree_to_database(species, tree_height, tree_width, focal_length, processed_image_path)
            st.success("Tree data saved successfully!")

if __name__ == "__main__":
    main()
