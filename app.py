import streamlit as st
import sqlite3
from PIL import Image, ImageDraw
from datetime import datetime
import requests
import wikipedia
import cv2
import numpy as np
import os
import exifread

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

def extract_metadata(image_path):
    """Extract focal length and sensor width from image metadata."""
    focal_length = 50.0  # Default value if metadata is unavailable
    sensor_width = 36.0  # Default value for full-frame cameras

    try:
        with open(image_path, 'rb') as img_file:
            tags = exifread.process_file(img_file, details=False)
            focal_length_tag = tags.get('EXIF FocalLength')
            if focal_length_tag:
                focal_length = float(focal_length_tag.values[0])
    except Exception as e:
        st.warning(f"Could not extract metadata: {e}")

    return focal_length, sensor_width

def calculate_tree_dimensions(bbox, focal_length, img_width, img_height):
    """Calculate tree dimensions based on bounding box and image metadata."""
    sensor_width = 36.0  # mm (standard full-frame sensor width)
    distance_to_tree = 5000.0  # mm (arbitrary distance to the tree)

    if focal_length == 0:  # Prevent division by zero
        focal_length = 1.0

    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    tree_width = (bbox_width / img_width) * (sensor_width / focal_length) * distance_to_tree
    tree_height = (bbox_height / img_height) * (sensor_width / focal_length) * distance_to_tree
    crown_size = tree_width * 0.6  # Assume crown size is 60% of tree width

    return round(tree_height / 1000, 2), round(tree_width / 1000, 2), round(crown_size / 1000, 2)

def detect_tree_and_draw_bbox(image_path):
    """Detect the tree in the image and draw a bounding box based on color segmentation."""
    # Load image using OpenCV
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Convert to HSV color space
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Define range for green color (common for trees)
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])

    # Create mask for green regions
    mask = cv2.inRange(hsv_image, lower_green, upper_green)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Get the largest contour (assuming it's the tree)
        largest_contour = max(contours, key=cv2.contourArea)

        # Get bounding box for the largest contour
        x, y, w, h = cv2.boundingRect(largest_contour)

        # Draw bounding box on original image
        cv2.rectangle(image_rgb, (x, y), (x + w, y + h), (255, 0, 0), 3)

        # Save the output image with bounding box
        output_path = image_path.replace(".jpg", "_bbox.jpg")
        Image.fromarray(image_rgb).save(output_path)

        return (x, y, x + w, y + h), output_path
    else:
        st.error("No tree detected in the image.")
        return None, None

def add_image(image_data):
    """Add image details to the Images table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Images (collection_date, focal_length, height, width, file_path, bounding_box)
    VALUES (?, ?, ?, ?, ?, ?)
    """, image_data)
    conn.commit()
    conn.close()

def get_wikipedia_details(tree_name):
    """Fetch details of the tree from Wikipedia."""
    try:
        tree_name_query = f"{tree_name} tree"
        summary = wikipedia.summary(tree_name_query, sentences=3)
        link = wikipedia.page(tree_name_query).url
        return summary, link
    except wikipedia.exceptions.DisambiguationError as e:
        st.error(f"Disambiguation error: {e}")
        return None, None
    except wikipedia.exceptions.PageError:
        st.error(f"Page for '{tree_name}' not found.")
        return None, None

def main():
    st.title("Real Forestry Project")
    st.write("Capture tree data and save it to the database.")

    create_database()

    # Step 1: Capture or upload an image
    st.header("Capture or Upload Tree Image")
    img_data = st.camera_input("Take a picture of the tree") or st.file_uploader("Or upload an image", type=["jpg", "png", "jpeg"])

    if img_data:
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())
        st.success(f"Image saved: {img_path}")

        # Extract metadata
        focal_length, sensor_width = extract_metadata(img_path)

        # Detect tree and draw bounding box
        bounding_box, bbox_img_path = detect_tree_and_draw_bbox(img_path)
        if bounding_box:
            st.image(bbox_img_path, caption="Tree with Bounding Box")

            # Calculate tree dimensions
            image = Image.open(img_path)
            resolution = image.size

            tree_height, tree_width, crown_size = calculate_tree_dimensions(bounding_box, focal_length, *resolution)
            st.write("### Calculated Tree Dimensions")
            st.write(f"Height: {tree_height} m")
            st.write(f"Width: {tree_width} m")
            st.write(f"Crown Size: {crown_size} m²")

            # Save to database
            image_data = (
                datetime.now().strftime("%Y-%m-%d"),
                focal_length,
                resolution[1],
                resolution[0],
                img_path,
                str(bounding_box)
            )
            add_image(image_data)
            st.success("Image metadata and bounding box saved to the database.")

if __name__ == "__main__":
    main()
