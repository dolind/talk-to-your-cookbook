## Architecture

The system implements a retrieval-augmented generation pipeline
to answer recipe-related questions grounded in real user data.

## Pipeline Overview

Start by index all Recipes from the Chat Screen.

1. User query is embedded to vector space  
2. Semantic search (pgvector cosine similarity) finds top-K matching chunks  
3. Retrieved evidence is included in the LLM prompt  
4. Model produces a grounded answer

This reduces hallucinations and increases factual accuracy.

A **mock chatbot** mode outputs only retrieved chunks
It can be activated by setting `LLM_API_PROVIDER=mock` in config or ENV file.

Advanced techniques exist privately for future commercialization.

## Architecture Diagram
The chat app uses `langgraph` as backend technology.

This is the current layout of the graph.
```mermaid
{!diagrams/graphs/chat_app.mmd !}
```
## Evaluation
Public evaluation is planned.

## Interaction surfaces in the legacy UI

RAG capabilities integrate into the existing recipe management UX:

- From a recipe detail page, the user can launch a chat pre-loaded with relevant context.
- From the global search/chat interface, the user can request similar recipes and navigate back into the structured content.

UI exists only as a demonstration context for intelligent workflows.