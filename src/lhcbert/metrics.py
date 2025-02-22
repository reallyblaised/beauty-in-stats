# metrics.py
from sklearn.metrics import v_measure_score, normalized_mutual_info_score
from sklearn.cluster import KMeans
import numpy as np


class MetricsCalculator:
    """Handles computation of evaluation metrics"""

    @staticmethod
    def compute_clustering_metrics(embeddings, labels, n_clusters=None):
        """Compute clustering performance metrics"""
        if n_clusters is None:
            n_clusters = len(np.unique(labels))

        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)

        return {
            "v_score": v_measure_score(labels, cluster_labels),
            "nmi_score": normalized_mutual_info_score(labels, cluster_labels),
            "cluster_labels": cluster_labels,
        }

    @staticmethod
    def compute_retrieval_metrics(
        query_embeddings, doc_embeddings, relevant_docs, k=10
    ):
        """Compute nDCG@k for retrieval"""
        similarities = np.dot(query_embeddings, doc_embeddings.T)
        top_k_docs = np.argsort(-similarities, axis=1)[:, :k]

        ndcg_scores = []
        for i, rel_docs in enumerate(relevant_docs):
            dcg = sum(
                1 / np.log2(j + 2)
                for j, doc_idx in enumerate(top_k_docs[i])
                if doc_idx in rel_docs
            )
            idcg = sum(1 / np.log2(j + 2) for j in range(min(k, len(rel_docs))))
            ndcg = dcg / idcg if idcg > 0 else 0
            ndcg_scores.append(ndcg)

        return np.mean(ndcg_scores)

    @staticmethod
    def compute_group_metrics(embeddings, groups):
        """Compute metrics for each group"""
        # Normalize embeddings
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        group_metrics = {}
        unique_groups = set(groups)
        for group in unique_groups:
            group_mask = np.array([g == group for g in groups])
            group_embeddings = embeddings[group_mask]
            if len(group_embeddings) > 1:
                similarities = np.dot(group_embeddings, group_embeddings.T)
                avg_similarity = (np.sum(similarities) - np.trace(similarities)) / (
                    len(group_embeddings) * (len(group_embeddings) - 1)
                )
            else:
                avg_similarity = 0.0
            group_metrics[group] = {
                "count": np.sum(group_mask),
                "avg_similarity": avg_similarity,
            }
        return group_metrics
