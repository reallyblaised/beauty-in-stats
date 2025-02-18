import torch
from transformers import AutoTokenizer, ModernBertModel
from tqdm import tqdm
import numpy as np
from typing import Union
from data_processor import DataProcessor
import os

# Set tokenizer parallelism explicitly
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EncoderModel:
    """Model loading, tokenisatuionn, and inference."""

    def __init__(
        self,
        model_name: str = "answerdotai/ModernBERT-base",
        device: Union[str, None] = None,
    ) -> None:
        """Initialize the model."""
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = ModernBertModel.from_pretrained(model_name).to(self.device)
        assert (
            self.model.device.type == self.device.type
        ), f"Model is on {self.model.device.type}, but expected {self.device.type}."

    def encode(self, texts: list[str], batch_size: int = 1) -> torch.Tensor:
        """Get embeddings for a list of texts."""
        embeddings = []

        # Process texts in full-batch mode
        self.model.eval()
        for i in tqdm(range(0, len(texts), batch_size), desc="Processing batches"):
            batch_text = texts[i : i + min(batch_size, len(texts))]

            # Tokenize and encode the batch
            inputs = self.tokenizer(batch_text, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

                # Fetch the [CLS] representation in the last embedding layer - following BERT
                cls_batch_embeddings = outputs.last_hidden_state[:, 0, :]
                embeddings.append(cls_batch_embeddings.cpu())

        return torch.cat(embeddings, dim=0)


if __name__ == "__main__":

    # load the dataset and one-hot encode the labels
    lhcb_abstract_dataset, abstract_labels = DataProcessor.load_and_process_data(
        "/ceph/submit/data/user/b/blaised/lhcb_corpus/lhcb_papers.pkl"
    )

    # get the abstract corpus
    abstract_corpus = lhcb_abstract_dataset["abstract"].tolist()
    print(f"Loaded {len(abstract_corpus)} abstracts.")

    # embed
    model = EncoderModel(device="cuda:1")
    encoded_corpus = model.encode(abstract_corpus)
    print(encoded_corpus.shape)
