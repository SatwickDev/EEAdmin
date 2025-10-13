import fitz  # PyMuPDF


def is_page_blank(page):
    """Check if a page is blank by verifying text, images, and vector graphics."""
    text = page.get_text("text")
    images = page.get_images(full=True)
    vectors = len(page.get_drawings())

    return not text.strip() and len(images) == 0 and vectors == 0


def remove_blank_pages(pdf_path, output_path):
    """Reads a PDF, removes blank pages, and saves the filtered PDF."""
    doc = fitz.open(pdf_path)
    new_doc = fitz.open()

    for i, page in enumerate(doc):
        if not is_page_blank(page):
            new_doc.insert_pdf(doc, from_page=i, to_page=i)

    new_doc.save(output_path)
    new_doc.close()
    return output_path  # Return cleaned PDF file path