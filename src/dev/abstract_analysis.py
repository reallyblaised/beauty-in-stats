import json
import requests
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

@dataclass
class ClassificationConfig:
    """Configuration for the classification categories and system prompt."""

    SYSTEM_PROMPT = """
    ROLE 
    ==== 
    You are a research scientist member of the LHCb collaboration at CERN. You are a domain expert in the fields of heavy-flavour, heavy-ion, dark-sector and electroweak physics, 
    and in precision tests of Standard Model (SM) and direct searches for New Physics. 
    
    TASK
    ====
    Classify abstracts from published LHCb papers focusing on data analysis. A subset of the published LHCb appers focus on instrumentation, high-throughput computing and software, and feasibility and sensitivity studies (referred to PERFORMANCE papers). 
    However, your must focus on classifying physics analysis results. Your classifications will power a RAG system for physics analysis recommendations. You will classify each abstract using the following categories:

        1. PHYSICS FOCUS --- the "context" of the analysis, categorised in a schema similar to the PHYSICS WORKING GROUPS of the LHCb Collaboration, with some additional categories, as specified below. 
        2. RUN PERIOD --- the LHCb data-taking period, categorised by the years of data taking and the integrated luminosity of the dataset used in the analysis.
        3. ANALYSIS STRATEGY --- the observable of the analysis and the statistical inference framework adopted to extract it from the data.

    CHAIN OF REASONING
    ==================
    1. Determine if the abstract pertains to physics analysis or a technical paper. 
    2. Extract the particle processes analysed in the measurement or search --- typically enclosed in $$ symbols.
    3. Identify the centre-of-mass energy, any mention of the runs of LHCb data taking (Run 1, Run 2, Run1+2, Run 3), if any, and the integrated luminosity of the dataset considered.
    4. Focus key words detailing the primary result of the paper. EXAPLE: "measurement", "angular analysis", "test", "search", etc. 

    PHYSICS SCOPE 
    =============
    - `b->sll`: loop-suppressed, PENGUIN beauty decays to final states with TWO same-generation leptons, mediated by the $b \to s \ell \ell$ current. EXAMPLES: $B^+ \to K^{+} \mu^+ \mu^-$, $B_s^0 \to \mu^+ \mu^-$, $B_s \to \phi \mu^+ \tau^-$. NOTE: this category does not include decays with neutrinos in the final state. This label cannot be assigned to fully hadronic final states.
    - 'radiative_decays': heavy-flavour decays with at least one photon, $\gamma$, in the final state. 
    - `spectroscopy`: exotic multi-quark (>3) QCD states, such as tetraquarks and pentaquarks.
    - `semileptonic`: beauty decays with NEUTRINOS in the final state. EXAMPLE: $B \to D^{(*)}\ell\nu$ decays.
    - `lifetime`: lifetimes of heavy-flavoured hadrons.
    - `electoweak`: Electroweak and Higgs physics, which typically focuses on the study of electroweak production of heavy bosons, such as $W$ and $Z$ bosons, and the Higgs boson. 
    - `dark_sector`: Dark Matter and Dark-Sector searches for particles produced in association with $B$ mesons or in the decays of $B$ mesons, or generated promptly or displaced states from the interaction points. Includes searches for dark photons, long-lived particles (LLP), dark scalars, Higgs-like bosons, axion-like particles (ALP), Majorana neutrinos, heavy neutral leptons (HNL), dark showers and dark hadrons etc
    - `forbidden_decays`: searches for baryon number violation, lepton flavour violation, lepton flavour universality violation, and lepton number violation in the decays of heavy-flavoured hadrons. 
    - `jet_physics`: Jet Physics and QCD, which typically focuses on the study of jet production in $pp$ collisions and the extraction of strong coupling constant, $\alpha_s$.
    - `heavy_ions`: ANY analysis of data NOT PRODUCED IN PROTON-PROTON collisions, but LED+matter interactions: EXAMPLE: $PbPb$, $p$Ne, $pPb$. 
    - `charm`: charm mesons and baryons, charge-parity asymmetry effects in the charm sector, and the extraction of CKM matrix elements, $|V_{cs}|$ and $|V_{cd}|$. The word 'CHARMLESS' means that this label DOES NOT APPLY. EXAMPLES: decays of $D^+$, $D_s$, $D^0$, $\Xi_c$, ... IMPORTANT: THEY NEVER INCLUDE BEAUTY DECAYS.
    - `CPV`: CP violation measurements in BEAUTY decays only, typically forcused on CP asymmetries and precision measurmements of the CKM angle $\gamma$ and the CKM phase $\beta$.
    
    RUN PERIOD 
    ==========
    Labels defined by years of data taking and the corresponding centre-of-mass energy and integrated luminosity:
    - `Run1`: years 2011 (1.0 fb-1, 7 TeV), 2012 (2.0 fb-1, 8 TeV); total integrated luminosity: 3 fb-1. 
    - `Run2`: years 2015 (0.3 fb-1, 13 TeV), 2016 (1.6 fb-1 AND NOT 1.0 fb-1, 13 TeV), 2017 (1.7 fb-1 AND NOT 1.0 fb-1, 13 TeV), 2018 (2.1 fb-1, 13 TeV); total integrated luminosity: 5.4 fb-1 or 6 fb-1. Check that the centre-of-mass energy is 13 TeV before assigning this label.
    - `Run1+2`: years 2011-2012, 2015-2018; total integrated luminosity: ~9 fb-1.
    - `Run3`: years 2022-2025; total integrated luminosity: ~15 fb-1 and nominal centre-of-mass energy of 13.6 TeV, *NOT 13 TeV*. NOTE: 13 TeV means Run 2 data taking.

    ANALYSIS STRATEGY
    =================
    - `angular_analysis`: study of angular distributions and asymmetries in the decays of heavy-flavoured hadrons and the extraction of observables related to WC (such as $P_5'$ and forward-backward asymmetries).
    - `amplitude_analysis`: study of the decay amplitudes of heavy-flavoured hadrons to determine spin-parity or observation of intermediate resonances and Dalitz analyses. Scrutinising the interefence between different decay amplitudes and the resonant substructure of the decay.
    - `search`: searches for yet-unobserved states or breaking of the Standard Model symmetries. Result in LIMIT SETTING at $90\%$ or $95\%$ confidence level (CL).
    - 'direct_measurement': measurement of particle- or decay- level observables, or measuremenst of symmetries (or breakinf thereof) or free parameters of the SM. EXAMPLES: BF measurements, lifetime measurements, mass measurements, CP asymmetry measurements, production cross-section measurements, magnitude of CKM matrix elements, CKM angles, etc.

    UNCERTAINTY GUIDELINES
    ======================
    In the event of a performance paper, use the <PERF> identifier for all categories.
    You may choose up to THREE labels for each category. If you are very confident about one or two categories, you may use those labels only. Only use labels for which your confidence is HIGH. 
    If you are uncertain about any category, USE the <UNK> identifier. 
    """

    # USER-LEVEL PROMPT
    # configuration for classification categories.
    VALID_FOCUS = {
        'b->sll',
        'radiative_decays', 
        'spectroscopy', 
        'semileptonic', 
        'lifetime', 
        'electoweak', 
        'dark_sector', 
        'forbidden_decays',
        'jet_physics', 
        'heavy_ions', 
        'charm', 
        'CPV'
    }

    VALID_RUN = {'Run1', 'Run2', 'Run1+2', 'Run3'}

    VALID_STRATEGY = {
        'angular_analysis', 'amplitude_analysis', 'search', 'direct_measurement'
    }

    @classmethod
    def get_prompt_template(cls) -> str:
        return f"""You are analyzing an LHCb physics paper abstract. Classify it according to these categories:

    PHYSICS FOCUS (choose 2): {', '.join(cls.VALID_FOCUS)}
    RUN PERIOD (choose 1): {', '.join(cls.VALID_RUN)}
    ANALYSIS STRATEGY (choose at most 2): {', '.join(cls.VALID_STRATEGY)}

    If you're uncertain about any category, use <UNK>. For technical/performance papers, use <PERF>.

    Your response must follow this exact format:
    {{{{
        "focus": "<CATEGORY>",
        "run": "<CATEGORY>",
        "strategy": "<CATEGORY>",
    }}}}

    Example responses:
    {{{{
        "focus": "b->sll", "radiative decays",
        "run": "Run1",
        "strategy": "angular_analysis", "search"
    }}}}

    Abstract:
    {{abstract}}

    Classification:"""

