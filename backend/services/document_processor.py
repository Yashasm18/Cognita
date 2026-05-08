"""Document processing service — extracts text from PDFs, images, and text files."""

import os
import uuid
import base64
import fitz  # PyMuPDF


class DocumentProcessor:
    """Processes uploaded documents and extracts their content."""

    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    async def process_file(
        self, file_content: bytes, filename: str, content_type: str
    ) -> dict:
        """Process an uploaded file and extract its content.

        Returns a dict with file_id, filename, file_type, extracted_text,
        content_preview, page_count, images, and raw_bytes.
        """
        file_id = str(uuid.uuid4())[:8]
        file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Persist the raw file
        save_path = os.path.join(self.upload_dir, f"{file_id}_{filename}")
        with open(save_path, "wb") as f:
            f.write(file_content)

        result = {
            "file_id": file_id,
            "filename": filename,
            "file_path": save_path,
            "file_type": file_ext,
            "extracted_text": "",
            "content_preview": "",
            "page_count": None,
            "char_count": 0,
            "images": [],
            "raw_bytes": file_content,
        }

        if file_ext == "pdf":
            try:
                result.update(self._process_pdf(file_content))
            except Exception as e:
                result["extracted_text"] = f"[Could not parse PDF: {e}]"
                result["content_preview"] = "[Invalid or corrupted PDF]"
        elif file_ext in ("png", "jpg", "jpeg", "gif", "webp"):
            result.update(self._process_image(file_content, content_type))
        elif file_ext in ("txt", "md", "csv"):
            result.update(self._process_text(file_content))
        else:
            try:
                text = file_content.decode("utf-8", errors="ignore")
                result["extracted_text"] = text
                result["content_preview"] = text[:500]
                result["char_count"] = len(text)
            except Exception:
                result["extracted_text"] = "[Binary file — could not extract text]"
                result["content_preview"] = "[Binary file]"

        return result

    def _process_pdf(self, file_content: bytes) -> dict:
        """Extract text and images from a PDF."""
        doc = fitz.open(stream=file_content, filetype="pdf")
        pages_text = []
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

            # Extract images from the page (limit to 3 per page)
            for img_index, img in enumerate(page.get_images(full=True)[:3]):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    images.append(
                        {
                            "page": page_num + 1,
                            "index": img_index,
                            "format": image_ext,
                            "data": img_b64,
                        }
                    )
                except Exception:
                    continue

        full_text = "\n\n".join(pages_text)
        doc.close()

        return {
            "extracted_text": full_text,
            "content_preview": full_text[:500],
            "page_count": len(pages_text),
            "char_count": len(full_text),
            "images": images[:10],
        }

    def _process_image(self, file_content: bytes, content_type: str) -> dict:
        """Process an image file — store for LLM vision analysis."""
        img_b64 = base64.b64encode(file_content).decode("utf-8")
        return {
            "extracted_text": "[Image file — will be analyzed by AI vision]",
            "content_preview": f"[Image: {content_type}]",
            "char_count": 0,
            "images": [
                {
                    "page": 1,
                    "index": 0,
                    "format": content_type.split("/")[-1],
                    "data": img_b64,
                }
            ],
        }

    def _process_text(self, file_content: bytes) -> dict:
        """Process a plain text, markdown, or CSV file."""
        text = file_content.decode("utf-8", errors="ignore")
        return {
            "extracted_text": text,
            "content_preview": text[:500],
            "char_count": len(text),
        }
