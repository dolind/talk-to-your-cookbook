
The following pipeline presents how the embeddings are created.
The embedding worker is an example for one of the background workers.
This allows smooth operation of the frontend, while the backend is busy creating the embeddings.

```mermaid
%%{
  init: {
    'flowchart': {
      'curve': 'basic'
    }
  }
}%%
flowchart TD

%% ================= CORE CONFIG =================
    subgraph Core-Settings
        Settings -->|has| TargetConfig
    end
    subgraph Presentation
        Main -->|uses| Settings

    end

%% ================= PORTS =================
    subgraph Core-Ports
        IChunker[[IChunker]]
        IEmbeddingStore[[IEmbeddingStore]]
    end

%% ================= INFRASTRUCTURE =================
    subgraph Infrastructure
        LCChunker[RecursiveChunker]
        PGVStore[PGVectorEmbeddingStore]
        StoreRegistry["build_store_registry()\n→ { target:version → PGVector }"]

    end

%% ================= WORKFLOWS =================
    subgraph Application
        subgraph Workflows-RecipeAssistant
            EmbWorker["EmbeddingWorker"]
        end
        subgraph Services
            EmbService[EmbeddingService]
        end
    end

%% ================= DEPENDENCIES =================

%% Service uses ports
    Main -->|uses| StoreRegistry
    Main -->|uses| LCChunker
    Main -->|uses| EmbService
    Main -->|start| EmbWorker
    EmbService -.->|chunks text with| IChunker
    EmbService -.->|stores recipe embeddings| IEmbeddingStore
%% Adapters implement ports
    LCChunker -->|implements| IChunker
    PGVStore -->|implements| IEmbeddingStore
%% Registry config
    StoreRegistry -->|reads target_config_list| Settings
    StoreRegistry -->|creates store instance| PGVStore
%% Worker orchestration
    EmbWorker -->|indexes recipes with| EmbService
    EmbWorker -.->|saves emb with| IEmbeddingStore

```