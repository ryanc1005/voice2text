"""文字轉 Markdown 格式化"""


def format_as_markdown(filename: str, text: str, prompt: str = "") -> str:
    """將轉錄文字格式化為 Markdown"""
    title = filename.rsplit(".", 1)[0]

    lines = [f"# {title}", ""]

    if prompt:
        lines.extend([f"> **活動資訊**：{prompt}", ""])

    lines.append("---")
    lines.append("")

    # 在中文句號處分段落
    paragraphs = _split_paragraphs(text)
    for para in paragraphs:
        para = para.strip()
        if para:
            lines.append(para)
            lines.append("")

    return "\n".join(lines)


def _split_paragraphs(text: str) -> list[str]:
    """依據中文句號等標點分段，每 3-5 句為一段"""
    # 先按現有換行分
    raw_paragraphs = text.split("\n")

    result = []
    for raw in raw_paragraphs:
        raw = raw.strip()
        if not raw:
            continue

        # 計算句子數量，超過 5 句則拆分
        sentences = []
        current = ""
        for char in raw:
            current += char
            if char in "。！？.!?":
                sentences.append(current)
                current = ""
        if current.strip():
            sentences.append(current)

        # 每 5 句分一段
        chunk_size = 5
        for i in range(0, len(sentences), chunk_size):
            para = "".join(sentences[i:i + chunk_size]).strip()
            if para:
                result.append(para)

    return result
