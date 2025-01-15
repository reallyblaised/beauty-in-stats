import gradio as gr
from abstract_analysis import OllamaClassifier
import random
import os
import glob

# Initialize classifier
classifier = OllamaClassifier(model_name="mistral")

# Brief instructions
INSTRUCTIONS = """
# AnalysisCopilot: LHCb Abstract Classifier - using the `mistral` open-source LLM

## Instructions

### Load or Enter Abstract
Execute one of the following options:

- Click the "Load Random Abstract" button to load a random LHCb paper abstract. 
- Enter your LHCb paper abstract in the text box. For best results, paste LaTeX source code of the abstract.

### Classify Abstract
Click the "Classify Abstract" button to classify the abstract based on its physics focus, run period, and analysis strategy.
"""

# Classification schema information
CLASSIFICATION_INFO = """
### Classification Categories

#### Physics Focus
- `b->sll`: Loop-suppressed beauty decays with leptons
- `radiative_decays`: Heavy-flavor decays with photons
- `spectroscopy`: Exotic multi-quark states
- `semileptonic`: B→D(*)ℓν decays with neutrinos
- `lifetime`: Heavy-flavored hadron lifetimes
- `electoweak`: W, Z, and Higgs physics
- `dark_sector`: Dark Matter/Dark-Sector searches
- `forbidden_decays`: Baryon/lepton number violation
- `jet_physics`: Jet production and QCD
- `heavy_ions`: Non-pp collision analyses
- `charm`: Charm physics and CP violation
- `CPV`: Beauty CP violation measurements

#### Run Period
- `Run1`: 2011-2012 (3 fb⁻¹, 7-8 TeV)
- `Run2`: 2015-2018 (5.4/6 fb⁻¹, 13 TeV)
- `Run1+2`: Combined datasets (~9 fb⁻¹, 13 TeV)
- `Run3`: 2022-2025 (13.6 TeV, expected ~15 fb⁻¹)

#### Analysis Strategy
- `angular_analysis`: Angular distributions and WC extraction
- `amplitude_analysis`: Decay amplitudes and resonances
- `search`: New state searches with limits
- `direct_measurement`: Observable measurements (BF, mass, etc.)
"""

def load_random_abstract():
    """Load a random abstract from the specified directory"""
    abstract_dir = "/work/submit/blaised/beauty-in-stats/data/abstracts"
    abstract_files = glob.glob(os.path.join(abstract_dir, "*.tex"))
    
    if not abstract_files:
        return "No abstract files found in directory.", ""
    
    random_file = random.choice(abstract_files)
    try:
        with open(random_file, 'r') as f:
            content = f.read()
        # Extract filename without .tex and path
        filename = os.path.basename(random_file).replace('.tex', '')
        return content, f"## arXiv ID: `{filename}`"
    except Exception as e:
        return f"Error loading abstract: {str(e)}", ""

def classify_abstract(abstract: str):
    """Classify the given abstract and return results in a formatted way"""
    result = classifier.classify_abstract(abstract)
    if result:
        return (
            result["focus"],
            result["run"],
            result["strategy"]
        )
    return "Error in classification", "Error in classification", "Error in classification"

# Create the interface
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown(INSTRUCTIONS)
            
            # Add arXiv ID display
            arxiv_id = gr.Markdown("")
            
            with gr.Row():
                abstract_input = gr.Textbox(
                    label="Enter abstract text",
                    placeholder="Paste your LHCb paper abstract here...",
                    lines=8
                )
            
            with gr.Row():
                random_btn = gr.Button("Load Random Abstract")
                classify_btn = gr.Button("Classify Abstract", variant="primary")
            
            with gr.Row():
                physics_output = gr.Textbox(label="Physics Focus")
                run_output = gr.Textbox(label="Run Period")
                strategy_output = gr.Textbox(label="Analysis Strategy")

        with gr.Column(scale=1):
            gr.Markdown(CLASSIFICATION_INFO)
    
    random_btn.click(
        fn=load_random_abstract,
        outputs=[abstract_input, arxiv_id]
    )
    
    classify_btn.click(
        fn=classify_abstract,
        inputs=[abstract_input],
        outputs=[physics_output, run_output, strategy_output]
    )

# Run the app with public URL
demo.launch(share=True)