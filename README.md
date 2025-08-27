Deep Research AI Agentic System
Overview
This project implements a Deep Research AI Agentic System using LangChain, LangGraph, and Tavily for web-based information gathering. The system is designed with a dual-agent architecture:

Research Agent: Crawls the web using Tavily to collect relevant data.
Answer Drafter Agent: Synthesizes the collected data into a coherent, well-structured response using Google's Gemini model (gemini-1.5-flash).

The workflow is orchestrated using LangGraph, ensuring modularity and state management. The system is designed to be extensible, with clear separation of concerns and robust error handling.
Features

Web Crawling: Utilizes Tavily for advanced web search and content extraction.
Agentic Workflow: Dual-agent system with distinct roles for research and answer drafting.
State Management: LangGraph manages the state, tracking query, research data, drafted answers, and conversation history.
Free-Tier LLM: Uses Google's Gemini (gemini-1.5-flash) for cost-free operation within free-tier limits.
Modular Design: Easily extensible to add more agents or integrate additional tools.
Error Handling: Gracefully handles API errors and empty search results with retry logic.
Customizable Output: Drafted answers are concise, cite sources, and address the query directly.

Prerequisites

Python 3.9+
API Keys:
Google API Key (for Gemini, free tier available)
Tavily API Key (for web search)


Dependencies (install via requirements.txt):
langchain
langchain-google-genai
langgraph
tavily-python
python-dotenv



Installation

Clone the repository:
git clone https://github.com/sujnankumar/scraping-and-answer-agent.git
cd deep-research-system


Create a virtual environment and install dependencies:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


Set up environment variables: Create a .env file in the root directory with the following:
GOOGLE_API_KEY=your-google-api-key
TAVILY_API_KEY=your-tavily-api-key


Obtain a Google API Key:

Go to Google Cloud Console.
Create a new project or select an existing one.
Enable the Generative AI API (or similar, depending on Google's naming).
Create an API key and add it to your .env file.



Usage
Two options:

1) CLI quick test
	 - Run the main script (contains an example query you can edit inside):
		 python main.py

2) Streamlit app (interactive UI)
	 - Install requirements (in your venv):
		 pip install -r requirements.txt
	 - Start the app:
		 streamlit run app.py
	 - Open the shown local URL, enter your query, and click "Run Research".
Example Output
Query: What are the latest advancements in quantum computing?

Research Data:
- Quantum Computing Breakthroughs [https://example.com/quantum]
- Advances in Quantum Hardware [https://example.com/hardware]

Drafted Answer:
Recent advancements in quantum computing include breakthroughs in qubit stability and error correction. [Source: https://example.com/quantum] Additionally, new hardware designs have improved scalability. [Source: https://example.com/hardware]

Messages:
- What are the latest advancements in quantum computing?
- Collected 5 research items.
- Drafted answer completed.

Implementation Details
Architecture

LangGraph Workflow:
Nodes: research_agent and answer_drafter_agent.
Edges: Sequential flow from research to drafting, ending after the answer is drafted.
State: Tracks query, research_data, drafted_answer, and messages.


Research Agent:
Uses Tavily's advanced search with a limit of 5 results.
Extracts title, URL, and content (truncated to 1000 characters).
Handles API errors and logs issues in the state.


Answer Drafter Agent:
Uses a ChatPromptTemplate to structure the response with Gemini (gemini-1.5-flash).
Summarizes research data, cites sources, and ensures clarity.
Includes retry logic with exponential backoff for API errors.
Falls back to explaining limitations if no data is available.

Author
[Sujnan Kumar][7899069448][[https://github.com/sujnankumar](https://github.com/sujnankumar)]
