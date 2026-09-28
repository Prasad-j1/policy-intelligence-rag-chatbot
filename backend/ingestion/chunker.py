from typing import List


# def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
#     """
#     Splits text into overlapping chunks based on word count.
#     chunk_size and chunk_overlap come from config.py, never hardcoded here.
#     """
#     words = text.split()
#     chunks = []

#     start = 0
#     while start < len(words):
#         end = start + chunk_size
#         chunk_words = words[start:end]
#         chunks.append(" ".join(chunk_words))

#         # move start forward, but overlap with previous chunk
#         start += chunk_size - chunk_overlap

#     return chunks


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for para in paragraphs:
        words = para.split()
        if len(words) <= chunk_size:
            chunks.append(para)  # short section stays whole, never gets merged with neighbors
            continue

        # only long paragraphs get cut by word count, same sliding-window as before
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - chunk_overlap

    return chunks