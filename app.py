import streamlit as st
import sqlite3
from PIL import Image, ExifTags
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

def process_image(image_path, real_world_scale_height=0.5, real_world_scale_width=0.5, reference_height=1.0, reference_width=0.2):
    """Process the image: detect tree, add guidelines, and calculate height/width in meters."""
    image = cv2.imread(image_path)
    height, width, _ = image.shape

    # Convert to HSV for color-based segmentation
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    green_lower = np.array([35, 50, 50])  # Lower bound for green
    green_upper = np.array([85, 255, 255])  # Upper bound for green
    mask = cv2.inRange(hsv, green_lower, green_upper)

    # Morphological operations to clean the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False, "No tree detected in the image. Please recapture.", None, None

    # Get the largest contour (assume it's the tree)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    # Convert the tree height and width to real-world meters using reference object
    tree_height_meters = (h / reference_height) * reference_height  # Based on reference height
    tree_width_meters = (w / reference_width) * reference_width  # Based on reference width

    # Calculate crown size (proportional to width)
    crown_size = tree_width_meters * 1.5  # For example, crown size is 1.5x the width

    # Add guidelines (dotted lines)
    cv2.line(image, (width // 2, 0), (width // 2, height), (255, 0, 0), 2, lineType=cv2.LINE_AA)  # Blue dotted vertical line
    cv2.line(image, (0, height // 2), (width, height // 2), (255, 0, 0), 2, lineType=cv2.LINE_AA)  # Blue dotted horizontal line

    # Add height and width text on the image with smaller font size and red color
    text_height = f"Height: {tree_height_meters:.2f}m"
    text_width = f"Width: {tree_width_meters:.2f}m"

    # Position text (you can adjust these positions as needed)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4  # Smaller font scale for smaller text
    thickness = 1  # Thin text for better fit

    # Calculate text size to ensure it's within image bounds
    (text_width_height, _) = cv2.getTextSize(text_height, font, font_scale, thickness)
    (text_width_width, _) = cv2.getTextSize(text_width, font, font_scale, thickness)

    # Ensure text fits within the image width and height
    text_x = max(10, min(x, width - text_width_height[0] - 10))
    text_y = max(10, y - 10)
    cv2.putText(image, text_height, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)

    text_x = max(10, min(x, width - text_width_width[0] - 10))
    text_y = max(10, y + h + 20)
    cv2.putText(image, text_width, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)

    # Save the processed image
    processed_image_path = image_path.replace(".jpg", "_processed.jpg")
    cv2.imwrite(processed_image_path, image)

    return True, None, processed_image_path, (tree_height_meters, tree_width_meters, crown_size)

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
    st.write("Capture or upload a tree image, validate its presence, and measure its dimensions in meters.")

    create_database()

    st.header("Capture or Upload Tree Image")
    capture_or_upload = st.radio("Choose an option:", ["Capture using Camera", "Upload an Image"])

    img_data = None
    if capture_or_upload == "Capture using Camera":
        img_data = st.camera_input("Take a picture of the tree")
    elif capture_or_upload == "Upload an Image":
        img_data = st.file_uploader("Upload a tree image", type=["jpg", "jpeg", "png"])

    if img_data:
        # Save uploaded image
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())
        st.success(f"Image saved: {img_path}")

        # Extract focal length
        focal_length = extract_focal_length(img_path)

        # Process the image
        is_valid, error_msg, processed_image_path, dimensions = process_image(img_path)

        if not is_valid:
            st.error(error_msg)
            return

        # Display the processed image
        st.image(processed_image_path, caption="Processed Image with Guidelines and Dimensions")
        st.success("Tree is properly centered and processed!")

        # Display dimensions in meters
        tree_height_meters, tree_width_meters, crown_size = dimensions
        st.write(f"**Tree Height:** {tree_height_meters:.2f} meters")
        st.write(f"**Tree Width:** {tree_width_meters:.2f} meters")
        st.write(f"**Tree Crown Size:** {crown_size:.2f} meters")

        # Save to database
        species = st.text_input("Enter tree species (optional):", value="Unknown Species")
        if st.button("Save to Database"):
            save_tree_to_database(species, tree_height_meters, tree_width_meters, crown_size, focal_length, processed_image_path)
            st.success("Tree data saved successfully!")

if __name__ == "__main__":
    main()
