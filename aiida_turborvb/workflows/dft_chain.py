from aiida.orm import Int, Float, Dict, StructureData, Code, Str
from aiida.engine import WorkChain, ToContext, calcfunction, if_
from aiida.plugins.factories import CalculationFactory

from aiida.engine import run

Mf10  = CalculationFactory('turborvb.makefort10wrp')
AP    = CalculationFactory('turborvb.assemblingpseudowrp')
Cf10m = CalculationFactory('turborvb.convertfort10molwrp')
Prep  = CalculationFactory('turborvb.prepwrp')

def add_this(name, src, dst):
    if name in src:
        dst[name] = src[name]

@calcfunction
def prepare_MF10_pars(pars):
    p = pars.get_dict()
    ret = {}
    for prop in ("basis", "pseudo"):
        add_this(prop, p, ret)
    ret = Dict(dict=ret)
    return ret

@calcfunction
def prepare_AP_pars(pars):
    p = pars.get_dict()
    ret = {}
    for prop in ("pseudo", ):
        add_this(prop, p, ret)
    ret = Dict(dict=ret)
    return ret

@calcfunction
def prepare_CF10M_pars(pars):
    ret = Dict()
    return ret

@calcfunction
def prepare_PREP_pars(pars, structure):
    p = pars.get_dict()
    structure_ = structure.get_ase()
    positions = structure_.get_positions()

    # Set default box

    import numpy as np
    minimum = np.min(positions, axis = 0)
    maximum = np.max(positions, axis = 0)
    difference = maximum - minimum
    box = (difference + 15) * 1.8897259886
    ret = {"box" : box}

    for prop in ("box", "grid", "doublegrid"):
        add_this(prop, p, ret)
    ret = Dict(dict=ret)
    return ret

@calcfunction
def get_energy():
    return Float(0.0)

class DFT(WorkChain):
    """
    A workflow for DFT calculation using TurboDFT
    """

    @classmethod
    def define(cls, spec):
        super(DFT, cls).define(spec)
        spec.input("mf10_code", valid_type = Code)
        spec.input("ap_code", valid_type = Code)
        spec.input("cf10m_code", valid_type = Code)
        spec.input("prep_code", valid_type = Code)
        spec.input("structure", valid_type = StructureData)
        spec.input("parameters", valid_type = Dict)
        spec.output("energy", valid_type = Float)
        spec.outline(
            cls.mf10,
            if_(cls.is_pseudo)(cls.ap),
            cls.cf10m,
            cls.prep,
            cls.energy
        )

    def is_pseudo(self):
        parameters = self.inputs.parameters.get_dict()
        return "pseudo" in parameters

    def mf10(self):
        inputs = dict( code       = self.inputs.mf10_code,
                       structure  = self.inputs.structure,
                       parameters = prepare_MF10_pars(self.inputs.parameters)
                     )
        future = self.submit(Mf10, **inputs)
        return ToContext(mf10 = future)

    def ap(self):
        inputs = dict( code       = self.inputs.ap_code,
                       fort10     = self.ctx.mf10.outputs.fort10,
                       parameters = prepare_AP_pars(self.inputs.parameters)
                     )
        future = self.submit(AP, **inputs)
        return ToContext(ap = future)

    def cf10m(self):
        inputs = dict( code       = self.inputs.cf10m_code,
                       fort10     = self.ctx.mf10.outputs.fort10,
                       parameters = prepare_CF10M_pars(self.inputs.parameters) )
        future = self.submit(Cf10m, **inputs)
        return ToContext(cf10m = future)

    def prep(self):
        inputs = dict( code       = self.inputs.prep_code,
                       fort10     = self.ctx.cf10m.outputs.fort10,
                       parameters = prepare_PREP_pars(self.inputs.parameters,
                                                      self.inputs.structure) )
        try:
            inputs["pseudo"] = self.ctx.ap.outputs.pseudo
        except:
            pass
        future = self.submit(Prep, **inputs)
        return ToContext(prep = future)

    def energy(self):
        self.out("energy", self.ctx.prep.outputs.energy)
        try:
            self.out("pseudo", self.ctx.prep.inputs.pseudo)
        except:
            pass

