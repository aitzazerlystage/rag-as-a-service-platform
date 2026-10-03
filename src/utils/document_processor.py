"""
Document processing utilities for the RAG service.
Handles non-PDF document processing (DOC, DOCX, TXT) using Docling.
"""

import os
import base64
import datetime
import io
from typing import Dict, Any, List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Global variables that will be imported from the main app
text_splitter = None
DOC_CONVERTER = None
PictureItem = None
LLM_MODEL = None
LLM_TEMPERATURE = None
LLM_MAX_TOKENS = None
OPENAI_API_KEY = None

def initialize_document_processor(
    text_splitter_instance, 
    doc_converter, 
    picture_item, 
    llm_model, 
    llm_temperature, 
    llm_max_tokens, 
    openai_key
):
    """Initialize the document processor with dependencies from the main app."""
    global text_splitter, DOC_CONVERTER, PictureItem, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OPENAI_API_KEY
    text_splitter = text_splitter_instance
    DOC_CONVERTER = doc_converter
    PictureItem = picture_item
    LLM_MODEL = llm_model
    LLM_TEMPERATURE = llm_temperature
    LLM_MAX_TOKENS = llm_max_tokens
    OPENAI_API_KEY = openai_key

def process_non_pdf_file(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract text from non-PDF documents and return a result compatible with the PDF pipeline output.

    Returns a dict with keys: {"success": bool, "final_text": str, "stats": {...}, "error": str (optional)}
    """
    try:
        ext = os.path.splitext(filename)[1].lower()
        start_time = datetime.datetime.now()

        final_text = ""
        image_count = 0
        
        # Reject PowerPoint files
        if ext in [".ppt", ".pptx"]:
            return {
                "success": False,
                "error": f"PowerPoint files (.ppt, .pptx) are not supported. Please use PDF, DOC, DOCX, or TXT files.",
            }
        
        if ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    final_text = f.read()
            except Exception:
                with open(file_path, "rb") as f:
                    final_text = f.read().decode("utf-8", errors="ignore")
        else:
            if DOC_CONVERTER is None:
                return {
                    "success": False,
                    "error": "Docling not available. Install 'docling' and 'docling-core' to process Office documents.",
                }
            conv_res = DOC_CONVERTER.convert(file_path)
            doc = conv_res.document
            markdown_text = doc.export_to_markdown() or ""

            # Collect images and generate captions using vision LLM
            captions: List[str] = []
            MAX_CAPTION_IMAGES = 8
            try:
                if PictureItem is not None:
                    picture_items = []
                    for element, _level in doc.iterate_items():
                        if PictureItem is not None and isinstance(element, PictureItem):
                            picture_items.append(element)
                    image_count = len(picture_items)

                    if image_count > 0:
                        vision_llm = ChatOpenAI(
                            model=LLM_MODEL,
                            temperature=LLM_TEMPERATURE,
                            max_tokens=LLM_MAX_TOKENS,
                            api_key=OPENAI_API_KEY
                        )
                        limit = min(image_count, MAX_CAPTION_IMAGES)
                        for idx in range(limit):
                            try:
                                pil_img = picture_items[idx].get_image(doc)
                                buffered = io.BytesIO()
                                pil_img.save(buffered, format="PNG")
                                b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                data_url = f"data:image/png;base64,{b64}"
                                system_message = SystemMessage(content=(
                                    "You are a helpful vision assistant. Generate a image description that captures key details (values, units, prices, etc.) relevant to the document context. Do not exclude any details."
                                ))
                                human_message = HumanMessage(content=[
                                    {"type": "text", "text": "Provide a summary for this figure/image from the document. Keep all the details(values, units, prices, etc.) in the image."},
                                    {"type": "image_url", "image_url": {"url": data_url}}
                                ])
                                result = vision_llm.invoke([system_message, human_message])
                                cap = result.content if hasattr(result, "content") else str(result)
                                cap = cap.strip()
                                if cap:
                                    captions.append(f"Image {idx + 1}: {cap}")
                            except Exception as cap_err:
                                print(f"WARNING: Failed to caption image {idx + 1} in {filename}: {cap_err}")
                                continue
            except Exception as e:
                print(f"WARNING: Image extraction/captioning failed for {filename}: {e}")
                image_count = image_count or 0

            if captions:
                captions_block = "\n\n[Image Captions]\n" + "\n".join(f"- {c}" for c in captions) + "\n"
            else:
                captions_block = ""
            final_text = markdown_text + captions_block

        # SemanticChunker calls the embeddings API; failures must not abort extraction (same idea as PDF:
        # store_in_vector_db catches errors and continues with extracted text).
        chunks_preview = []
        if final_text and text_splitter:
            try:
                chunks_preview = text_splitter.split_text(final_text)
            except Exception as chunk_err:
                print(
                    f"WARNING: Semantic chunk preview failed for {filename} (continuing with text only): {chunk_err}"
                )
                chunks_preview = []

        stats = {
            "text_length": len(final_text),
            "table_count": 0,
            "image_count": image_count,
            "chunks_stored": len(chunks_preview),
            "processing_time": str(datetime.datetime.now() - start_time)
        }
        return {
            "success": True,
            "final_text": final_text,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
