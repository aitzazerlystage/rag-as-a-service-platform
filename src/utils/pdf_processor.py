"""
PDF Processing utilities for text extraction, image processing, and vector database creation
"""

import os
import base64
import fitz  # PyMuPDF
import pdfplumber
# from langchain_openai import ChatOpenAI
from config.llm_factory import create_chat_llm
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from config.chunking_embeddings import get_chunking_embeddings
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import asyncio
import aiofiles
from pathlib import Path
import json
from typing import List, Dict, Tuple, Optional
import numpy as np

# Import configuration
from config.settings import (
    OPENAI_API_KEY,
    OUTPUT_DIR,
    VECTOR_DB_DIR,
    IMG_DIR,
    MAX_CONCURRENT_PDFS,
    MAX_IMAGE_WORKERS,
    LLM_MAX_TOKENS
)

# OCR Configuration
USE_OCR_FOR_IMAGE_FILTERING = True  # Set to False to disable OCR and use fallback method
OCR_MIN_TEXT_LENGTH = 3  # Minimum characters of text to consider meaningful
OCR_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence score (0.0-1.0)

# Import vector database interface
from .vector_db_interface import get_vector_database
from config.settings import get_vector_db_type, get_pinecone_api_key, get_pinecone_environment, get_pinecone_index_name

# -------- SETUP LOCAL OLLAMA LLM --------
# llm = ChatOpenAI(
#     model="gpt-4o",
#     temperature=0.2,
#     max_tokens=LLM_MAX_TOKENS,
#     api_key=OPENAI_API_KEY,
# )
llm = create_chat_llm(max_tokens=LLM_MAX_TOKENS)

# Setup embeddings for vector database (default provider from settings, e.g. Cohere)
embeddings = get_chunking_embeddings()

# Setup text splitter for chunking
# OLD APPROACH: Recursive splitting
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=1000,
#     chunk_overlap=200,
#     length_function=len,
# )

# NEW APPROACH: Semantic chunking - splits based on semantic similarity
from langchain_experimental.text_splitter import SemanticChunker
text_splitter = SemanticChunker(
    embeddings=embeddings,
    buffer_size=1,  # Number of sentences to combine
    add_start_index=True
)


# -------- STEP 1: Extract Text & Tables --------
def extract_text_tables(file_path):
    """Extract text and tables from PDF using pdfplumber"""
    all_text = ""
    all_tables = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                
                # Ensure text is a string
                if text is None:
                    text = ""
                text = str(text)
                
                all_text += f"\n--- Page {page_num + 1} ---\n{text}"
                
                # Fix: properly handle table extraction
                for table in tables:
                    if table and len(table) > 0:  # Check if table has content
                        # Ensure table data is valid
                        valid_table = []
                        for row in table:
                            if row and isinstance(row, list):
                                valid_row = [str(cell) if cell is not None else "" for cell in row]
                                valid_table.append(valid_row)
                        
                        if valid_table:
                            all_tables.append((page_num + 1, valid_table))
    except Exception as e:
        print(f"Error extracting text and tables from {file_path}: {e}")
        all_text = f"Error extracting content: {str(e)}"
        all_tables = []
    
    # Ensure we always return valid data
    if all_text is None:
        all_text = ""
    if all_tables is None:
        all_tables = []
        
    return all_text, all_tables

# -------- STEP 2: Extract Images --------
def extract_images(file_path, output_folder="images"):
    """Extract images from PDF using PyMuPDF"""
    image_paths = []
    
    try:
        os.makedirs(output_folder, exist_ok=True)
        doc = fitz.open(file_path)
        
        for page_index in range(len(doc)):
            for img_index, img in enumerate(doc[page_index].get_images(full=True)):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    # Always convert to RGB if not already
                    if pix.colorspace is not None and pix.colorspace.n != 3:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    img_path = os.path.join(output_folder, f"page{page_index + 1}_img{img_index + 1}.png")
                    pix.save(img_path)
                    image_paths.append({"page": page_index + 1, "path": img_path})
                    
                    pix = None  # Free memory
                except Exception as e:
                    print(f"Error processing image {img_index} on page {page_index + 1}: {e}")
                    continue

        doc.close()
    except Exception as e:
        print(f"Error extracting images from {file_path}: {e}")
        image_paths = []
    
    # Ensure we always return a list
    if image_paths is None:
        image_paths = []
        
    return image_paths 

