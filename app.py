import streamlit as st
import sqlite3
from PIL import Image, ImageDraw, ExifTags
from datetime import datetime
import cv2
import numpy as np
import os

# Database setup
DB_PATH = "tree_data.db"

def create_database():
    """Create the database tables for Trees and Images."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Trees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Trees (
        tree_id INTEGER PRIMARY KEY,
        species TEXT,
        height REAL,
        width REAL,
        crown_size REAL,
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

def detect_tree_and_validate(image_path):
    """Detect the tree and validate if the full tree is in the frame."""
    image = cv2.imread(image_path)
    height, width, _ = image.shape

    # Mock detection logic (replace with YOLO or similar model)
    bbox = [50, 50, width - 50, height - 50]  # Simulate bounding box in the center
    valid = bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= width and bbox[3] <= height

    # Draw bounding box and guidelines
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
    cv2.line(image, (width // 2, 0), (width // 2, height), (0, 255, 0), 1)  # Vertical
    cv2.line(image, (0, height // 2), (width, height // 2), (0, 255, 0), 1)  # Horizontal

    processed_image_path = image_path.replace(".jpg", "_processed.jpg")
    cv2.imwrite(processed_image_path, image)

    return valid, bbox, processed_image_path

def calculate_tree_dimensions(bbox, focal_length, img_width, img_height):
    """Calculate tree dimensions based on bounding box and image metadata."""
    sensor_width = 36.0  # mm (full-frame sensor width)
    distance_to_tree = 5000.0  # mm (arbitrary distance)

    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    tree_width = (bbox_width / img_width) * (sensor_width / focal_length) * distance_to_tree
    tree_height = (bbox_height / img_height) * (sensor_width / focal_length) * distance_to_tree
    crown_size = tree_width * 0.6  # Assume crown size is 60% of tree width

    return round(tree_height / 1000, 2), round(tree_width / 1000, 2), round(crown_size / 1000, 2)

def save_tree_to_database(species, height, width, crown_size, focal_length, image_path):
    """Save tree details to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Trees (species, height, width, crown_size, focal_length, image_path)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (species, height, width, crown_size, focal_length, image_path))
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

        # Detect tree and validate
        valid, bbox, processed_image_path = detect_tree_and_validate(img_path)
        if not valid:
            st.error("Invalid image: Ensure the entire tree is within the frame.")
            return

        st.image(processed_image_path, caption="Processed Image with Bounding Box and Guidelines")

        # Calculate tree dimensions
        image = Image.open(img_path)
        tree_height, tree_width, crown_size = calculate_tree_dimensions(bbox, focal_length, *image.size)

        st.write(f"**Tree Height:** {tree_height} meters")
        st.write(f"**Tree Width:** {tree_width} meters")
        st.write(f"**Crown Size:** {crown_size} meters")

        # Save tree details to database
        species = st.text_input("Enter tree species (optional):", value="Unknown Species")
        if st.button("Save to Database"):
            save_tree_to_database(species, tree_height, tree_width, crown_size, focal_length, processed_image_path)
            st.success("Tree data saved successfully!")

if __name__ == "__main__":
    main()
