from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveChunker:
    """
    Production-grade recursive text chunker.

    Splits text using progressively smaller separators:

        Paragraphs
            ↓
        New Lines
            ↓
        Sentences
            ↓
        Spaces
            ↓
        Characters

    This preserves semantic meaning much better than fixed-size chunking.
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ):

        self.splitter = RecursiveCharacterTextSplitter(

            chunk_size=chunk_size,

            chunk_overlap=chunk_overlap,

            separators=[
                "\n\n",
                "\n",
                ". ",
                "? ",
                "! ",
                "; ",
                ", ",
                " ",
                ""
            ],

            length_function=len,

            is_separator_regex=False,
        )

    def split(self, text: str) -> list[str]:
        """
        Split a document into semantic chunks.

        Returns
        -------
        list[str]
            List of cleaned chunks.
        """

        if not text.strip():
            return []

        chunks = self.splitter.split_text(text)

        return [
            chunk.strip()
            for chunk in chunks
            if chunk.strip()
        ]


# Singleton instance
_recursive_chunker = RecursiveChunker()


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Wrapper so the rest of the project can simply call:

        chunk_text(text)

    while internally using RecursiveChunker.
    """

    if (
        _recursive_chunker.splitter._chunk_size != chunk_size
        or
        _recursive_chunker.splitter._chunk_overlap != chunk_overlap
    ):
        chunker = RecursiveChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return chunker.split(text)

    return _recursive_chunker.split(text)