# -------- IMAGE FILTERING SYSTEM --------
def detect_text_in_image(image_path, min_text_length=3, confidence_threshold=0.6):
    """
    Use OCR to detect if an image contains textual data.
    
    Args:
        image_path: Path to the image file
        min_text_length: Minimum length of detected text to consider meaningful
        confidence_threshold: Minimum confidence score for text detection
    
    Returns:
        tuple: (has_text: bool, detected_text: str, confidence: float)
    """
    try:
        import pytesseract
        from PIL import Image
        
        # Open and preprocess image for better OCR
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image dimensions
            width, height = img.size
            
            # Skip very small images (likely decorative)
            if width < 30 or height < 30:
                return False, "", 0.0
            
            # Use Tesseract OCR to detect text
            # Configure Tesseract for better text detection
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}"\'@#$%^&*+-=<>/\\|`~_'
            
            # Get detailed OCR data including confidence scores
            ocr_data = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Extract text and confidence scores
            detected_text = ""
            confidences = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                if text and conf > 0:  # Valid text with confidence > 0
                    detected_text += text + " "
                    confidences.append(conf)
            
            detected_text = detected_text.strip()
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Check if we have meaningful text
            has_text = (
                len(detected_text) >= min_text_length and 
                avg_confidence >= confidence_threshold * 100  # Tesseract uses 0-100 scale
            )
            
            if has_text:
                print(f"📝 Text detected: '{detected_text[:50]}{'...' if len(detected_text) > 50 else ''}' (confidence: {avg_confidence:.1f}%)")
            else:
                print(f"🔍 No meaningful text detected (length: {len(detected_text)}, confidence: {avg_confidence:.1f}%)")
            
            return has_text, detected_text, avg_confidence
            
    except ImportError:
        print("⚠️ pytesseract not available, falling back to basic image analysis")
        return _fallback_text_detection(image_path)
    except Exception as e:
        print(f"⚠️ Error in OCR text detection for {image_path}: {e}")
        return _fallback_text_detection(image_path)

def _fallback_text_detection(image_path, min_size=(50, 50), max_solid_color_ratio=0.95):
    """
    Fallback text detection using basic image analysis when OCR is not available.
    
    Args:
        image_path: Path to the image file
        min_size: Minimum dimensions (width, height) for meaningful images
        max_solid_color_ratio: Maximum ratio of solid color pixels
    
    Returns:
        tuple: (has_text: bool, detected_text: str, confidence: float)
    """
    try:
        from PIL import Image
        import numpy as np
        
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Check minimum size - filter out tiny decorative elements
            if width < min_size[0] or height < min_size[1]:
                print(f"🔍 Filtered out small image: {width}x{height} (too small)")
                return False, "", 0.0
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array for analysis
            img_array = np.array(img)
            
            # Check for solid color images (decorative elements)
            pixels = img_array.reshape(-1, 3)
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            most_common_count = np.max(counts)
            total_pixels = len(pixels)
            solid_color_ratio = most_common_count / total_pixels
            
            if solid_color_ratio > max_solid_color_ratio:
                print(f"🔍 Filtered out solid color image: {solid_color_ratio:.2f} ratio (decorative)")
                return False, "", 0.0
            
            # Check for very low contrast (mostly white/light backgrounds)
            gray_img = img.convert('L')
            gray_array = np.array(gray_img)
            contrast = np.std(gray_array)
            
            if contrast < 10:  # Very low contrast threshold
                print(f"🔍 Filtered out low contrast image: {contrast:.2f} std (likely blank/decorative)")
                return False, "", 0.0
            
            # Check for images that are mostly white/light (common for decorative elements)
            mean_brightness = np.mean(gray_array)
            if mean_brightness > 240:  # Very bright images
                print(f"🔍 Filtered out very bright image: {mean_brightness:.2f} brightness (likely decorative)")
                return False, "", 0.0
            
            # Look for text-like patterns using edge detection
            from PIL import ImageFilter
            edges = gray_img.filter(ImageFilter.FIND_EDGES)
            edge_array = np.array(edges)
            edge_density = np.sum(edge_array > 50) / total_pixels
            
            if edge_density < 0.01:  # Very few edges
                print(f"🔍 Filtered out low edge density image: {edge_density:.4f} (likely solid/decorative)")
                return False, "", 0.0
            
            # Estimate confidence based on edge density and contrast
            confidence = min(100, (edge_density * 1000 + contrast) * 2)
            
            print(f"✅ Image passed fallback filtering: {width}x{height}, contrast={contrast:.2f}, edges={edge_density:.4f} (confidence: {confidence:.1f}%)")
            return True, f"[Image with {width}x{height} dimensions, {edge_density:.4f} edge density]", confidence
            
    except Exception as e:
        print(f"⚠️ Error in fallback text detection for {image_path}: {e}")
        return False, "", 0.0

