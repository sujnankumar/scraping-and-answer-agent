import os
import uuid
import time
from typing import Dict, List, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Initialize clients
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# Define the state for the LangGraph workflow
class ResearchState(TypedDict):
    query: str
    research_data: List[Dict]
    drafted_answer: str
    messages: List[HumanMessage | AIMessage]

# Research Agent: Collects data using Tavily
def research_agent(state: ResearchState) -> ResearchState:
    query = state["query"]
    try:
        # Perform Tavily search
        search_results = tavily_client.search(
            query=query,
            max_results=5,
            search_depth="advanced",
            include_raw_content=True
        )
        # Extract relevant data
        research_data = [
            {
                "url": result["url"],
                "title": result["title"],
                "content": result["content"][:1000],  # Limit content length
                "source": "web"
            }
            for result in search_results["results"]
        ]
        return {
            "research_data": research_data,
            "messages": state["messages"] + [AIMessage(content=f"Collected {len(research_data)} research items.")],
            "query": query,
            "drafted_answer": state.get("drafted_answer", "")
        }
    except Exception as e:
        return {
            "research_data": [],
            "messages": state["messages"] + [AIMessage(content=f"Error in research: {str(e)}")],
            "query": query,
            "drafted_answer": state.get("drafted_answer", "")
        }

# Answer Drafter Agent: Synthesizes research data into a coherent response
def answer_drafter_agent(state: ResearchState) -> ResearchState:
    prompt = ChatPromptTemplate.from_template("""
    You are an expert answer drafter. Based on the following research data and user query, create a concise, well-structured, and informative response. Ensure the answer is clear, addresses the query directly, and cites sources where relevant.

    **User Query**: {query}

    **Research Data**:
    {research_data}

    **Instructions**:
    - Summarize key findings.
    - Provide a clear and concise answer (max 500 words).
    - Cite sources using [Source: URL] format.
    - If no relevant data is found, explain the limitation and suggest next steps.
    """)
    
    research_data_str = "\n".join(
        [f"Title: {item['title']}\nURL: {item['url']}\nContent: {item['content']}" for item in state["research_data"]]
    ) if state["research_data"] else "No research data available."
    
    chain = prompt | llm
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = chain.invoke({
                "query": state["query"],
                "research_data": research_data_str
            })
            return {
                "drafted_answer": response.content,
                "messages": state["messages"] + [AIMessage(content="Drafted answer completed.")],
                "query": state["query"],
                "research_data": state["research_data"]
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return {
                "drafted_answer": "Failed to draft answer due to API error.",
                "messages": state["messages"] + [AIMessage(content=f"Error in drafting: {str(e)}")],
                "query": state["query"],
                "research_data": state["research_data"]
            }

# Define the LangGraph workflow
workflow = StateGraph(ResearchState)

# Add nodes
workflow.add_node("research_agent", research_agent)
workflow.add_node("answer_drafter_agent", answer_drafter_agent)

# Define edges
workflow.add_edge("research_agent", "answer_drafter_agent")
workflow.add_edge("answer_drafter_agent", END)

# Set entry point
workflow.set_entry_point("research_agent")

# Compile the graph
app = workflow.compile()

# Function to run the research system
def run_research_system(query: str) -> Dict:
    initial_state = {
        "query": query,
        "research_data": [],
        "drafted_answer": "",
        "messages": [HumanMessage(content=query)]
    }
    result = app.invoke(initial_state)
    return result

# Example usage
if __name__ == "__main__":
    query = "in which year iitb had some fest on march 20"
    result = run_research_system(query)
    print("Query:", result["query"])
    print("\nResearch Data:")
    for item in result["research_data"]:
        print(f"- {item['title']} [{item['url']}]")
    print("\nDrafted Answer:")
    print(result["drafted_answer"])
    print("\nMessages:")
    for msg in result["messages"]:
        print(f"- {msg.content}")