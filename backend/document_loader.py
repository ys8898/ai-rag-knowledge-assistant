import os

from docx import Document
from pypdf import PdfReader


def read_txt(path):

    # 读取txt文件
    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()



def read_docx(path):

    # 读取Word文件

    doc = Document(path)

    texts=[]


    # 遍历每个段落
    for paragraph in doc.paragraphs:

        if paragraph.text.strip():

            texts.append(
                paragraph.text
            )


    return "\n".join(texts)



def read_pdf(path):

    # 读取PDF

    reader = PdfReader(path)

    texts=[]


    for page in reader.pages:

        text = page.extract_text()


        if text:

            texts.append(text)


    return "\n".join(texts)



def load_documents(folder):


    documents=[]
    print(
    "知识库目录文件:"
)

    print(
        os.listdir(folder)
    )

    # 遍历知识库目录
    for filename in os.listdir(folder):


        path=os.path.join(
            folder,
            filename
        )

        lower_filename = filename.lower()  # 转小写再判断

        # txt
        if lower_filename.endswith(".txt"):

            content=read_txt(path)


        # Word
        elif lower_filename.endswith(".docx"):

            content=read_docx(path)


        # PDF
        elif lower_filename.endswith(".pdf"):

            content=read_pdf(path)


        else:

            # 不支持格式跳过
            continue

        if not content.strip():

            continue


        documents.append(
            {
                "text":content,
                "source":filename
            }
        )


    return documents