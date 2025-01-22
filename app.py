import streamlit as st
import sqlite3
from PIL import Image, ImageDraw
from datetime import datetime
import os
import numpy as np

# Database setup
DB_PATH = "real_forestry_project.db"

def create_database():
    """Create the database tables for Trees and Images."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Trees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Trees (
        tree_id INTEGER PRIMARY KEY,
        species TEXT,
        year_of_plantation INTEGER,
        location TEXT,
        height REAL,
        width REAL,
        crown_size REAL,
        stem_bark_code TEXT UNIQUE,
        images TEXT,
        wikipedia_link TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create Images table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Images (
        image_id INTEGER PRIMARY KEY,
        collection_date DATE,
        focal_length REAL,
        height INTEGER,
        width INTEGER,
        file_path TEXT UNIQUE,
        bounding_box TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def draw_guidelines(image_path):
    """Draw vertical and horizontal guidelines on the image."""
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Draw vertical and horizontal center lines
    draw.line([(width // 2, 0), (width // 2, height)], fill="green", width=2)  # Vertical
    draw.line([(0, height // 2), (width, height // 2)], fill="green", width=2)  # Horizontal

    guideline_path = image_path.replace(".jpg", "_guidelines.jpg")
    image.save(guideline_path)
    return guideline_path

def detect_tree_and_validate(image_path):
    """Detect the tree and validate if the full tree is in the frame."""
    # Mock detection: Replace this with an actual detection algorithm
    bbox = [50, 50, 450, 800]  # Mocked bounding box

    image = Image.open(image_path)
    width, height = image.size

    # Check if the tree is fully captured
    if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= width or bbox[3] >= height:
        return False, bbox  # Tree is not fully within the frame

    # Draw bounding box on the image
    draw = ImageDraw.Draw(image)
    draw.rectangle(bbox, outline="red", width=3)
    bbox_img_path = image_path.replace(".jpg", "_bbox.jpg")
    image.save(bbox_img_path)

    return True, (bbox, bbox_img_path)

def calculate_tree_dimensions(bbox, focal_length, img_width, img_height):
    """Calculate tree dimensions based on bounding box and image metadata."""
    sensor_width = 36.0  # mm (standard full-frame sensor width)
    distance_to_tree = 5000.0  # mm (arbitrary distance to the tree)

    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    tree_width = (bbox_width / img_width) * (sensor_width / focal_length) * distance_to_tree
    tree_height = (bbox_height / img_height) * (sensor_width / focal_length) * distance_to_tree
    crown_size = tree_width * 0.6  # Assume crown size is 60% of tree width

    return round(tree_height / 1000, 2), round(tree_width / 1000, 2), round(crown_size / 1000, 2)

def main():
    st.title("Tree Detection and Measurement")
    st.write("Ensure the tree is fully captured with the help of guidelines.")

    create_database()

    st.header("Capture or Upload Tree Image")
    img_data = st.camera_input("Take a picture of the tree") or st.file_uploader("Or upload an image", type=["jpg", "png", "jpeg"])

    if img_data:
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())
        st.success(f"Image saved: {img_path}")

        # Draw guidelines
        guideline_img_path = draw_guidelines(img_path)
        st.image(guideline_img_path, caption="Image with Guidelines")

        # Detect tree and validate
        valid, detection_data = detect_tree_and_validate(img_path)
        if not valid:
            st.error("Invalid image: Ensure the entire tree is within the frame.")
            return

        bbox, bbox_img_path = detection_data
        st.image(bbox_img_path, caption="Tree with Bounding Box")

        # Calculate dimensions
        image = Image.open(img_path)
        focal_length = 50.0
        tree_height, tree_width, crown_size = calculate_tree_dimensions(bbox, focal_length, *image.size)
        st.write(f"Tree Height: {tree_height} meters")
        st.write(f"Tree Width: {tree_width} meters")
        st.write(f"Crown Size: {crown_size} meters")

if __name__ == "__main__":
    main()
