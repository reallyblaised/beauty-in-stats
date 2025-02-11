import numpy as np
import os
import time

from paper_tree import PaperTree

import chromadb
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker

model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cuda")
reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True, device="cuda")

### Tree RAG Method 0: Base RAG
class BaseRAG:

    def __init__(self, papers):
        self.unique_id = str(int(10000 * time.time()) % 2**16)

        self.papers = papers
        self.chunks = []
        self.ids = []
        for id in papers:
            paper = papers[id]
            self.add_paper(paper)

        self.client = chromadb.EphemeralClient()
        self.build_collection()

    def __del__(self):
        collections = self.client.list_collections()
        for collection in collections:
            if self.unique_id in collection:
                self.client.delete_collection(collection)

    def add_paper(self, paper):
        if len(paper.sections) == 0:
            self.chunks.append(f"{paper._id_str()} \n {paper.abstract}")
            self.ids.append(paper._id_str())
        for section in paper.sections:
            self.add_paper(section)

    def build_collection(self):
        collection = self.client.get_or_create_collection(name = f"base-rag-{self.unique_id}" , metadata = {"hnsw:space" : "cosine"})

        batch_size = 250
        all_embeddings = []
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i:i + batch_size]
            batch_embeddings = model.encode(batch)
            all_embeddings.append(batch_embeddings)
        embeddings = np.vstack(all_embeddings)

        collection.add(
            embeddings=embeddings,
            documents=self.chunks,
            ids=self.ids,
        )
        self.collection = collection

    def query(self, query, n_results):
        query_embedding = model.encode(query)

        results = self.collection.query(
            query_embeddings = [query_embedding],
            n_results = n_results,
        )

        result_ids = results["ids"][0]
        result_docs = results["documents"][0]

        final_results = []
        for i in range(len(result_docs)):
            final_results.append((result_ids[i], result_docs[i]))

        return final_results
    
### Tree RAG Method 0.1: Base RAG + Reranker
class BaseRerankRAG:

    def __init__(self, papers):
        self.unique_id = str(int(10000 * time.time()) % 2**16)

        self.papers = papers
        self.chunks = []
        self.ids = []
        for id in papers:
            paper = papers[id]
            self.add_paper(paper)

        self.client = chromadb.EphemeralClient()
        self.build_collection()

    def __del__(self):
        collections = self.client.list_collections()
        for collection in collections:
            if self.unique_id in collection:
                self.client.delete_collection(collection)

    def add_paper(self, paper):
        if len(paper.sections) == 0:
            self.chunks.append(f"{paper._id_str()} \n {paper.abstract}")
            self.ids.append(paper._id_str())
        for section in paper.sections:
            self.add_paper(section)

    def build_collection(self):
        collection = self.client.get_or_create_collection(name = f"base-rag-{self.unique_id}" , metadata = {"hnsw:space" : "cosine"})

        batch_size = 250
        all_embeddings = []
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i:i + batch_size]
            batch_embeddings = model.encode(batch)
            all_embeddings.append(batch_embeddings)
        embeddings = np.vstack(all_embeddings)

        collection.add(
            embeddings=embeddings,
            documents=self.chunks,
            ids=self.ids,
        )
        self.collection = collection

    def query(self, query, n_results):
        query_embedding = model.encode(query)

        results = self.collection.query(
            query_embeddings = [query_embedding],
            n_results = 3 * n_results,
        )

        result_ids = results["ids"][0]
        result_docs = results["documents"][0]

        rankings = self.rerank(query, result_docs)
        result_ids = np.array(result_ids)[rankings][0:n_results]
        result_docs = np.array(result_docs)[rankings][0:n_results]

        final_results = []
        for i in range(len(result_docs)):
            final_results.append((result_ids[i], result_docs[i]))

        return final_results
    
    def rerank(self, query, paragraphs):
        def rank_indices(lst):
            return [i for i, _ in sorted(enumerate(lst), key=lambda x: -x[1])]
        
        rankings = reranker.compute_score([[query, paragraph] for paragraph in paragraphs], normalize = True)
        return rank_indices(rankings)

