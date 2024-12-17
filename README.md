<img src="./assets/beauty-in-stats-logo.png" alt="BeautyInStats Logo" width="1000"/>

# BeautyInStats
An explainable agentic workflow as analysis copilot for LHCb OpenData and dissemination of best-practice methods for the apt evaluation of systematic uncertainties.  

## Design document 

```mermaid
graph TD
    subgraph FT ["LLM fine-tuning"]
        Knowledge[(Corpus of LHCb Papers with adequate parsing of equations)]
        FT_node[[PEFT]]
        LLM_model[/LHCbGPT/]
        
        Knowledge --> FT_node
        FT_node --> LLM_model
    end
    
    subgraph Flow ["Agentic Workflow"]
        subgraph Bonus ["Bonus"]
                LHCbCorpus[(Embedded LHCb papers)]
                Checker{{Checker Agent}}
            end
        LHCbCorpus[(Embedded LHCb papers)]
        User[/"User Query"/]
        QueryEmbedding[Query Embedding]
        QV{{Query Validation Agent}}
        Abstracts[(Abstract vector store)]
        RP1[/Relevant abstract/]
        RP2[/Relevant abstract/]
        IP1[/Irrelevant abstract/]
        IP2[/Irrelevant abstract/]
        RAGnode{RAG}
        SS1((Semantic<br/>similarity))
        SS2((Semantic<br/>similarity))
        SS3((Semantic<br/>similarity))
        SS4((Semantic<br/>similarity))
        Summary1[Focused paper<br/>summary agent]
        Summary2[Focused paper<br/>summary agent]
        Proposer{{Proposer Agent}}
        Checker{{Checker Agent}}
        Answer[/Final Answer/]
        
        User --> QV
        QV --> QueryEmbedding
        QueryEmbedding --> Abstracts
        Abstracts -.-> SS1 -.-> IP1
        Abstracts -.-> SS2 -.-> IP2
        Abstracts --> SS3 --> RP1
        Abstracts --> SS4 --> RP2
        RP1 --> Summary1
        RP2 --> Summary2
        Summary1 --> RAGnode
        Summary2 --> RAGnode
        QueryEmbedding --> RAGnode
        RAGnode --> Proposer
        Proposer --> Checker
        LHCbCorpus -- RAG --> Checker
        Checker --> Proposer
        Proposer ==> Answer
    end
    
    %% Connect the workflows
    LLM_model -..-> Flow
    
    style FT fill:#f0f0f0,stroke:#333,stroke-width:0px
    style FT_node fill:#f9fbe7,stroke:#827717
    style Flow fill:#f0f0f0,stroke:#333,stroke-width:0px
    style Knowledge fill:#e1f5fe,stroke:#01579b
    style LLM_model fill:#fff3e0,stroke:#e65100
    style Proposer fill:#fff3e0,stroke:#e65100
    style Checker fill:#fff3e0,stroke:#e65100
    style LHCbCorpus fill:#e1f5fe,stroke:#01579b
    style Abstracts fill:#e1f5fe,stroke:#01579b
    style IP1 fill:#ffebee,stroke:#c62828
    style IP2 fill:#ffebee,stroke:#c62828
    style RP1 fill:#e8f5e9,stroke:#2e7d32
    style RP2 fill:#e8f5e9,stroke:#2e7d32
    style RAGnode fill:#f3e5f5,stroke:#6a1b9a
    style Summary1 fill:#e0f2f1,stroke:#00695c
    style Summary2 fill:#e0f2f1,stroke:#00695c
    style SS1 fill:#eceff1,stroke:#455a64
     style SS2 fill:#eceff1,stroke:#455a64
      style SS3 fill:#eceff1,stroke:#455a64
       style SS4 fill:#eceff1,stroke:#455a64

    style QV fill:#fff3e0,stroke:#e65100
     style Bonus fill:none,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5
```

### Architecture Details

#### Foundation Model Stage
- LLama foundation model as base architecture
- LHCb paper corpus curated to maintain apt embedding of text and equations
- PEFT-based domain adaptation (LoRA)
- Creates LHCbGPT: physics-aware LLM enabling the agentic workflow

#### User Query

- User query embedding 
- Validation agent: converts free-form physics queries into structured query cards following a fixed schema 
- Error handling for malformed queries

#### RAG System
- Abstracts are expert-compiled summaries
- Thus, semantic similarity between the validated query and the abstract enables the identification of papers most relevant to the user query
- For each identified paper, a _focused summary_ is generated from the entire paper, honing into the aspects most relevant to the user query
- RAG across all such summaries, to provide focus, and interpretability by way of keeping track of the references used to generate the final answer
- _NOTE_: this setup is likely achievable by graph-based RAG systems (under investigation)

#### Agentic Feeback

- Proposer Agent synthesizes solution from focused summaries
- [Optional] Checker Agent validates proposals against LHCb corpus and provides interaction for further refinement


### Technical Details
- `LangGraph` for orchestration
- `LLamaIndex` for traditional RAG
- `HuggingFace` for embedding, fine-tuning, and model sourcing. 
- ...

### Useful References

- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130)
- [Language agents achieve superhuman synthesis of scientific knowledge](https://arxiv.org/abs/2409.13740)
- [PACuna: Automated Fine-Tuning of Language Models
for Particle Accelerators](https://arxiv.org/pdf/2310.19106v3)
- [AI Engineering](https://www.oreilly.com/library/view/ai-engineering/9781098166298/)
- [PhysBERT: A Text Embedding Model for Physics Scientific Literature](https://arxiv.org/pdf/2408.09574v1)

### Potentially Helpful Tutorials 

- [Building a GraphRAG Agent With Neo4j and Milvus](https://neo4j.com/developer-blog/graphrag-agent-neo4j-milvus/)
- [Fine-Tuning Open-Source LLM using QLoRA with MLflow and PEFT](https://mlflow.org/docs/latest/llms/transformers/tutorials/fine-tuning/transformers-peft.html)