def is_image_informational(image_path, min_size=(50, 50), max_solid_color_ratio=0.95, use_ocr=True):
    """
    Analyze an image to determine if it contains meaningful textual content.
    
    Args:
        image_path: Path to the image file
        min_size: Minimum dimensions (width, height) for meaningful images
        max_solid_color_ratio: Maximum ratio of solid color pixels (for detecting decorative elements)
        use_ocr: Whether to use OCR for text detection (True) or fallback to basic analysis (False)
    
    Returns:
        bool: True if image contains meaningful content, False otherwise
    """
    if use_ocr:
        has_text, detected_text, confidence = detect_text_in_image(image_path)
        return has_text
    else:
        has_text, detected_text, confidence = _fallback_text_detection(image_path, min_size, max_solid_color_ratio)
        return has_text

def filter_informational_images(image_paths, min_size=(50, 50), max_solid_color_ratio=0.95, use_ocr=True, min_text_length=3, confidence_threshold=0.6):
    """
    Filter out non-informational images from a list of image paths using OCR text detection.
    
    Args:
        image_paths: List of image dictionaries with 'path' and 'page' keys
        min_size: Minimum dimensions for meaningful images
        max_solid_color_ratio: Maximum ratio of solid color pixels
        use_ocr: Whether to use OCR for text detection (True) or fallback to basic analysis (False)
        min_text_length: Minimum length of detected text to consider meaningful
        confidence_threshold: Minimum confidence score for text detection
    
    Returns:
        List of filtered image dictionaries with text content
    """
    if not image_paths:
        return []
    
    print(f"🔍 Filtering {len(image_paths)} extracted images for textual content...")
    if use_ocr:
        print(f"📝 Using OCR text detection (min_text_length={min_text_length}, confidence_threshold={confidence_threshold})")
    else:
        print(f"🔍 Using fallback image analysis")
    
    filtered_images = []
    filtered_count = 0
    text_detection_results = []
    
    for img in image_paths:
        if not isinstance(img, dict) or 'path' not in img:
            continue
            
        image_path = img['path']
        
        # Use OCR-based text detection
        if use_ocr:
            has_text, detected_text, confidence = detect_text_in_image(image_path, min_text_length, confidence_threshold)
        else:
            has_text, detected_text, confidence = _fallback_text_detection(image_path, min_size, max_solid_color_ratio)
        
        if has_text:
            # Add detected text information to the image metadata
            img_with_text = img.copy()
            img_with_text['detected_text'] = detected_text
            img_with_text['text_confidence'] = confidence
            filtered_images.append(img_with_text)
            text_detection_results.append(f"✅ {os.path.basename(image_path)}: '{detected_text[:30]}{'...' if len(detected_text) > 30 else ''}' ({confidence:.1f}%)")
        else:
            filtered_count += 1
            # Clean up filtered image file to save space
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"⚠️ Could not remove filtered image {image_path}: {e}")
    
    # Print detailed results
    print(f"✅ Text-based image filtering complete:")
    print(f"   📝 {len(filtered_images)} images with text content kept")
    print(f"   🗑️  {filtered_count} images without text filtered out")
    
    if text_detection_results:
        print(f"📋 Text detection results:")
        for result in text_detection_results[:5]:  # Show first 5 results
            print(f"   {result}")
        if len(text_detection_results) > 5:
            print(f"   ... and {len(text_detection_results) - 5} more")
    
    return filtered_images

