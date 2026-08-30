def clean_text(text):

    if not text:
        return ""


    # 删除空字符
    text = text.replace(
        "\x00",
        ""
    )


    # 删除BOM
    text = text.replace(
        "\ufeff",
        ""
    )


    # 删除特殊换行
    text = text.replace(
        "\u2028",
        ""
    )

    text = text.replace(
        "\u2029",
        ""
    )


    # docx常见特殊空格
    text = text.replace(
        "\xa0",
        " "
    )


    # 普通换行
    text = text.replace(
        "\r",
        ""
    )

    text = text.replace(
        "\n",
        ""
    )


    return text.strip()