class OllamaClassifier:
    """Class to handle paper classification using an open-source LLM."""
    
    def __init__(self, model_name: str = "mistral", base_url: str = "http://localhost:11434"):
        """Initialize the classifier with model name and Ollama API URL."""
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.config = ClassificationConfig()
        self.prompt_template = self.config.get_prompt_template()

    def _make_ollama_request(self, prompt: str) -> str:
            """Send request to Ollama API."""
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model_name,
                "prompt": self.config.SYSTEM_PROMPT + "\n\n" + prompt,
                "stream": False,
                "options": {"temperature": 0.1, "top_p": 0.9}
            }

            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
                return response.json().get('response', '')
            except requests.RequestException as e:
                raise ConnectionError(f"Failed to connect to Ollama: {e}")
            except KeyError:
                raise ValueError("Unexpected response format from Ollama.")

    def classify_abstract(self, abstract: str) -> Optional[Dict[str, str]]:
        """Classify a single abstract."""
        prompt = self.prompt_template.format(abstract=abstract)
        response = self._make_ollama_request(prompt)

        try:
            # Parse JSON response
            classification = json.loads(response)
            if classification.get("focus") in self.config.VALID_FOCUS or classification.get("focus") == "<UNK>":
                return classification
        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
        return None

def main():
    """Interactive abstract classification."""
    classifier = OllamaClassifier(model_name="mistral")
    
    print("\n=== LHCb Paper Abstract Classifier ===")
    print("Enter/paste your abstract below (press Enter twice to finish):\n")
    
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    
    abstract = "\n".join(lines)
    
    if not abstract.strip():
        print("No abstract provided. Exiting.")
        return
    
    print("\nClassifying abstract...")
    result = classifier.classify_abstract(abstract)

    if result:
        print("\nClassification Result:")
        print(json.dumps(result, indent=2))
    else:
        print("\nCould not classify the abstract. Please try again.")

if __name__ == "__main__":
    main()