### Tree RAG Method 1: Level Search
class LevelSearchRAG:

    def __init__(self, papers):
        self.unique_id = str(int(10000 * time.time()) % 2**16)

        self.papers = papers
        self.id_to_paper = {}
        self.level_zero = []
        for id in papers:
            paper = papers[id]
            self.add_paper(paper)

        self.client = chromadb.EphemeralClient()
        self.build_collection()

    def __del__(self):
        collections = self.client.list_collections()
        for collection in collections:
            if self.unique_id in collection:
                self.client.delete_collection(collection)

    def add_paper(self, paper):
        if paper.abstract is not None:
            id = paper._id_str()
            self.id_to_paper[id] = paper
            if paper.get_depth() == 0:
                self.level_zero.append(id)
        for section in paper.sections:
            self.add_paper(section)

    def build_collection(self):
        self.collection = self.client.get_or_create_collection(name = f"level-rag-{self.unique_id}" , metadata = {"hnsw:space" : "cosine"})

        ids = list(self.id_to_paper.keys())
        chunks = []
        for id in ids:
            paper = self.id_to_paper[id]
            chunks.append(f"{paper._id_str()} \n {paper.abstract}")

        batch_size = 250
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = model.encode(batch)
            all_embeddings.append(batch_embeddings)
        embeddings = np.vstack(all_embeddings)

        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"id" : id} for id in ids],
            ids=ids,
        )

    def query(self, query, n_results):
        query_embedding = model.encode(query)
        focus_ids = list(self.level_zero)
        final_results = []
        while len(focus_ids) > 0 and len(final_results) < n_results:
            result = self.collection.query(
                query_embeddings = [query_embedding],
                n_results = n_results,
                where = {"id" : {"$in" : focus_ids}}
            )
            if len(result) == 0:
                break

            best_id = result['ids'][0][0]
            best_document = result['documents'][0][0]
            best_paper = self.id_to_paper[best_id]

            focus_ids.remove(best_id)
            if len(best_paper.sections) > 0:
                for section in best_paper.sections:
                    focus_ids.append(section._id_str())
            else:
                final_results.append((best_id, best_document))

        return final_results


### Tree RAG Method 2: Level Search with Reranker
class LevelSearchRerankRAG:

    def __init__(self, papers):
        self.unique_id = str(int(10000 * time.time()) % 2**16)

        self.papers = papers
        self.id_to_paper = {}
        self.level_zero = []
        for id in papers:
            paper = papers[id]
            self.add_paper(paper)

        self.client = chromadb.EphemeralClient()
        self.build_collection()

    def __del__(self):
        collections = self.client.list_collections()
        for collection in collections:
            if self.unique_id in collection:
                self.client.delete_collection(collection)

    def add_paper(self, paper):
        if paper.abstract is not None:
            id = paper._id_str()
            self.id_to_paper[id] = paper
            if paper.get_depth() == 0:
                self.level_zero.append(id)
        for section in paper.sections:
            self.add_paper(section)

    def build_collection(self):
        self.collection = self.client.get_or_create_collection(name = f"level-rag-{self.unique_id}" , metadata = {"hnsw:space" : "cosine"})

        ids = list(self.id_to_paper.keys())
        chunks = []
        for id in ids:
            paper = self.id_to_paper[id]
            chunks.append(f"{paper._id_str()} \n {paper.abstract}")

        batch_size = 250
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = model.encode(batch)
            all_embeddings.append(batch_embeddings)
        embeddings = np.vstack(all_embeddings)

        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"id" : id} for id in ids],
            ids=ids,
        )

    def query(self, query, n_results):
        query_embedding = model.encode(query)
        focus_ids = list(self.level_zero)
        final_results = []
        id_to_relevance = {}
        while len(focus_ids) > 0 and len(final_results) < n_results:
            result = self.collection.query(
                query_embeddings = [query_embedding],
                n_results = 15,
                where = {"id" : {"$in" : focus_ids}}
            )
            if len(result) == 0:
                break

            ids = result['ids'][0]
            documents = result['documents'][0]
            needs_relevance_ids = []
            needs_relevance_chunks = []
            for id, document in zip(ids, documents):
                if id not in id_to_relevance.keys():
                    needs_relevance_ids.append(id)
                    paper = self.id_to_paper[id]
                    needs_relevance_chunks.append(f"{paper._id_str()} \n {paper.abstract}")
        
            for id, relevance in zip(needs_relevance_ids, self.llm_reranker(query, needs_relevance_chunks)):
                id_to_relevance[id] = relevance

            best_id = max(id_to_relevance, key=id_to_relevance.get)
            best_paper = self.id_to_paper[best_id]
            best_document = f"{best_paper._id_str()} \n {best_paper.abstract}"

            focus_ids.remove(best_id)
            id_to_relevance.pop(best_id)

            if len(best_paper.sections) > 0:
                for section in best_paper.sections:
                    focus_ids.append(section._id_str())
            else:
                final_results.append((best_id, best_document))

        return final_results

    def llm_reranker(self, query, paragraphs):
        if len(paragraphs) == 0:
            return []
        relevances = reranker.compute_score([[query, paragraph] for paragraph in paragraphs], normalize = True)
        return relevances