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