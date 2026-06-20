import os
from typing import Any,Dict,List
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model # Initialize a chat model from any supported provider using a unified interface.
from langchain_core.messages import ToolMessage # ToolMessage : Tool Messages are used to pass the results of a single tool execution back to the model.
from langchain.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

#Initialzie the Embedding Model
embedding_model=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",show_progress=True)
 
# Initialzie the Vector Store
vectorstore=PineconeVectorStore(index_name=os.environ["INDEX_NAME"],embedding=embedding_model)

#Initialzie the Chat Model with the required provider
chat_model=init_chat_model("groq:llama-3.3-70b-versatile",temperature=0) 

# Enitre retrive context tool
# R of RAG : Retrive the relevant chunks
@tool(response_format="content_and_artifact")
def retrive_context(query:str): #Here query is the user query
    """Retrieve relevant documentation (chunks of documentations) to help answer user quries about Langchain"""
    
    retrieved_chunks=vectorstore.as_retriever().invoke(query,k=6)  #retrive the top 6 chunks that are semnatically relevant and related to the user query
    # invoke method is used to perfom the similairty search
    
    # Serialize documents for the model
    serialized = "\n\n".join(
        (f"Source: {doc.metadata.get('source', 'Unknown')}\n\nContent: {doc.page_content}")
        for doc in retrieved_chunks
    )
    
    # Return both serialized content and raw documents
    return serialized, retrieved_chunks


# Agent that will be using the retrive_context tool
# This function will run the RAG retrival Piepline to answer the question
def run_llm(query:str)-> Dict[str,Any]:
    """
    Run the RAG pipeline to answer a query using retrieved documentation.
    
    Args:
        query: The user's question
        
    Returns:
        Dictionary containing:
            - answer: The generated answer
            - context: List of retrieved documents/chunks
    """
    # Create the agent with one retrieval tool
    system_prompt = (
        "You are a helpful AI assistant that answers questions about LangChain documentation. "
        "You have access to a tool that retrieves relevant documentation or explicilty the chunks of the documentations. "
        "Use the tool to find relevant information before answering questions. "
        "Always cite the sources you use in your answers. "
        "If you cannot find the answer in the retrieved documentation, say so."
    )
    
    agent=create_agent(model=chat_model,tools=[retrive_context],system_prompt=system_prompt)
    
    # Build messages list
    messages = [{"role": "user", "content": query}]
    
    # Invoke the agent
    response = agent.invoke({"messages": messages})
    
    # Extract the answer from the last AI message
    answer = response["messages"][-1].content
    
    # Extract context documents from ToolMessage artifacts
    context_docs = []
    for message in response["messages"]:
        # Check if this is a ToolMessage with artifact
        if isinstance(message, ToolMessage) and hasattr(message, "artifact"):
            # The artifact should contain the list of Document objects
            if isinstance(message.artifact, list):
                context_docs.extend(message.artifact)
    
    return {
        "answer": answer,
        "context": context_docs
    }
    
if __name__ == '__main__':
    result = run_llm(query="what is meant by chain in langchain?")
    print(result)
    
    
    
    