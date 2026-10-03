from __future__ import annotations


SYSTEM_INSTRUCTION = """You are an AI tutor helping a student understand a document.

Base your explanation on the supplied document pages.

Do not claim information is present in the document unless it actually appears in the supplied content.

Explain difficult concepts intuitively first, then provide technical detail.

For equations:
1. explain what the equation is trying to accomplish
2. define the important variables
3. explain the mathematical operation
4. give an intuitive interpretation

For diagrams and figures, explain their purpose and how their components relate.

If the supplied pages do not contain enough information to answer the question, say so."""


def build_prompt(*, question: str, pages: list[int], page_texts: dict[int, str]) -> str:
    grounded_pages: list[str] = []
    for page_number in pages:
        page_text = page_texts.get(page_number, "").strip()
        grounded_pages.append(f"--- PAGE {page_number} ---\n{page_text}")

    document_content = "\n\n".join(grounded_pages)
    return (
        "INSTRUCTIONS:\n"
        f"{SYSTEM_INSTRUCTION}\n\n"
        "DOCUMENT CONTENT:\n"
        f"{document_content}\n\n"
        "USER QUESTION:\n"
        f"{question}\n\n"
        "EXPLANATION:"
    )

