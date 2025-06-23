from langchain.chat_models import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools.retriever import create_retriever_tool
from app.utils.policy_loader import load_policy_vectorstore

retriever = load_policy_vectorstore().as_retriever(search_kwargs={"k": 3})
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="PolicyRetriever",
    description="Find matching policy rules for lifecycle decisions"
)

llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = create_react_agent(llm=llm, tools=[retriever_tool])
executor = AgentExecutor(agent=agent, verbose=True)

def match_policy(content: str, metadata: dict):
    query = f"""
    Given this document content and metadata, recommend a policy-based lifecycle action.
    Metadata: {metadata}
    Document:\n{content[:1200]}
    """
    return executor.invoke({"input": query})