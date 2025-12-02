## Frontend

The frontend provides interfaces to interact with intelligent workflows
(OCR ingestion, retrieval search, grounded
chat). State remains primary in the backend to simplify demo usage.

```mermaid
%%{ init: { 'flowchart': { 'curve': 'stepBefore' } } }%%
flowchart TD

%% ========================
%% Frontend
%% ========================
    subgraph Frontend
        chat_ui[Chat UI]
        recipe_browser[Recipe Browser]
        recipe_detail[Recipe Details]
        plan_viewer[Meal Plan Viewer]
        shopping_list[Shopping List]
        ocr_explorer[Recipe Book OCR]
        api_client[API Client]
    end

    chat_ui --> api_client
    recipe_browser --> api_client
    recipe_detail --> api_client
    plan_viewer --> api_client
    ocr_explorer --> api_client
    shopping_list --> api_client
    backend[Backend]
    api_client -->|HTTP, WebSocket| backend

```

## Backend

I try to follow a clean architecture approach and at the same time balance this with the speed requirement of a
prototyping phase.

This has led to only a soft clean architecture structure.

The standard structure of fastapi apps makes it difficult to follow a clean architecture.

I did try to follow a more structure approach. However, doing so creates a lot of extra files, and therefore I settled
on
this slimmer structure

Components are grouped by their role in the stack; edges are omitted for clarity.

```mermaid

flowchart TB


%% --- ordering constraints (invisible) ---
    Core_Domain --> Application_Layer
    Core_Domain --> Infra_Layer
    Application_Layer --> Presentation
    Infra_Layer --> Presentation
%% --- diagram ---
    subgraph Core_Domain
        models["models (SQLAlchemy entities)"]
        schemas["schemas (Pydantic DTOs)"]
        ports["ports (interfaces for infra adapters)"]
        experimental["mocks for ports"]
        repos["repos (without ports)"]
    end

    subgraph Presentation
        main["FastAPI entrypoint"]
    end

    subgraph Application_Layer
        services["services (use-case coordination"]
        workflows["workflows (pipelines/orchestration, langgraphs)"]
        routes["routes (API & partly use-case coordination)"]
    end

    subgraph Infra_Layer
        storage
        database["database (SQL, Embeddings)"]
        infra["adapters (3rd party software)"]
    end

```