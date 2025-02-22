from metrics import MetricsCalculator
from encoder import EncoderModel
from data_processor import DataProcessor
import numpy as np


def run_evaluation():
    # Load data
    print("Loading data...")
    lhcb_abstract_dataset = DataProcessor.load_and_process_data(
        "/ceph/submit/data/user/b/blaised/lhcb_corpus/lhcb_papers.pkl"
    )

    # .dropna()  # remove unassigned papers

    abstract_corpus = lhcb_abstract_dataset["abstract"].tolist()
    working_groups = lhcb_abstract_dataset["working_groups"].tolist()
    abstract_labels = lhcb_abstract_dataset["encoded_wg"].tolist()

    print(f"Loaded {len(abstract_corpus)} abstracts")

    # Initialize model and get embeddings
    print("Generating embeddings...")
    model = EncoderModel(
        # model_name="/ceph/submit/data/user/b/blaised/mlm_output/final_model",
        model_name="answerdotai/ModernBERT-large",
        device="cuda:0",
    )
    embeddings = model.encode(abstract_corpus)
    embeddings_np = embeddings.numpy()

    # Initialize metrics calculator
    metrics_calc = MetricsCalculator()

    # 1. Compute clustering metrics
    print("\nComputing clustering metrics...")
    clustering_results = metrics_calc.compute_clustering_metrics(
        embeddings=embeddings_np, labels=abstract_labels
    )
    print(f"V-score: {clustering_results['v_score']:.3f}")
    print(f"NMI score: {clustering_results['nmi_score']:.3f}")

    # 2. Compute group metrics
    print("\nComputing group metrics...")
    group_metrics = metrics_calc.compute_group_metrics(
        embeddings=embeddings_np, groups=working_groups
    )

    print("\nGroup statistics:")
    for group, metrics in group_metrics.items():
        print(f"\nGroup: {group}")
        print(f"Count: {metrics['count']}")
        print(f"Average similarity: {metrics['avg_similarity']:.3f}")

    # 3. Simple retrieval test - using first 100 abstracts as queries
    print("\nComputing retrieval metrics...")
    n_queries = 100
    query_embeddings = embeddings_np[:n_queries]
    doc_embeddings = embeddings_np[n_queries:]

    # For this example, let's consider documents from the same working group as relevant
    relevant_docs = []
    for i in range(n_queries):
        query_group = working_groups[i]
        rel_docs = [
            j
            for j, group in enumerate(working_groups[n_queries:])
            if group == query_group
        ]
        relevant_docs.append(rel_docs)

    ndcg = metrics_calc.compute_retrieval_metrics(
        query_embeddings=query_embeddings,
        doc_embeddings=doc_embeddings,
        relevant_docs=relevant_docs,
    )
    print(f"nDCG@10: {ndcg:.3f}")


if __name__ == "__main__":
    run_evaluation()
