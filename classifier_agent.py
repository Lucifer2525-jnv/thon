from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0)

def classify_document(content: str):
    prompt = f"""
    Classify the following document into:
    1. Content Type (e.g., HR, Finance, Legal, Personal)
    2. Sensitivity (Public, Internal, Confidential, Restricted)

    Document content:
    {content[:1200]}
    """
    return llm.invoke(prompt)