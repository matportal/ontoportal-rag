from langchain.text_splitter import MarkdownHeaderTextSplitter

def test_markdown_header_text_splitter():
    """
    Tests that the MarkdownHeaderTextSplitter correctly chunks a document
    based on headers.
    """
    markdown_text = """
# Introduction

This is the first section.

## Details

More details here.

# Second Major Section

Some other content.
"""

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(markdown_text)

    # We expect 3 chunks:
    # 1. The first section under "Introduction"
    # 2. The subsection under "Details"
    # 3. The second major section
    assert len(chunks) == 3

    # Check the content and metadata of the first chunk
    assert "This is the first section." in chunks[0].page_content
    assert chunks[0].metadata == {"Header 1": "Introduction"}

    # Check the content and metadata of the second chunk
    assert "More details here." in chunks[1].page_content
    assert chunks[1].metadata == {"Header 1": "Introduction", "Header 2": "Details"}

    # Check the content and metadata of the third chunk
    assert "Some other content." in chunks[2].page_content
    assert chunks[2].metadata == {"Header 1": "Second Major Section"}
