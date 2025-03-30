from particle import Particle
from particle.converters.bimap import DirectionalMaps
from particle import PDGID


PDG2LaTeXNameMap, LaTeX2PDGNameMap = DirectionalMaps("PDGID", "LaTexName", converters=(PDGID, str))
PDG2EvtGenNameMap, EvtGen2PDGNameMap = DirectionalMaps("PDGID", "EVTGENNAME", converters=(PDGID, str))

def count_charm(pdgid):
    """
    This function counts the number of charm quarks in a particle.
    For charm tetraquarks or pentaquarks, this returns 1.
    """
    if pdgid.pdgid.has_charm:
        if pdgid.pdgid.is_meson and pdgid.is_self_conjugate:
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

def get_pdgids(cildren):
    ids = []
    for c in children:
        try:
            idc = Particle.from_pdgid(int(c))
            ids.append(idc)
        except Exception as e:
            print(e)
            if c in ["jet", "jets"]:
                ids.append(c)

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
    # pdgid_parent = EvtGen2PDGNameMap[parent]
    # pdgid_children = [EvtGen2PDGNameMap[child] for child in children]
    pdgid_parent = Particle.from_pdgid(int(parent))
    pdgid_children = [Particle.from_pdgid(int(child)) for child in children]
    if any(c.pdgid.has_top for c in pdgid_children) or any(c in children for c in ["jet", "jets"]) or pdgid_parent.pdgid.is_gauge_boson_or_higgs or children==[]:
        return "qcd_electroweak_and_exotica"
    if pdgid_parent.pdgid.has_charm & (not pdgid_parent.pdgid.has_bottom) & (not pdgid_parent.is_self_conjugate): # ccbar goes to quarkonia
        # Is there exactly one c and no Bc?
        return "charm_physics"
    if pdgid_parent.is_self_conjugate:
        return "Quarkonia"
    if not (production=="pp"):
        return "ions_and_fixed_target"
    if any(abs(c.pdgid) in [12, 14, 16] for c in pdgid_children):
        return "semileptonic_b_decays"
    radiative = any(abs(c.pdgid)==22 for c in pdgid_children)
    leptonic = any(c.pdgid.is_lepton for c in pdgid_children)
    if radiative or leptonic:
        # Missing forbidden decays but maybe the leptonic rule catches them
        return "rare_decays"
    charms = [count_charm(c) for c in pdgid_children]
    if 1 in charms:
        return "b_decays_to_open_charm"
    if 2 in charms:
        return "b_decays_to_charmonia"
    return "charmless_b_hadron_decays"