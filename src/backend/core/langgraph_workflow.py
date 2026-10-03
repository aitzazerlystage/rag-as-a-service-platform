"""
LangGraph workflow for LLM processing with pre-retrieved context
"""

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.prompts import ChatPromptTemplate
import sqlite3
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic


# Import configuration
from config.settings import (
    OPENAI_API_KEY,
    GOOGLE_API_KEY,
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    get_OPENAI_API_KEY
)

# Note: LLM instances are now created dynamically based on provider in response_node

# Note: Embeddings are no longer needed for pure LLM workflow

# Database path helper function
def get_db_path():
    """Get the correct path to the chatbot.db file."""
    # Get the project root directory (parent of src)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    db_path = os.path.join(project_root, 'chatbot.db')
    return db_path

# Database connection for chat history
conn = sqlite3.connect(database=get_db_path(), check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

class RagState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def format_history(messages):
    """Format conversation history for context"""
    formatted = []
    for msg in messages[:-1]:  # Exclude the current question
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        formatted.append(f"{role}: {msg.content}")
    return "\n".join(formatted) if formatted else "No previous conversation."


def response_node(state: RagState, org_id: str, project_id: str, model: str = None, context: str = None, openai_api_key: str = None, include_history: bool = True):
    """
    LangGraph response node that processes pre-retrieved context
    Pure LLM processing workflow - relies on pre-provided context from the endpoint
    """
    try:
        print(f"🤖 Processing chat request with pre-retrieved context for Org: {org_id}, Project: {project_id}")
        
        # Get the latest question
        latest_question = state["messages"][-1].content
        print(f"📝 Processing question: {latest_question}")
        
        # Format conversation history (excluding current question) - only if history is enabled
        if include_history and len(state["messages"]) > 1:
            history_text = format_history(state["messages"])
            print(f"📚 HISTORY PREVIEW (include_history=True):")
            print(f"📚 History length: {len(history_text)} characters")
            print(f"📚 History preview (last 300 chars): ...{history_text[-300:]}")
        else:
            history_text = "No previous conversation."  # or "" if you want empty history
            print(f"📚 HISTORY PREVIEW (include_history=False): No conversation history will be sent to LLM")
        
        # Use provided context (required - no fallback retrieval)
        if context and context.strip():
            print(f"✅ Using provided context: {len(context)} characters")
            context_text = context
            print(f"📄 Context preview: {context_text[:200]}...")
        else:
            print("⚠️ Warning: No context provided - this should not happen in the new architecture")
            context_text = "No context available for this query. Please ensure retrieval is performed at the endpoint level."
        
        # Enhanced template that uses both context and history, with special handling for multi-PDF questions
        # template = """You are a helpful assistant that can answer questions about multiple documents and other type of files. 
        # Answer the question based on the retrieved context from the documents and conversation history.

        # CRITICAL INSTRUCTIONS:
        # 1. For conversational greetings (like "Hi", "Hello", "How are you?") or general questions not related to documents, respond naturally without requiring document context
        # 2. For document-related questions, ALWAYS use the retrieved context below to answer the question
        # 3. The retrieved context contains relevant information from the user's documents
        # 4. If the context contains information related to the question, provide a comprehensive answer based on that context
        # 5. If the context contains partial information, explain what you found and what might be missing
        # 6. Only say "no relevant information found" if the context is completely empty or contains no information related to the question AND the user is asking about documents
        # 7. IMPORTANT: The context below contains actual document content - use it to answer document-related questions
        # 8. **FORMAT YOUR RESPONSE IN MARKDOWN** - Use headers, lists, code blocks, bold text, etc. for better readability
        
        # IMPORTANT:  Only say "No Relevant Information Found" if the context is completely empty or contains no information related to the question.
        
        # When answering questions about multiple documents:
        # - If the user is asking for comparisons between documents, clearly identify which information comes from which document
        # - If the user is asking about similarities or differences, highlight the key points from each document
        # - If the user is asking general questions that span multiple documents, synthesize the information coherently
        # - Always cite the source document when providing specific information

        # Note: The Retrieved Context can be from PDF, TXT, DOC, or DOCX files. Always check the metadata of the context.
        
        # **MARKDOWN FORMATTING GUIDELINES:**
        # - Use # for main headings, ## for subheadings, ### for sub-subheadings
        # - Use **bold text** for emphasis and important points
        # - Use *italic text* for subtle emphasis
        # - Use - for bullet points and 1. 2. 3. for numbered lists
        # - Use `inline code` for code snippets and ```language for code blocks
        # - Use > for blockquotes and important notes
        # - Use | for tables when presenting structured data
        # - Use [link text](url) for links when relevant
        
        # SPECIAL CASES:
        # - If the user says greetings like "Hi", "Hello", "Hey", "Good morning", etc., respond warmly and ask how you can help with their documents
        # - If the user asks general questions not related to documents, respond helpfully and offer to help with document-related questions
        # - Only use the retrieved context when the user is asking specific questions about their documents or files
        
        # RELEVANCE CHECK:
        # - If the retrieved context is completely empty, say "No relevant docs found"
        # - If the retrieved context exists but contains NO information related to the user's question, say "No relevant docs found"
        # - Only provide detailed answers when the context contains relevant information about the user's question
        # {history_section}
        
        # Retrieved Context (USE THIS TO ANSWER DOCUMENT-RELATED QUESTIONS):
        # {context}
        
        # Current Question: {question}
        
        # IMPORTANT: Before answering, check if the context contains information relevant to the question. If not, respond with "No relevant data found". If relevant information exists, provide a detailed answer in **MARKDOWN FORMAT**:"""

        template= """You are a highly capable assistant designed to respond to inquiries based on multiple documents and various types of files. Your primary responsibility is to provide precise and accurate answers to questions, referencing the context retrieved from these documents and the conversation history.

### CRITICAL INSTRUCTIONS:

1. **Conversational Greetings**:
   - For general greetings (e.g., "Hi", "Hello", "How are you?"), respond naturally without the need for document context.

2. **Document-Related Inquiries**:
   - Always base your responses on the context retrieved from the relevant documents or files.
   - If the user asks about specific content from a document, ensure your answer is grounded in the provided context.

2.1 **Unrelated to Context Questions**:
   - If the user asks a question that is not related to the context, start your answer with "This question is not related to the context. Although I will answer it based on my knowledge." Then answer the question.
3. **Context Usage**:
   - The context includes information directly extracted from the documents and conversation history.
   - If relevant information exists within the context, provide a comprehensive answer.
   - If the context only provides partial information, explain what is available and highlight what might be missing.

4. **Answer Format**:
   - If relevant information exists, provide a detailed answer in **MARKDOWN FORMAT**. 

   **consistant Format of Answer**:
   - Always have a Consistant format while answering.

   **Prefered Format**:
   - The Answer Must Be In Bullet Points
   - The Answer Must Include Headings
   - The Answer Format Must be Consistant everytime

   **Example**:

        ### **Benefits of Drinking Water**

        1. **Keeps You Hydrated**
            
            - Maintains the balance of bodily fluids.
            - Supports digestion, absorption, circulation, and temperature regulation.

        2. **Improves Physical Performance**

            -Prevents fatigue during exercise.
            -Reduces the risk of cramps and dizziness.

        3. **Supports Healthy Skin**

            -Keeps skin moisturized and glowing.
            -Helps flush out toxins that may cause acne.

5. **Metadata Awareness**:
    Each document you receive includes a metadata block in this format:

    ------------------- METADATA -------------------
    Title: <TITLE_OF_DOCUMENT>
    Authors: <AUTHORS_LIST>
    Journal: <JOURNAL_NAME>
    Publication Date: <DATE>
    DOI: <DOI>
    ------------------------------------------------

    ALWAYS use these exact fields when the user asks about titles, authors, journal, publication dates, or DOI.

    - **When user asks for titles → ONLY return values from "Title:"**
    - **When user asks for authors → ONLY return values from "Authors:"**
    - **Do NOT guess or extract from PDF text unless metadata is missing.**
    - If multiple documents are in the context, return multiple titles/authors accordingly.
   - Always check the metadata of the files to determine their type (e.g., PDF, DOC, DOCX, TXT). If a user asks about a specific file type, ensure the context you are referencing corresponds to that particular file type.

6. **Comparisons Between Documents**:
   - When comparing documents or files, check the metadata for timestamps to identify the order in which the files were uploaded. Compare the contexts of the earliest and the most recent files accordingly, and use the context from the first file when necessary.

7. **Tables**:
   - If the context includes tables (e.g., markdown format), refer to them directly to answer relevant questions. Pay close attention to the structure of the table, such as column headers and row data, to provide accurate responses.
   - **For questions related to tables**:
     - Use the **columns** and **rows** in the table to extract the relevant data.
     - Ensure you address any specific data points (e.g., patient details, metrics, percentages, etc.) as per the user's query.
     - Format your responses clearly and refer to specific rows or columns in the table where necessary.
     - Accurately count and compute data from tables when the user requests quantitative information or performs mathematical operations (e.g., “How many patients?”).

### Response Formatting:

- **Use Markdown formatting** for readability and clarity:
  - `#` for main headings, `##` for subheadings, and `###` for sub-subheadings
  - **Bold text** for emphasis and key details
  - *Italic text* for subtle emphasis
  - Bullet points with `-` and numbered lists with `1. 2. 3.`
  - Code blocks with ```language for code snippets
  - Blockquotes with `>`, and tables with `|`
  
- **Ensure your answers are clearly structured** using the above formatting conventions.

### Special Handling for Queries:

- **Comparing Documents**:
  - If the user asks about **comparisons** between documents, ensure to check timestamps from the metadata to determine which document was uploaded first.
  - **Compare the contexts** of the two documents, providing insights into which one was uploaded earlier and using that context to answer the question.

- **question from metadaata**
-  When the user asks for titles of documents, list every title from the metadata of all uploaded files, even if the retrieval returns fewer documents

- **Specific Data from Tables**:
  - If the user asks about **specific data tables** (e.g., patient data, financial data, metrics), prioritize **extracting information from the table** in your response.
  - For instance, if the user asks about a patient's outcome or take rate, ensure you reference the relevant **columns** (e.g., **Take rate (%)**, **Outcome**, **Age (yr)**) and **rows** (individual patients).
  
    Example:
    - If a question asks for the **Take rate (%)** of patients, refer to the "Take rate (%)" column for relevant values.
    - If the question asks about the **outcome** for a particular age group, refer to the "Age (yr)" column to find the relevant patients and match their outcomes from the "Outcome" column.

- **General Queries**:
  - For general or non-document-related inquiries, provide helpful responses and offer assistance regarding any documents the user may need help with.

   **Relevance Verification**:
    - If no context exists, or if the context does not directly address the user's question, perform a keyword-based search within the available documents using key terms from the query.

    - If relevant information is found through this keyword search, use it to generate a detailed answer.

    - If no relevant matches are found even after the keyword-based search:

    - Instead of returning “No relevant data found”, respond with a message indicating that the document does not focus on that specific area, and summarize what the document does focus on.

    - The response should follow this structure and tone:

    **Example Response Format**:

    - The PDF you uploaded — “Dacomitinib in NSCLC: a positive trial with little clinical impact – Authors’ reply” — does not include or discuss any adverse events related to dacomitinib.

    It focuses only on:
    • CNS penetration (and lack of data in the study),
    • subgroup analysis between Asian and non-Asian populations,
    • progression-free survival (PFS) comparisons, and
    • findings regarding HER2 mutations.

    👉 No adverse event data (e.g., toxicity, side effects, safety profile, or grade of reactions) are mentioned anywhere in this correspondence
### File Type Awareness:

- **Always check the file type** (e.g., PDF, DOC, DOCX, TXT) based on the metadata.
  - If a query is about **text-based documents**, use the relevant text file for context.

### Note on Tables:
If the context includes tables in markdown format, always use the table data to answer relevant questions. Pay close attention to the **columns** and **rows** to ensure you extract accurate details.



### **Current Question**: {question}

### **Conversation History**: {history_section}

### **Retrieved Context** (USE THIS TO ANSWER DOCUMENT-RELATED QUESTIONS): {context}
"""

        # Create history section based on flag
        if include_history:
            history_section = "Conversation History:\n{history}\n"
        else:
            history_section = ""

        # Update template with dynamic history section
        template = template.replace("{history_section}", history_section)

        prompt = ChatPromptTemplate.from_template(template)

        # Create OpenAI LLM instance
        llm = ChatOpenAI(
            model=model or LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            api_key=openai_api_key,
            streaming=True
        )
        
        # Create the LLM chain with proper context injection
        llm_chain = prompt | llm

        print("-------------------------------llm_chain--------------------------------")
        print(llm_chain)
        print("-------------------------------llm_chain--------------------------------")

        print(f"🔄 Invoking LLM chain with context...")
        print(f"🔍 DEBUG: Context length: {len(context_text)} characters")
        print(f"🔍 DEBUG: Context preview (first 500 chars): {context_text[:500]}")
        print(f"🔍 DEBUG: Question: {latest_question}")
        print(f"🔍 DEBUG: History length: {len(history_text)} characters")
        
        # Debug: Check if context is empty
        if not context_text.strip():
            print("⚠️ WARNING: Context is empty!")
            context_text = "No context retrieved from documents."
        else:
            print(f"✅ Context contains {len(context_text)} characters of retrieved content")
        
        result = llm_chain.invoke({
            "history": history_text,
            "context": context_text,
            "question": latest_question
        })
        print(f"✅ LLM chain completed successfully")
        print(f"🔍 DEBUG: LLM response preview: {result.content[:200]}...")
        
        return {"messages": [AIMessage(content=result.content)]}
        
    except Exception as e:
        print(f"❌ Error in response_node: {e}")
        import traceback
        traceback.print_exc()
        error_message = f"Sorry, I encountered an error while processing your question: {str(e)}"
        return {"messages": [AIMessage(content=error_message)]}

def get_unified_pinecone_vector_store(pdf_ids: List[str], embeddings, user_id: str = None):
    """
    Create a unified Pinecone vector store for specific PDFs with user isolation
    
    Args:
        pdf_ids: List of PDF IDs to include in the unified store
        embeddings: Embeddings model to use
        user_id: User ID for access control (required for security)
    """
    try:
        print(f"🌲 Creating unified Pinecone vector store for {len(pdf_ids)} PDFs, User ID: {user_id}")
        print(f"🔒 Thread isolation: PDFs restricted to: {pdf_ids}")
        
        if not user_id:
            print("❌ ERROR: user_id is required for secure Pinecone access")
            return None
        
        # Import Pinecone components
        try:
            from langchain_pinecone import PineconeVectorStore
        except ImportError:
            print("❌ langchain-pinecone not available")
            return None
        
        # Get Pinecone configuration
        from config.settings import get_pinecone_api_key, get_pinecone_environment, get_pinecone_index_name
        api_key = get_pinecone_api_key()
        environment = get_pinecone_environment()
        index_name = get_pinecone_index_name()
        
        print(f"🔑 Using Pinecone index: {index_name}")
        
        # Set environment variable for Pinecone client
        import os
        os.environ["PINECONE_API_KEY"] = api_key
        
        # Create Pinecone vector store
        # Note: API key should be set as PINECONE_API_KEY environment variable
        vector_store = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings
        )
        
        # Create a custom retriever that enforces user isolation
        class UserIsolatedRetriever:
            def __init__(self, vector_store, user_id, pdf_ids):
                self.vector_store = vector_store
                self.user_id = user_id
                self.pdf_ids = pdf_ids
            
            def get_relevant_documents(self, query: str):
                """Get documents with user isolation enforced"""
                try:
                    # CRITICAL: If no PDFs are allowed in this thread, return empty immediately
                    if not self.pdf_ids or len(self.pdf_ids) == 0:
                        print(f"🚫 Thread isolation: No PDFs allowed for User {self.user_id}, returning empty results")
                        return []
                    
                    print(f"🔍 Searching Pinecone with user isolation - User: {self.user_id}, PDFs: {self.pdf_ids}")
                    
                    # Filter by user_id AND pdf_ids for complete isolation
                    results = self.vector_store.similarity_search(
                        query, 
                        k=10,
                        filter={
                            "user_id": self.user_id,
                            "pdf_id": {"$in": self.pdf_ids}
                        }
                    )
                    print(f"✅ Retrieved {len(results)} documents with user isolation for User {self.user_id}")
                    
                    # Double-check results contain only allowed PDFs (defensive programming)
                    if results:
                        filtered_results = []
                        for doc in results:
                            doc_pdf_id = doc.metadata.get('pdf_id')
                            if doc_pdf_id in self.pdf_ids:
                                filtered_results.append(doc)
                            else:
                                print(f"⚠️ SECURITY WARNING: Filtered out document from unauthorized PDF {doc_pdf_id}")
                        results = filtered_results
                        print(f"🔒 Final filtered results: {len(results)} documents")
                    
                    return results
                except Exception as e:
                    print(f"❌ Error in user-isolated retrieval: {e}")
                    return []
            
            def as_retriever(self):
                return self
        
        # Return the user-isolated retriever
        isolated_retriever = UserIsolatedRetriever(vector_store, user_id, pdf_ids)
        print(f"✅ Successfully created unified Pinecone vector store with user isolation")
        return isolated_retriever
        
    except Exception as e:
        print(f"❌ Error creating unified Pinecone vector store: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_unified_faiss_vector_store(pdf_ids: List[str], embeddings):
    """
    Create a unified FAISS vector store from specific PDF vector databases
    
    Args:
        pdf_ids: List of PDF IDs to include in the unified store
        embeddings: Embeddings model to use
    """
    try:
        print(f"🔍 Creating unified FAISS vector store for {len(pdf_ids)} PDFs")
        print(f"🔒 Thread isolation: PDFs restricted to: {pdf_ids}")
        vector_dbs = []
        
        # Look for vector databases for the specific PDF IDs
        for pdf_id in pdf_ids:
            vector_db_path = f"vector_db_{pdf_id}"
            if os.path.exists(vector_db_path) and os.path.isdir(vector_db_path):
                vector_dbs.append(vector_db_path)
        
        print(f"🔍 Found vector databases: {vector_dbs}")
        if not vector_dbs:
            print("🔍 No vector databases found for specified PDFs")
            return None
            
        if len(vector_dbs) == 1:
            print("🔍 Returning single vector store")
            from langchain_community.vectorstores import FAISS
            return FAISS.load_local(vector_dbs[0], embeddings, allow_dangerous_deserialization=True)
            
        all_docs = []
        from langchain_community.vectorstores import FAISS
        for db_path in vector_dbs:
            try:
                store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
                if hasattr(store, 'docstore') and store.docstore:
                    for doc_id, doc in store.docstore._dict.items():
                        all_docs.append(doc)
            except Exception as e:
                print(f"⚠️ Could not load {db_path}: {e}")
                
        if all_docs:
            unified_store = FAISS.from_documents(all_docs, embeddings)
            print("✅ Successfully created unified FAISS vector store")
            return unified_store
            
        return None
    except Exception as e:
        print(f"❌ Error creating unified FAISS vector store: {e}")
        return None

def create_chat_workflow(org_id: str, project_id: str, user_id: str = None, model: str = None, context: str = None, openai_api_key: str = None, include_history: bool = True):
    """
    Create a LangGraph workflow for processing pre-retrieved context
    No longer performs retrieval - relies on pre-provided context from the endpoint
    """
    workflow = StateGraph(RagState)
    workflow.add_node("response", lambda state: response_node(state, org_id, project_id, model, context, openai_api_key, include_history))
    workflow.add_edge(START, "response")
    workflow.add_edge("response", END)
    
    return workflow.compile(checkpointer=checkpointer)

def create_unified_chat_workflow(org_id: str, project_id: str, model: str = None, context: str = None, openai_api_key: str = None, include_history: bool = True):
    """
    Create a LangGraph workflow for processing pre-retrieved context
    No longer performs retrieval - relies on pre-provided context from the endpoint
    """
    workflow = StateGraph(RagState)
    workflow.add_node("response", lambda state: response_node(state, org_id, project_id, model, context, openai_api_key, include_history))
    workflow.add_edge(START, "response")
    workflow.add_edge("response", END)
    
    return workflow.compile(checkpointer=checkpointer)

def llm_only_response_node(state: RagState, include_history: bool = True):
    """
    LangGraph response node for pure LLM chat (no PDF context)
    """
    try:
        print(f"🤖 Processing LLM-only chat request (no PDF context)")
        
        # Get the latest question
        latest_question = state["messages"][-1].content
        print(f"📝 Processing question: {latest_question}")
        
        # Format conversation history (excluding current question) - only if history is enabled
        if include_history and len(state["messages"]) > 1:
            history_text = format_history(state["messages"])
            print(f"📚 HISTORY PREVIEW (include_history=True):")
            print(f"📚 History length: {len(history_text)} characters")
            print(f"📚 History preview (last 300 chars): ...{history_text[-300:]}")
        else:
            history_text = "No previous conversation."  # or "" if you want empty history
            print(f"📚 HISTORY PREVIEW (include_history=False): No conversation history will be sent to LLM")
        
        # Simple template for pure LLM chat with context about thread state
        template = """You are a helpful assistant. Answer the user's question based on your knowledge and the conversation history.

        IMPORTANT CONTEXT: This conversation currently has no documents or PDFs uploaded to it. You should respond based on your general knowledge, not on any specific documents. If the user asks about PDFs or documents they think they uploaded, politely let them know that you don't see any documents in this conversation thread and suggest they either upload documents or check if they're in the correct conversation thread.
                
        **Relevance Verification**:
            - If no context exists, or if the context does not directly address the user's question, perform a keyword-based search within the available documents using key terms from the query.

            - If relevant information is found through this keyword search, use it to generate a detailed answer.

            - If no relevant matches are found even after the keyword-based search:

            - Instead of returning “No relevant data found”, respond with a message indicating that the document does not focus on that specific area, and summarize what the document does focus on.

            - The response should follow this structure and tone:

            **Example Response Format**:

            - The PDF you uploaded — “Dacomitinib in NSCLC: a positive trial with little clinical impact – Authors’ reply” — does not include or discuss any adverse events related to dacomitinib.
                **FORMAT YOUR RESPONSE IN MARKDOWN** - Use headers, lists, code blocks, bold text, etc. for better readability.
        
        **MARKDOWN FORMATTING GUIDELINES:**
        - Use # for main headings, ## for subheadings, ### for sub-subheadings
        - Use **bold text** for emphasis and important points
        - Use *italic text* for subtle emphasis
        - Use - for bullet points and 1. 2. 3. for numbered lists
        - Use `inline code` for code snippets and ```language for code blocks
        - Use > for blockquotes and important notes
        - Use | for tables when presenting structured data
        - Use [link text](url) for links when relevant
        {history_section}
        
        Current Question: {question}
        
        Answer in **MARKDOWN FORMAT**:"""

        # Create history section based on flag
        if include_history:
            history_section = "Conversation History:\n{history}\n"
        else:
            history_section = ""

        # Update template with dynamic history section
        template = template.replace("{history_section}", history_section)

        prompt = ChatPromptTemplate.from_template(template)
        
        # Create LLM instance with default settings
        llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            api_key=get_OPENAI_API_KEY(),
        )
        
        llm_chain = (
            {
                "history": lambda _: history_text,
                "question": lambda _: latest_question
            }
            | prompt
            | llm
        )

        print(f"🔄 Invoking LLM-only chain...")
        result = llm_chain.invoke(latest_question)
        print(f"✅ LLM-only chain completed successfully")
        
        return {"messages": [AIMessage(content=result.content)]}
        
    except Exception as e:
        print(f"❌ Error in llm_only_response_node: {e}")
        import traceback
        traceback.print_exc()
        error_message = f"Sorry, I encountered an error while processing your question: {str(e)}"
        return {"messages": [AIMessage(content=error_message)]}

