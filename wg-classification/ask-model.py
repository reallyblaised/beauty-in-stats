from transformers import AutoModelForCausalLM, AutoTokenizer
import pandas as pd
import torch
import time
import numpy as np

import ast

from rulebased import decaybased_classifier

import os
os.environ["export PYTORCH_CUDA_ALLOC_CONF"] = 'expandable_segments:True'

from accelerate import Accelerator

accelerator = Accelerator()

start = time.time()

model_name = "Qwen/Qwen2.5-7B-Instruct"

torch.cuda.empty_cache()
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,#"auto",
    device_map="auto",
    cache_dir="/work/submit/anbeck/cache/huggingface",
)

# model = model.to("cuda")
model = accelerator.prepare(model)
tokenizer = AutoTokenizer.from_pretrained(model_name)
print(f"Loading the model took {time.time() - start:.2f}s", flush=True)
start = time.time()

from sentence_transformers import SentenceTransformer, util
similarity_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def guess_pdgid(model, embeddings, pdgids, particle):
    embedding = model.encode(particle, convert_to_tensor=True)
    similarity = [util.pytorch_cos_sim(embedding, e)[0][0].cpu() for e in embeddings]
    if np.max(similarity) > 0.5:
        bestguess = pdgids[np.argmax(similarity)]
    else:
        bestguess = "unknown"
    return bestguess

def load_conversions():
    conversions = pd.read_csv("conversions.csv", comment="#", skipinitialspace=True)
    conversions.drop(columns=["PYTHIAID", "GEANT3ID"], inplace=True)
    conversions.rename(columns={"ID": "PDGID"}, inplace=True)
    return conversions

conversions = load_conversions()
embeddings = [similarity_model.encode(l.replace("{", "").replace("}", "").replace("\\", ""), convert_to_tensor=True) for l in conversions['LATEXNAME'].values]
print(f"Loading the data took {time.time() - start:.2f}s", flush=True)

intro = "You are a particle physicist. "
instructions = "Determine the full decay chain considered in the analysis described in the following abstract. State your result in terms of the production mechanism, the parent in the decay, and the children. "
example = "As an example, a paper that measures Bs->mu+mu- in pp collisions would be classified as production=['pp'], parent=['B_s^0'], children=['\mu^+', '\mu^-']. "
details = "The last line of your response should be a list of three lists of strings, one for each of the production, parent, and children, for example: [['pp'], ['B_s^0'], ['\mu^+', '\mu^-']]. If there are two or more different decay chains, list two or more lists of this type. Note that a jet is considered its own particle."
task = "The abstract is as follows:"


data = pd.read_pickle("/ceph/submit/data/user/b/blaised/lhcb_corpus/lhcb_papers.pkl")
classifier_wg = []
for abstract, wg, arxiv in zip(data["abstract"], data["working_groups"], data['arxiv_id']):
    start = time.time()
    messages = [
        {"role": "system", "content": intro+instructions+example+details+task},
        {"role": "user", "content": abstract}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    torch.cuda.empty_cache()
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=500,
        do_sample=False,
        temperature=0.0,
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    t_response = time.time()-start
    start = time.time()

    lastline = response.split("\n")[-1].replace("{", "").replace("}", "").replace("\\", "").replace("rm ", "").replace('.', "").replace('(',"").replace(')',"")
    print(lastline, flush=True)
    try:
        decays = ast.literal_eval("["+lastline+"]")
    except:
        print("Could not parse the response", flush=True)
        classifier_wg.append(["unintelligible"])
        continue
    try:
        assert(len(decays) > 0)
        assert(all([len(d) == 3 for d in decays]))
    except:
        classifier_wg.append(["unintelligible"])
        continue

    for d in range(len(decays)):
        production, parent, children = decays[d][0], decays[d][1], decays[d][2]
        if production == [""]: # Assume pp if couldn't infer
            production = ["pp"]
        for i in range(len(parent)):
            parent[i] = guess_pdgid(similarity_model, embeddings, conversions['PDGID'].values, parent[i])
        for i in range(len(children)):
            children[i] = guess_pdgid(similarity_model, embeddings, conversions['PDGID'].values, children[i])
        decays[d][0] = production
        decays[d][1] = parent
        decays[d][2] = children
    # print(decays, flush=True)

    t_pdgid = time.time()-start
    start = time.time()

    classifier_wg.append([])
    for d in decays:
        production, parents, children = d
        for p in parents:
            try:
                guess = decaybased_classifier(production[0], p, children)
            except Exception as e:
                print(e)
                print(production[0], p, children)
                guess = "unidentifiable"
            classifier_wg[-1].append(guess)
    if sum([w==classifier_wg[-1][0] for w in classifier_wg[-1]]) == len(classifier_wg[-1]):
        classifier_wg[-1] = [classifier_wg[-1][0]]

    t_classification = time.time()-start
    print(f"{arxiv}: {classifier_wg[-1]} {wg}", flush=True)
    print(f"Response: {t_response:.2f}s, PDGID: {t_pdgid:.2f}s, Classification: {t_classification:.2f}s", flush=True)
    print(f"\n\n", flush=True)

data["classifier_wg"] = classifier_wg
data.to_pickle("lhcb_papers.pkl")