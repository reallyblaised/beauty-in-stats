# Pedestrian working group classification

The following prompt can fairly reliably pick out the relevant decay chain from an abstract:
```bash
You are a particle physicist specializing in flavour physics with the LHCb experiment.
Determine the full decay chain considered in the paper corresponding to the following abstract.
Please state your result in terms of the production mechanism, the parent in the decay, and the children.
For example, a paper that measures Bs->mu+mu- in pp collisions would be classified as production="pp", parent="Bs", children=["mu+", "mu-"].
```
Additional instructions are able to prompot the LLM to present the parent and children using their PDGID.
However, any of the representations in [this file](https://github.com/scikit-hep/particle/blob/main/src/particle/data/conversions.csv) are possible. Including latex.

The production, parent, and children can then be given to the function defined in this folder called `decaybased_classifier(production, parent, children)` in order to obtain a primary classification.