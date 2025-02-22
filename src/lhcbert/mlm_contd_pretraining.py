import torch
from transformers import (
    AutoTokenizer,
    AutoModelForMaskedLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset
import numpy as np
from typing import List
from data_processor import DataProcessor


class MLMTrainer:
    def __init__(
        self,
        model_name: str = "answerdotai/ModernBERT-base",
        output_dir: str = "/ceph/submit/data/user/b/blaised/mlm_output",
        cache_dir: str = "/ceph/submit/data/user/b/blaised/cache",
    ):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_dir = cache_dir
        self.output_dir = output_dir

        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir=self.cache_dir
        )

        # Initialize model with Flash Attention 2 disabled
        if self.device == "cuda":
            self.model = AutoModelForMaskedLM.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                torch_dtype="auto",
                attn_implementation="flash_attention_2",
                reference_compile=False,
            ).to(f"cuda:{torch.cuda.current_device()}")
        else:
            self.model = AutoModelForMaskedLM.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                reference_compile=False,
            )

    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Dataset = None,
        num_train_epochs: int = 3,
        per_device_train_batch_size: int = 4,
        gradient_accumulation_steps: int = 4,
        learning_rate: float = 2e-5,
        weight_decay: float = 0.01,
    ):
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            logging_steps=100,
            save_strategy="epoch",
            eval_strategy="epoch" if eval_dataset else "no",
        )

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer, mlm=True, mlm_probability=0.15
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )

        trainer.train()
        trainer.save_model(f"{self.output_dir}/final_model")
        self.tokenizer.save_pretrained(f"{self.output_dir}/final_model")
        return trainer


if __name__ == "__main__":
    # ------------------------------------------------------------
    # 1) Load data and prepare texts
    # ------------------------------------------------------------
    data = DataProcessor.load_and_process_data(
        "/ceph/submit/data/user/b/blaised/lhcb_corpus/lhcb_papers.pkl"
    )
    texts = data["abstract"].tolist()

    # Train/eval split
    np.random.seed(42)
    eval_size = int(len(texts) * 0.1)
    eval_indices = np.random.choice(len(texts), eval_size, replace=False)
    train_indices = [i for i in range(len(texts)) if i not in eval_indices]

    train_texts = [texts[i] for i in train_indices]
    eval_texts = [texts[i] for i in eval_indices]

    # ------------------------------------------------------------
    # 2) Initialize trainer and get tokenizer
    # ------------------------------------------------------------
    mlm_trainer = MLMTrainer()
    tokenizer = mlm_trainer.tokenizer  # Get reference to tokenizer

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding=False,  # ModernBERT unpadded usage
            truncation=False,
            return_special_tokens_mask=True,
        )

    # ------------------------------------------------------------
    # 3) Prepare and tokenize datasets
    # ------------------------------------------------------------
    # Create datasets
    train_dataset = Dataset.from_dict({"text": train_texts})
    eval_dataset = Dataset.from_dict({"text": eval_texts})

    # Tokenize using multiple processes
    train_dataset = train_dataset.map(
        tokenize_function,
        batched=True,
        num_proc=4,
        remove_columns=["text"],
    )
    eval_dataset = eval_dataset.map(
        tokenize_function,
        batched=True,
        num_proc=4,
        remove_columns=["text"],
    )

    # ------------------------------------------------------------
    # 4) Train the model
    # ------------------------------------------------------------
    mlm_trainer.train(
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=4,
    )
