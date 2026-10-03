

from backend.core.langgraph_workflow import create_llm_workflow
import json
from langchain_core.messages import HumanMessage
from backend.crud import get_current_api_key
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException
from utils.get_api_key import get_key
from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService
from backend.database import get_db
from langchain_core.messages import HumanMessage, SystemMessage
from backend.database import get_db


#HTTPException
from fastapi import HTTPException
from fastapi import APIRouter, Depends, HTTPException
from fastapi import HTTPException, APIRouter, Depends
from services.service_factory import create_services_from_auth, get_namespace_from_auth

from backend.crud import (
    get_user_by_id, get_user_by_email, get_user_by_username, create_user, get_user_info,
    check_pdf_exists, get_existing_pdf_data, save_pdf_to_db, validate_user_pdf,
    get_user_pdfs, filter_unprocessed_pdf_ids, mark_pdfs_as_processed,
    get_pdf_info, update_pdf_llm_processed_flag, delete_pdf,
    create_thread_id, save_thread_to_db, update_thread_title, get_thread_by_id,
    get_user_threads, get_thread_pdfs, validate_thread_pdf_access, update_thread_pdfs,
    remove_pdf_from_thread, save_message_to_db, get_thread_messages,
    set_user_organization, get_organization_by_name, delete_user,
    get_organization_by_id, create_project, get_project_by_name_in_org,
    record_token_usage, record_aggregated_token_usage
) 

from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI





class CheckGreeting(BaseModel):
    greeting_classifier: Literal["yes", "no"] = Field(
        ...,
        description="Indicates whether the input text is classified as a greeting ('yes') or not ('no')."
    )

def check_greeting(text: str, openai_api_key: str) -> CheckGreeting:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    llm_with_structured_output = llm.with_structured_output(CheckGreeting)
    return llm_with_structured_output.invoke(text)

router = APIRouter()

def format_context_for_langgraph(context_list):
    """
    Format the context list from query.py to match the format expected by LangGraph workflow
    """
    if not context_list:
        return ""
    
    formatted_parts = []
    for item in context_list:
        text = item.get("text", "")
        metadata = item.get("metadata", {})
        
        # Format metadata as key-value pairs
        metadata_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() if v is not None)
        
        # Create formatted document
        formatted_doc = f"Content:\n{text}\n\nMetadata:\n{metadata_str}"
        formatted_parts.append(formatted_doc)
    
    # Join with separator
    return "\n\n---\n\n".join(formatted_parts)
import numpy as np

def clean_numpy(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, np.generic):
        return obj.item()

    if isinstance(obj, (list, tuple)):
        return [clean_numpy(x) for x in obj]

    if isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}

    return obj

