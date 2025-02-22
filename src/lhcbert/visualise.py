import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
import numpy as np
import umap.umap_ as umap


class Visualizer:
    """Handles visualization of embeddings and metrics"""

    @staticmethod
    def plot_embeddings(
        embeddings, labels, method="pca", save_path=None, fig_size=(12, 8)
    ):
        """Plot embeddings using PCA or UMAP"""
        plt.figure(figsize=fig_size)

        reducer = (
            PCA(n_components=2)
            if method.lower() == "pca"
            else umap.UMAP(random_state=42)
        )
        reduced_embeddings = reducer.fit_transform(embeddings)

        unique_labels = np.unique(labels)
        colors = sns.color_palette("husl", n_colors=len(unique_labels))

        for i, label in enumerate(unique_labels):
            mask = labels == label
            plt.scatter(
                reduced_embeddings[mask, 0],
                reduced_embeddings[mask, 1],
                c=[colors[i]],
                label=label,
                alpha=0.6,
            )

        plt.title(f"LHCb Abstracts Embeddings ({method.upper()})")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)
        plt.show()
