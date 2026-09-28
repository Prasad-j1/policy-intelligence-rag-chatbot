import fitz

# Point this at one of your actual policy PDFs
file_path = "data/knowledge_base/02_Leave & Time-Off Policy.pdf"

doc = fitz.open(file_path)

for page_number, page in enumerate(doc, start=1):
    print(f"\n===== PAGE {page_number} =====")
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                if text:
                    print(f"size={span['size']:.2f} | bold={'Bold' in span['font']} | text='{text[:60]}'")

    if page_number == 2:  # just check first 2 pages for now
        break

doc.close()