def create_llm_only_chat_workflow(include_history: bool = True):
    """
    Create a LangGraph workflow for pure LLM chat (no vector retrieval)
    """
    workflow = StateGraph(RagState)
    workflow.add_node("response", lambda state: llm_only_response_node(state, include_history))
    workflow.add_edge(START, "response")
    workflow.add_edge("response", END)
    
    return workflow.compile(checkpointer=checkpointer)

def get_checkpointer():
    """Get the checkpointer instance"""
    return checkpointer

def close_connection():
    """Close the database connection"""
    if conn:
        conn.close()

# Convenience function for easy integration with your existing API
def create_llm_workflow(org_id: str, project_id: str, user_id: str = None, unified: bool = False, model: str = None, context: str = None, openai_api_key: str = None, include_history: str = "False"):
    if include_history == "True":
        include_history = True
    else:
        include_history = False
    """
    Create a pure LLM workflow for processing pre-retrieved context
    
    Args:
        org_id: Organization ID (for logging/identification)
        project_id: Project ID (for logging/identification)  
        user_id: Optional user ID (for logging/identification)
        unified: If True, creates unified workflow for all documents
                If False, creates standard workflow
        model: LLM model name
        context: Pre-retrieved context to process (required)
        openai_api_key: OpenAI API key for LLM processing
        include_history: Whether to include conversation history (default: False)
    
    Returns:
        Compiled LangGraph workflow ready for use
    """
    if unified:
        return create_unified_chat_workflow(org_id, project_id, model, context, openai_api_key, include_history)
    else:
        return create_chat_workflow(org_id, project_id, user_id, model, context, openai_api_key, include_history)

