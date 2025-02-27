from particle import Particle
from particle.converters.bimap import DirectionalMaps
from particle import PDGID


PDG2LaTeXNameMap, LaTeX2PDGNameMap = DirectionalMaps("PDGID", "LaTexName", converters=(PDGID, str))

def count_charm(pdgid):
    """
    This function counts the number of charm quarks in a particle.
    For charm tetraquarks or pentaquarks, this returns 1.
    """
    if pdgid.has_charm:
        if pdgid.is_meson and pdgid.is_self_conjugate:
            return 2
        else:
            return 1
    return 0

def count_bottom(part):
    """
    This function counts the number of bottom quarks in a particle.
    """
    p = Particle.finditer(latex_name=part)
    return next(p).has_bottom

def decaybased_classifier(production, parent, children):
    """
    This function classifies a decay chain based on the considered decay chain.
    Example:
    The measurement of the branching fraction of Bs->mu^+mu^- in pp collisions
    is input as production="pp", parent="Bs", children=["mu+", "mu-"].
    The output broadly follows the LHCb working groups. Due to the ambiguity
    in amplitude analyses and spectroscopy, the classification given here might
    differ form the real assignment.
    """
    # Convert LaTeX names to PDGIDs
    pdgid_parent = LaTeX2PDGNameMap[parent]
    pdgid_children = [LaTeX2PDGNameMap[child] for child in children]
    if any(c.has_top in pdgid_children) or any(c in children for c in ["jet", "jets"]) or pdgid_parent.is_gauge_boson_or_higgs or children==[]:
        return "QEE"
    if pdgid_parent.has_charm & (not pdgid_parent.has_bottom) & (not pdgid_parent.is_self_conjugate): # ccbar goes to quarkonia
        # Is there exactly one c and no Bc?
        return "Charm"
    if pdgid_parent.is_self_conjugate:
        return "Quarkonia"
    if not (production=="pp" ):
        return "HeavyIon"
    if any(abs(c) in [12, 14, 16] for c in pdgid_children):
        return "SL"
    radiative = any(abs(c)==22 for c in pdgid_children)
    leptonic = any(c.is_lepton for c in pdgid_children)
    if radiative | leptonic:
        # Missing forbidden decays but maybe the leptonic rule catches them
        return "RD"
    charms = [count_charm(c) for c in pdgid_children]
    if 1 in charms:
        return "B2OC"
    if 2 in charms:
        return "B2C"
    return "B2noC"