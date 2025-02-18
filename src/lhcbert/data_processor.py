# data_processor.py
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from pathlib import Path
from typing import Tuple

class DataProcessor:
    """Handles data loading and preprocessing"""
    @staticmethod
    def load_and_process_data(csv_path: Path) -> Tuple[pd.DataFrame, LabelEncoder]:
        """Load and preprocess LHCb data"""
        df = pd.read_pickle(csv_path) if csv_path.endswith('.pkl') else pd.read_csv(csv_path)

        # Explode to handle multiple WGs per paper
        df = df.explode('working_groups')

        # Remove leading/trailing whitespace
        df['working_groups'] = df['working_groups'].str.strip()

        # Encode labels
        label_encoder = LabelEncoder()
        df['encoded_wg'] = label_encoder.fit_transform(df['working_groups'])

        return df, label_encoder