@router.post("/vectors/query")
async def query_vector(
    request: Dict[str, Any],
    auth=Depends(get_current_api_key)  # returns { "api_key": obj, "subscription": obj }
):
    """
    Query stored vectors for a given text within org & project namespace
    Enhanced with LangGraph workflow integration support
    
    Input:
    {
      "query_text": "search query",
      "study_id": "study_123",       # Optional: filter by specific study
      "knowledge_base_id": "kb_456", # Optional: filter by specific knowledge base
      "embedding_provider": "openai",       # Optional: "openai", "voyageai", "cohere" (default: "openai")
      "embedding_model": "text-embedding-3-small",  # Optional: specific model name (uses provider default if not specified)
      "llm_provider": "openai",             # Optional: "openai", "anthropic", "google" (default: "openai")
      "llm_model": "gpt-4o",                # Optional: specific model name (uses provider default if not specified)
      "top_k": 5,                    # Optional: number of results (default: 5)
      "thread_id": "thread_123",     # Optional: conversation context
      "history": false,              # Optional: include prior turns in LLM prompt (default: false)
      "filter_metadata": {           # Optional: custom metadata filters
        "doc.author": "John Doe",
        "doc.category": "research",
        "doc.publishedyear": {"$gte": 2020},
        "doc.priority": {"$gte": 5},
        "part.section_type": "abstract",
        "part.sentiment_score": {"$gte": 0.7}
      }
    }
    """
    try:
        query_text = request.get("query_text")
        if not query_text:
            raise HTTPException(status_code=400, detail="query_text is required")
        # Get API key early for both greeting check and potential greeting response
        api_key_obj = auth["api_key"]
        subscription = auth["subscription"]
        openai_api_key, _, _, _ = get_key(subscription)
        
        greeting_classifier = check_greeting(query_text, openai_api_key)

        print(f"DEBUG: Greeting classifier: {greeting_classifier}")
        
        # If it's a greeting, use simple LLM for casual response
        if greeting_classifier.greeting_classifier == "yes":
            # Create LLM instance with API key for this specific request
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
            
            # Create a simple prompt for greeting responses
            greeting_prompt = "You are a helpful AI assistant. Respond to greetings and casual conversation in a friendly, professional manner. Keep responses brief and welcoming."
            
            # Generate casual response with prompt
            messages = [
                SystemMessage(content=greeting_prompt),
                HumanMessage(content=query_text)
            ]
            response = llm.invoke(messages)
            response_text = response.content

            
            
            # Return simple greeting response
            return {
                "langgraph_response": response_text
            }
        
        # If not a greeting, proceed with full RAG workflow
        # Extract embedding parameters from request
        embedding_provider = request.get("embedding_provider", "openai")
        embedding_model = request.get("embedding_model", None)
        
        # Extract LLM parameters from request
        llm_provider = request.get("llm_provider", "openai")
        llm_model = request.get("llm_model", None)
        
        # Extract history flag for LLM prompt (create_llm_workflow expects "True"/"False" strings)
        _hist = request.get("history", False)
        if _hist is True or (
            isinstance(_hist, str) and _hist.strip().lower() in ("true", "1", "yes")
        ):
            include_history = "True"
        else:
            include_history = "False"

        # Validate embedding provider
        if embedding_provider not in ["openai", "voyageai", "cohere"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported embedding provider: {embedding_provider}. Supported: openai, voyageai, cohere"
            )
        
        # Validate LLM provider
        if llm_provider not in ["openai", "anthropic", "google"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported LLM provider: {llm_provider}. Supported: openai, anthropic, google"
            )

        # Get plan-specific API keys for RAG workflow
        _, pinecone_api_key, pinecone_index_name, pinecone_env = get_key(subscription)
        print(f"DEBUG: openai_api_key: {openai_api_key}, pinecone_api_key: {pinecone_api_key}, pinecone_index_name: {pinecone_index_name}, pinecone_env: {pinecone_env}")
        # Optional: conversation context
        thread_id = request.get("thread_id")
        
        # Optional: study and knowledge base filters
        study_id = request.get("study_id")
        knowledge_base_id = request.get("knowledge_base_id")
        screening_result_id = request.get("screening_result_id")
        user_id_genex=request.get("user_id")
        
        # Optional: custom metadata filters
        user_filter_metadata = request.get("filter_metadata", {})

        org_id = api_key_obj.org_id
        project_id = api_key_obj.project_id
        user_id = api_key_obj.user_id
        namespace = get_namespace_from_auth(auth)




        # 🔒 Enforce subscription query quota
        if subscription.monthly_limit_queries is not None:
            if subscription.used_queries >= subscription.monthly_limit_queries:
                raise HTTPException(status_code=402, detail="Query quota exceeded.")

        # ✨ Initialize services using factory (handles all key management automatically)
        try:
            embedding_service, pinecone_service = create_services_from_auth(
                auth=auth,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")

        query_embedding = await embedding_service.generate_embedding(query_text)

        # Combine system filters with optional user filters
        filter_metadata = {
            "org_id": org_id,
            "project_id": project_id
        }
        
        # Add study_id and knowledge_base_id filters if provided
        # if study_id:
        #     filter_metadata["study_id"] = study_id
        #     print(f"DEBUG: Added study_id filter: {study_id}")
        
        # if knowledge_base_id:
        #     filter_metadata["knowledge_base_id"] = knowledge_base_id
        #     print(f"DEBUG: Added knowledge_base_id filter: {knowledge_base_id}")

        # if screening_result_id:
        #     filter_metadata["screening_result_id"] = screening_result_id
        #     print(f"DEBUG: Added screening_result_id filter: {screening_result_id}")

        # if user_id_genex:
        #     filter_metadata["user_id_genex"] = user_id_genex
        #     print(f"DEBUG: Added user_id_genex filter: {user_id_genex}")


        
        # Add custom user metadata filters (all optional)
        if user_filter_metadata:
            # Validate and sanitize user filter metadata
            allowed_filter_fields = [
                "doc.author", "doc.category", "doc.publishedyear", "doc.priority",
                "part.section_type", "part.sentiment_score", "part.clause_type",
                "study_id", "knowledge_base_id","screening_result_id","user_id"
            ]
            
            # Fields that should be normalized to lowercase (text fields)
            text_fields_to_normalize = [
                "doc.author", 
                "doc.category", 
                "part.section_type", 
                "part.clause_type"
            ]
            
            def _normalize_filter_value(value: Any, field: str) -> Any:
                """Normalize filter values for case-insensitive matching - matches insert logic"""
                if isinstance(value, dict):
                    # Handle Pinecone operators like {"$gte": 2020}
                    return value
                elif isinstance(value, (int, float)):
                    # Keep numeric values as-is
                    return value
                elif isinstance(value, bool):
                    return str(value).lower()
                else:
                    # Convert to string first, then normalize case for text fields
                    str_value = str(value).strip()
                    if field in text_fields_to_normalize:
                        return str_value.lower()
                    return str_value
            
            for field, value in user_filter_metadata.items():
                if field in allowed_filter_fields:
                    normalized_value = _normalize_filter_value(value, field)
                    filter_metadata[field] = normalized_value
                    print(f"DEBUG: Added filter {field}: {normalized_value}")
                else:
                    print(f"WARNING: Ignored unknown filter field: {field}")
        
        results = await pinecone_service.search_similar_pdfs(
            query_embedding=query_embedding,
            filter_metadata=filter_metadata,
            top_k=request.get("top_k", 17),
            namespace=namespace
        )

        from flashrank import Ranker, RerankRequest

        # Initialize FlashRank (do this once, perhaps in your service initialization)
        # ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")  # or "rank-T5-flan" for better accuracy
        ranker = Ranker(model_name="rank-T5-flan")

        # Your existing search code
       
       # Make sure query is a string, not None or dict
        query_text = request.get("query_text", "")
        if not isinstance(query_text, str):
            query_text = str(query_text)

        # Prepare passages - just a list of dicts with "text" key
        passages = []
        metadata_map = {}

        for idx, result in enumerate(results):
            # Extract text and ensure it's a string
            text = result.get("metadata", {}).get("pdf_text", "") or result.get("text", "")
            
            # Ensure text is actually a string and not None
            if text is None:
                text = ""
            
            # Clean the text if needed
            text = str(text).strip()
            
            if text:  # Only add non-empty passages
                passages.append({
                    "text": text,
                    "id": idx
                })
                
                metadata_map[idx] = {
                    "id": result.get("id"),
                    "metadata": result.get("metadata", {}),
                    "original_score": result.get("score", 0)
                }

        # ✅ Create RerankRequest properly - pass as dict/object attributes
        from flashrank import RerankRequest

        # Try creating the request object with proper attribute setting
        rerank_req = RerankRequest(query=query_text, passages=passages)

        # OR try this if that doesn't work:
        # rerank_req = RerankRequest()
        # rerank_req.query = query_text
        # rerank_req.passages = passages

        # Get top results
        final_top_k = 5
        final_results = []

        # Call rerank with the request object
        try:
            reranked_results = ranker.rerank(rerank_req)
        except Exception as e:
            print(f"Error: {e}")
            # Alternative: try passing positional arguments
            # reranked_results = ranker.rerank(query_text, passages)
            final_top_k = 5
            reranked_results = [
                {
                    "id": idx,
                    "score": result.get("score", 0),
                    "text": result.get("metadata", {}).get("pdf_text", "") or result.get("text", "")
                }
                for idx, result in enumerate(results[:final_top_k])
            ]

        # Get top results
        final_top_k = 5
        final_results = []

        for reranked in reranked_results[:final_top_k]:
            # Get the index/id from reranked result
            idx = reranked.get("id") or reranked.get("index", 0)
            original_data = metadata_map.get(idx, {})
            
            final_results.append({
                "id": original_data.get("id"),
                "score": float(reranked["score"]),
                "metadata": original_data.get("metadata", {}),
                "text": reranked["text"]
            })





     


        context = [
            {
                "text": match["metadata"].get("pdf_text", ""),
                "metadata": {
                    "doc_id": match["metadata"].get("doc_id"),
                    "chunk_index": match["metadata"].get("chunk_index"),
                    "total_chunks": match["metadata"].get("total_chunks"),
                    "project_id": match["metadata"].get("project_id"),
                    "org_id": match["metadata"].get("org_id"),
                    "score": match.get("score"),
                    "vector_id": match.get("id"),
                    # Document metadata fields
                    "document_title": match["metadata"].get("document_title"),
                    "pdf_name": match["metadata"].get("pdf_name"),
                    "authors": match["metadata"].get("authors"),
                    "journal": match["metadata"].get("journal"),
                    "publication_date": match["metadata"].get("publication_date"),
                    "doi": match["metadata"].get("doi"),
                    # Include custom metadata fields
                    "doc.author": match["metadata"].get("doc.author"),
                    "doc.category": match["metadata"].get("doc.category"),
                    "doc.publishedyear": match["metadata"].get("doc.publishedyear"),
                    "doc.priority": match["metadata"].get("doc.priority"),
                    "part.section_type": match["metadata"].get("part.section_type"),
                    "part.sentiment_score": match["metadata"].get("part.sentiment_score"),
                    "part.clause_type": match["metadata"].get("part.clause_type"),
                    "study_id": match["metadata"].get("study_id"),
                    "knowledge_base_id": match["metadata"].get("knowledge_base_id"),
                    "screening_result_id": match["metadata"].get("screening_result_id"),
                    "user_id": match["metadata"].get("user_id"),
                    "embedding_provider": match["metadata"].get("embedding_provider"),
                    "embedding_model": match["metadata"].get("embedding_model")
                }
            }
            for match in results
        ]

        # Format context for LangGraph workflow
        formatted_context = format_context_for_langgraph(context)
        print(f"🔍 DEBUG: Formatted context length: {len(formatted_context)} characters")
        print("------------------------formatted_context---------------------")
        print(f"🔍 DEBUG: Formatted context preview:----- {formatted_context}...")
        print("------------------------formatted_context end---------------------")

        # Build workflow for response generation with pre-retrieved context
        workflow = create_llm_workflow(
            org_id=org_id,
            project_id=project_id,
            user_id=user_id,
            unified=True,
            model=llm_model,
            context=formatted_context,
            openai_api_key=openai_api_key,
            include_history=include_history
        )

        config = {"configurable": {"thread_id": thread_id}}
        response = workflow.invoke(
            {"messages": [HumanMessage(content=query_text)]},
            config=config
        )

        response_text = response["messages"][-1].content
        response_text_lower = response_text.lower().strip()

        # llm_model_used="gpt-4o-mini"

        
        # input_tokens = count_tokens_with_tiktoken(query_text,llm_model_used )
        # output_tokens = count_tokens_with_tiktoken(response_text,llm_model_used)
        # total_tokens = input_tokens + output_tokens

        # Check if LLM response indicates no relevant information found
        no_info_phrases = [
            "no relevant information found",
            "no relevant information",
            "no information found",
            "no relevant data found",
            "no relevant data",
            "no information available",
            "no relevant content found",
            "no relevant docs found",
            "no relevant documents found"
        ]

        if any(phrase in response_text_lower for phrase in no_info_phrases):
            # Return early with only the LLM response
            return {
                "langgraph_response": response_text
            }

        output_characters = len(response_text)

        print(f"DEBUG: Token counting - Query: {len(query_text)} chars, "
              f"LLM Response: {output_characters} chars, "
              f"Total: {len(query_text) + output_characters} chars")

        # ✅ Increment subscription usage
        db = next(get_db())
        subscription.used_queries += 1
        db.commit()

        # Record token usage
        try:
            total_tokens=record_token_usage(
                db=db,
                api_key_id=api_key_obj.id,
                endpoint="vectors/query",
                operation_type="query",
                input_text=query_text,
                output_text=response_text
            )
        except Exception as e:
            print(f"WARNING: Failed to record token usage: {e}")


        print("rag_token_usage",total_tokens)




        # Keep top-k reranked chunks as results
        results = final_results

        # Use an LLM to infer which document/pdf IDs are truly relevant among the top-k chunks
        relevant_ids = set()
        try:
            print("🔍 Starting LLM relevance filtering over top-k chunks...")

            system_prompt = ( 
                """
# Relevance Filter Instructions (RAG)

You are a **strict relevance filter** for Retrieval-Augmented Generation (RAG).  
Your task is to determine which document IDs (`doc_ids`) are relevant to answering the user's query.

---

## Inputs You Receive

You will be given:

1. **User Query**  
2. **Generated Response** (`langgraph_response`)  
3. **Candidate Chunks**, each containing:
   - A text chunk  
   - A numeric similarity score  
   - A `doc_id` representing the document the chunk came from  

---

## Your Objective

Identify which `doc_ids` are clearly relevant based on:

- The **user query**
- The **generated response**
- The **content of the candidate chunks**

There is **no limit** to the number of relevant `doc_ids`.  
If many documents support the answer, include all of them.

---

## Relevance Rules

A chunk should be considered **relevant** if:

- It directly contributed to the **langgraph response0**

Additional rules:

- Always evaluate:
  - The *generated response*

---

## Important:
- Please Review the langgraph_response carefully.
- Review Chunks and See which Chunks Contributed to the Response.
- Always return the doc_ids after careful evaluation.
- Return All doc_ids whose chunks are relevant to the **langgraph response**
- The Query is only for guidence. Main thing is the **langgraph response**, See the langgraph response, and return the only *doc_ids* that are relevant to the langgraph response.

---

## Output Format

Return **ONLY** a JSON object in the following exact shape (without any markdown or surrounding text):


{"relevant_ids": ["pdf_id_1", "pdf_id_2", "..."]} """




            )

            candidate_lines = []
            for r in context:
                metadata = r.get("metadata", {})
                pdf_id = metadata.get("doc_id")
                document_title = metadata.get("document_title")
                pdf_name = metadata.get("pdf_name")
                doc_author = metadata.get("doc.author")
                authors = metadata.get("authors")
                candidate_lines.append(
                    f"PDF_ID: {pdf_id}\n"
                    f"VectorID: {metadata.get('vector_id')}\n"
                    f"Score: {metadata.get('score')}\n"
                    f"Document Title: {document_title}\n"
                    f"PDF Name: {pdf_name}\n"
                    f"Doc Author: {doc_author}\n"
                    f"Authors: {authors}\n"
                    f"Text:\n{r['text']}\n"
                    "--------------------"
                )

            human_content = (
                f"User query:\n{query_text}\n\n"
                f"Generated response (langgraph_response):\n{response_text}\n\n"
                "Candidate chunks:\n\n" + "\n".join(candidate_lines)
            )
            print("Prompt for relevance filter")
            print("--------------------")
            print(system_prompt)
            print("🔍 Relevance-filter prompt content (human message) being sent to LLM:")
            print(human_content)
            print("🔍 Sending relevance-filter prompt to LLM...")

            llm_filter = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                openai_api_key=openai_api_key,
            )

            filter_response = llm_filter.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_content),
            ])

            try:
                print(f"🔍 Raw relevance-filter LLM response: {filter_response.content}")
                parsed = json.loads(filter_response.content)
                relevant_ids = set(parsed.get("relevant_ids", []))
                print(f"✅ Extracted relevant doc_ids from LLM: {relevant_ids}")
            except Exception as e:
                print(f"WARNING: Failed to parse relevance filter response: {e}")
                relevant_ids = set()

        except Exception as e:
            # If anything goes wrong with the relevance filter, fall back gracefully
            print(f"WARNING: LLM relevance filter failed: {e}")
            relevant_ids = set()

        print(f"✅ Final relevant_pdf_ids to return: {list(relevant_ids)}")

        return {
            "namespace": namespace,
            "results": results,
            "context": context,
            "langgraph_response": response_text,
            "thread_id": thread_id,
            "message_count": len(response["messages"]),
            "study_id": study_id,
            "knowledge_base_id": knowledge_base_id,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_service.model_name, 
            "total_tokens_org": total_tokens,  
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "is_greeting": False,
            "relevant_pdf_ids": list(relevant_ids)
        }





    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))