# -------- STEP 3: Process Images with GPT-4 Vision (Parallel) --------
def encode_image_to_base64(image_path):
    """Encode image to base64 for GPT-4 Vision"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def describe_image_with_gpt(image_path):
    """Describe image using GPT-4 Vision with token counting"""
    try:
        image_b64 = encode_image_to_base64(image_path)
        image_url = f"data:image/png;base64,{image_b64}"

        # Prepare input message for token counting
        input_text = "Describe this clinical figure or chart in detail."
        
        message = [
            HumanMessage(content=[
                {"type": "text", "text": input_text},
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ]

        response = llm.invoke(message)
        
        # Count tokens using tiktoken
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4o")
            
            # Count text tokens
            input_tokens = len(encoding.encode(input_text))
            
            # Add image tokens (GPT-4o uses approximately 85 tokens per image)
            input_tokens += 85
            
            output_tokens = len(encoding.encode(str(response.content))) if response and response.content else 0
            total_tokens = input_tokens + output_tokens
            
            print(f"📊 PDF image processing tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
        except Exception as token_error:
            print(f"Warning: Failed to count tokens: {token_error}")
            # Fallback to character counting (less accurate for images)
            input_tokens = len(input_text) + 85  # Add estimated image tokens
            output_tokens = len(str(response.content)) if response and response.content else 0
            total_tokens = input_tokens + output_tokens
        
        # Ensure we always return a string, never None
        description = str(response.content) if response and response.content else "No description available"
        
        return {
            "description": description,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return {
            "description": f"Error processing image: {str(e)}",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }

def process_images_parallel(image_paths, max_workers=4):
    """Process multiple images in parallel using ThreadPoolExecutor"""
    image_captions = []
    
    # Validate input
    if not image_paths or not isinstance(image_paths, list):
        print("⚠️  No valid image paths provided")
        return []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all image processing tasks
        future_to_image = {}
        for img in image_paths:
            # Validate image data structure
            if not isinstance(img, dict) or 'path' not in img or 'page' not in img:
                print(f"⚠️  Invalid image data structure: {img}")
                continue
                
            future = executor.submit(describe_image_with_gpt, img["path"])
            future_to_image[future] = img
        
        # Collect results as they complete
        total_tokens_used = 0
        for future in as_completed(future_to_image):
            img = future_to_image[future]
            try:
                result = future.result()
                # Handle new return format with token counts
                if isinstance(result, dict):
                    caption = result.get("description", "No description available")
                    input_tokens = result.get("input_tokens", 0)
                    output_tokens = result.get("output_tokens", 0)
                    tokens = result.get("total_tokens", 0)
                    total_tokens_used += tokens
                else:
                    # Fallback for old format
                    caption = str(result) if result else "No description available"
                    input_tokens = 0
                    output_tokens = 0
                    tokens = 0
                
                image_captions.append({
                    "page": img["page"], 
                    "path": img["path"], 
                    "caption": caption,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": tokens
                })
                print(f"✓ Processed image from page {img['page']} (tokens: {tokens})")
            except Exception as e:
                print(f"✗ Error processing image from page {img['page']}: {e}")
                image_captions.append({
                    "page": img["page"], 
                    "path": img["path"], 
                    "caption": f"Error: {str(e)}",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                })
    
    print(f"📊 Total tokens used for image processing: {total_tokens_used}")
    return image_captions


def process_images_parallel_with_progress(image_paths, max_workers=4, progress_callback=None):
    """Process multiple images in parallel with progress reporting"""
    image_captions = []
    
    # Validate input
    if not image_paths or not isinstance(image_paths, list):
        print("⚠️  No valid image paths provided")
        return []
    
    total_images = len(image_paths)
    processed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all image processing tasks
        future_to_image = {}
        for img in image_paths:
            # Validate image data structure
            if not isinstance(img, dict) or 'path' not in img or 'page' not in img:
                print(f"⚠️  Invalid image data structure: {img}")
                continue
                
            future = executor.submit(describe_image_with_gpt, img["path"])
            future_to_image[future] = img
        
        # Collect results as they complete
        total_tokens_used = 0
        for future in as_completed(future_to_image):
            img = future_to_image[future]
            try:
                result = future.result()
                # Handle new return format with token counts
                if isinstance(result, dict):
                    caption = result.get("description", "No description available")
                    input_tokens = result.get("input_tokens", 0)
                    output_tokens = result.get("output_tokens", 0)
                    tokens = result.get("total_tokens", 0)
                    total_tokens_used += tokens
                else:
                    # Fallback for old format
                    caption = str(result) if result else "No description available"
                    input_tokens = 0
                    output_tokens = 0
                    tokens = 0
                
                image_captions.append({
                    "page": img["page"], 
                    "path": img["path"], 
                    "caption": caption,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": tokens
                })
                print(f"✓ Processed image from page {img['page']} (tokens: {tokens})")
            except Exception as e:
                print(f"✗ Error processing image from page {img['page']}: {e}")
                image_captions.append({
                    "page": img["page"], 
                    "path": img["path"], 
                    "caption": f"Error: {str(e)}",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                })
            
            # Update progress
            processed_count += 1
            
            # Report progress every 10 images or at milestones
            if progress_callback and (processed_count % 10 == 0 or processed_count == total_images):
                # Calculate progress in the 40-80% range for image processing
                progress_percent = 40 + int((processed_count / total_images) * 40)
                progress_callback(
                    progress_percent, 
                    f"Processing images: {processed_count}/{total_images}"
                )
    
    print(f"📊 Total tokens used for image processing: {total_tokens_used}")
    return image_captions, total_tokens_used

# -------- STEP 4: Concatenate All Content --------
def concatenate_all_content(text, tables, image_captions):
    """Combine all extracted content into a single text"""
    # Ensure text is a string
    if text is None:
        text = ""
    
    final_text = str(text) + "\n\n"
    
    # Add tables
    if tables:
        final_text += "\n=== TABLES ===\n"
        for page, table in tables:
            final_text += f"\n--- Table from Page {page} ---\n"
            # Ensure table data is valid
            if table and isinstance(table, list):
                table_str = "\n".join([" | ".join([str(cell) for cell in row if cell is not None]) for row in table if row])
                final_text += table_str + "\n"
    
    # Add image descriptions
    if image_captions:
        final_text += "\n=== IMAGE DESCRIPTIONS ===\n"
        for item in image_captions:
            # Ensure all values are strings and not None
            page = str(item.get('page', 'Unknown')) if item.get('page') is not None else 'Unknown'
            path = str(item.get('path', 'Unknown')) if item.get('path') is not None else 'Unknown'
            caption = str(item.get('caption', 'No description')) if item.get('caption') is not None else 'No description'
            
            final_text += f"\n--- Image from Page {page} ---\n"
            final_text += f"Path: {path}\n"
            final_text += f"Description: {caption}\n"
    
    return final_text

# -------- STEP 5: Store in Vector Database --------
def store_in_vector_db(text_content, pdf_name, vector_db_path="vector_db", pdf_id=None, user_id=None, org_id=None):
    """Store the extracted content in a vector database"""
    upload_time = datetime.datetime.now().isoformat()
    
    try:
        # Create vector database directory for local storage
        os.makedirs(vector_db_path, exist_ok=True)
        
        # Split text into chunks
        chunks = text_splitter.split_text(text_content)
        
        if not chunks:
            print(f"⚠️  [{pdf_name}] No content to store in vector database")
            return 0
        
        # Create documents with comprehensive metadata
        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": pdf_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "upload_time": upload_time,
                "processing_time": datetime.datetime.now().isoformat(),
                "text_length": len(text_content)
            }
            
            # Add PDF-specific metadata for Pinecone
            if pdf_id:
                metadata["pdf_id"] = pdf_id
            if user_id:
                metadata["user_id"] = user_id
            if org_id:
                metadata["org_id"] = org_id

            
            documents.append(Document(
                page_content=chunk,
                metadata=metadata
            ))
        
        # Get vector database type and initialize appropriate backend
        db_type = get_vector_db_type()
        
        if db_type == "pinecone":
            # Use Pinecone
            vector_db = get_vector_database(
                db_type="pinecone",
                api_key=get_pinecone_api_key(),
                environment=get_pinecone_environment(),
                index_name=get_pinecone_index_name(),
                embeddings=embeddings
            )
        else:
            # Use local database (existing behavior)
            vector_db = get_vector_database(
                db_type="local",
                persist_directory=vector_db_path,
                embeddings=embeddings
            )
        
        # Store documents using the interface
        success = vector_db.store_documents(documents, {"source": pdf_name, "pdf_id": pdf_id, "user_id": user_id})
        
        if success:
            print(f"✓ [{pdf_name}] Stored {len(chunks)} chunks in vector database with metadata: pdf_id={pdf_id}, user_id={user_id}")
            return len(chunks)
        else:
            print(f"❌ [{pdf_name}] Failed to store documents in vector database")
            return 0
            
    except Exception as e:
        print(f"❌ [{pdf_name}] Error storing in vector database: {e}")
        return 0

def search_vector_db(query, vector_db_path="vector_db", top_k=5):
    """Search the vector database for relevant content"""
    
    try:
        # Get vector database type
        db_type = get_vector_db_type()
        
        if db_type == "pinecone":
            # Use Pinecone
            vector_db = get_vector_database(
                db_type="pinecone",
                api_key=get_pinecone_api_key(),
                environment=get_pinecone_environment(),
                index_name=get_pinecone_index_name(),
                embeddings=embeddings
            )
        else:
            # Use local database
            if not os.path.exists(vector_db_path):
                print("❌ Vector database not found. Please process PDFs first.")
                return []
            
            vector_db = get_vector_database(
                db_type="local",
                persist_directory=vector_db_path,
                embeddings=embeddings
            )
        
        # Search using the interface
        results = vector_db.search(query, top_k=top_k)
        
        print(f"✓ Found {len(results)} relevant documents for query: '{query}'")
        return results
        
    except Exception as e:
        print(f"❌ Error searching vector database: {e}")
        return []

# -------- SINGLE PDF PIPELINE --------
def run_single_pdf_pipeline(pdf_path, max_workers=4, pdf_id=None, user_id=None, org_id=None, progress_callback=None):
    """Process a single PDF file with optional progress reporting"""
    pdf_name = os.path.basename(pdf_path)
    print(f"🚀 Starting processing: {pdf_name}")
    print(f"📄 PDF ID: {pdf_id}, User ID: {user_id}")
    start_time = datetime.datetime.now()
    
    try:
        # Step 1: Extract text and tables
        print(f"📖 [{pdf_name}] Extracting text and tables...")
        text, tables = extract_text_tables(pdf_path)
        
        # Ensure text and tables are valid
        if text is None:
            text = ""
        if tables is None:
            tables = []
            
        print(f"✓ [{pdf_name}] Extracted text from {len(text.split('--- Page')) if text else 0} pages")
        print(f"✓ [{pdf_name}] Found {len(tables)} tables")
        
        # Report progress after text extraction
        if progress_callback:
            pages_count = len(text.split('--- Page')) if text else 0
            progress_callback(35, f"Extracted text from {pages_count} pages and {len(tables)} tables")
        
        # Step 2: Extract images
        print(f"🖼️  [{pdf_name}] Extracting images...")
        image_paths = extract_images(pdf_path)
        
        # Ensure image_paths is valid
        if image_paths is None:
            image_paths = []
            
        print(f"✓ [{pdf_name}] Extracted {len(image_paths)} images")
        
        # Step 2.5: Filter images for textual content using OCR
        if image_paths:
            print(f"🔍 [{pdf_name}] Filtering images for textual content using OCR...")
            filtered_image_paths = filter_informational_images(
                image_paths, 
                use_ocr=USE_OCR_FOR_IMAGE_FILTERING,  # Use OCR for text detection
                min_text_length=OCR_MIN_TEXT_LENGTH,  # Minimum characters of text
                confidence_threshold=OCR_CONFIDENCE_THRESHOLD  # Confidence threshold
            )
            print(f"✓ [{pdf_name}] Filtered to {len(filtered_image_paths)} images with text content")
            
            # Report progress after image filtering
            if progress_callback:
                progress_callback(45, f"Filtered to {len(filtered_image_paths)} images with text content")
        else:
            filtered_image_paths = []
            print(f"ℹ️  [{pdf_name}] No images found to filter")
        
        # Step 3: Process filtered images with LLM (parallel)
        total_tokens_used = 0  # Initialize token counter
        if filtered_image_paths:
            print(f"🤖 [{pdf_name}] Processing {len(filtered_image_paths)} informational images with GPT-4 Vision (parallel)...")
            # Pass progress callback for image processing
            image_captions, total_tokens_used = process_images_parallel_with_progress(filtered_image_paths, max_workers, progress_callback)
            print(f"✓ [{pdf_name}] Processed {len(image_captions)} informational images")
            
            # Report completion of image processing
            if progress_callback:
                progress_callback(80, f"Processed all {len(image_captions)} informational images")
        else:
            image_captions = []
            print(f"ℹ️  [{pdf_name}] No informational images found to process")
        
        # Step 4: Concatenate everything
        print(f"🔗 [{pdf_name}] Concatenating all content...")
        final_text = concatenate_all_content(text, tables, image_captions)
        
        # Step 5: Store in vector database
        print(f"🗄️  [{pdf_name}] Storing in vector database...")
        if progress_callback:
            progress_callback(85, "Creating vector database...")


        chunks_stored = store_in_vector_db(final_text, pdf_name, VECTOR_DB_DIR, pdf_id, user_id, org_id)
        
        if progress_callback:
            progress_callback(95, f"Stored {chunks_stored} chunks in vector database")
        
        end_time = datetime.datetime.now()
        total_time = end_time - start_time
        
        print(f"✅ [{pdf_name}] Completed in {total_time}")
        
        # Note: Cleanup will be handled by the caller after all processing is complete
        # to avoid race conditions with parallel image processing
        
        return {
            "pdf_name": pdf_name,
            "pdf_path": pdf_path,
            "pdf_id": pdf_id,
            "user_id": user_id,
            "final_text": final_text,
            "stats": {
                "text_length": len(text),
                "table_count": len(tables),
                "image_count": len(filtered_image_paths),  # Use filtered count for meaningful images
                "total_images_extracted": len(image_paths),  # Keep track of total extracted
                "chunks_stored": chunks_stored,
                "llm_tokens": total_tokens_used,  # Include LLM tokens for tracking
                "processing_time": total_time
            },
            "success": True
        }
        
    except Exception as e:
        end_time = datetime.datetime.now()
        total_time = end_time - start_time
        print(f"❌ [{pdf_name}] Failed after {total_time}: {e}")
        
        return {
            "pdf_name": pdf_name,
            "pdf_path": pdf_path,
            "final_text": "",
            "stats": {
                "text_length": 0,
                "table_count": 0,
                "image_count": 0,
                "chunks_stored": 0,
                "processing_time": total_time
            },
            "success": False,
            "error": str(e)
        }

# -------- MULTI-PDF ASYNC PIPELINE --------
async def process_multiple_pdfs_async(pdf_paths, max_concurrent_pdfs=3, max_image_workers=4):
    """Process multiple PDFs concurrently using asyncio and ThreadPoolExecutor"""
    print(f"🚀 Starting multi-PDF pipeline with {len(pdf_paths)} files...")
    print(f"📊 Max concurrent PDFs: {max_concurrent_pdfs}, Max image workers per PDF: {max_image_workers}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Use ThreadPoolExecutor for CPU-bound PDF processing
    with ThreadPoolExecutor(max_workers=max_concurrent_pdfs) as executor:
        # Submit all PDF processing tasks
        loop = asyncio.get_event_loop()
        tasks = []
        
        for pdf_path in pdf_paths:
            task = loop.run_in_executor(
                executor, 
                run_single_pdf_pipeline, 
                pdf_path, 
                max_image_workers
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Clean up images folder after all processing is complete
    cleanup_images_folder()
    
    return results

# -------- UTILITY FUNCTIONS --------
def cleanup_images_folder(images_folder="images"):
    """
    Clean up the images folder after processing is complete.
    This removes all extracted images to save disk space.
    """
    try:
        if os.path.exists(images_folder):
            import shutil
            shutil.rmtree(images_folder)
            print(f"🧹 Cleaned up images folder: {images_folder}")
        else:
            print(f"ℹ️  Images folder does not exist: {images_folder}")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up images folder {images_folder}: {e}")

def find_pdf_files(directory):
    """Find all PDF files in the specified directory"""
    pdf_files = []
    for file in os.listdir(directory):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, file))
    return pdf_files

async def save_results(results):
    """Save all results to files"""
    print("\n💾 Saving results...")
    
    # Save individual PDF results
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Skipping result due to exception: {result}")
            continue
            
        if result["success"]:
            pdf_name = result["pdf_name"]
            safe_name = pdf_name.replace(".pdf", "").replace(" ", "_")
            
            # Save text content
            text_file = os.path.join(OUTPUT_DIR, f"{safe_name}_extracted.txt")
            async with aiofiles.open(text_file, 'w', encoding='utf-8') as f:
                await f.write(result["final_text"])
            
            # Save metadata
            meta_file = os.path.join(OUTPUT_DIR, f"{safe_name}_metadata.json")
            async with aiofiles.open(meta_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(result["stats"], indent=2, default=str))
            
            print(f"✓ Saved results for {pdf_name}")
    
    # Save summary report
    summary_file = os.path.join(OUTPUT_DIR, "processing_summary.txt")
    summary_content = generate_summary_report(results)
    async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
        await f.write(summary_content)
    
    print(f"✓ Saved summary report to {summary_file}")
    
    # Clean up images folder after saving all results
    cleanup_images_folder()

def generate_summary_report(results):
    """Generate a summary report of all processing results"""
    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    summary = f"""PDF Processing Summary Report
Generated: {datetime.datetime.now()}

TOTAL PDFs: {len(results)}
SUCCESSFUL: {len(successful)}
FAILED: {len(failed)}
EXCEPTIONS: {len(exceptions)}

=== SUCCESSFUL PROCESSING ===
"""
    
    for result in successful:
        stats = result["stats"]
        summary += f"""
📄 {result['pdf_name']}
   Text Length: {stats['text_length']} characters
   Tables: {stats['table_count']}
   Images: {stats['image_count']}
   Processing Time: {stats['processing_time']}
"""
    
    if failed:
        summary += "\n=== FAILED PROCESSING ===\n"
        for result in failed:
            summary += f"❌ {result['pdf_name']}: {result.get('error', 'Unknown error')}\n"
    
    if exceptions:
        summary += "\n=== EXCEPTIONS ===\n"
        for exc in exceptions:
            summary += f"💥 Exception: {exc}\n"
    
    return summary

# -------- NON-PDF PROCESSING (DOC/DOCX/TXT) --------
