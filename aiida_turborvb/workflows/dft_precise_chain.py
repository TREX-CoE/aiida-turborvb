from aiida.orm import Int, Float, Dict, StructureData, Code, Str
from aiida.engine import WorkChain, ToContext, calcfunction, if_, while_
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
def prepare_PREP_pars(pars, structure, density):
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

    ret["grid"] = density

    for prop in ("box", "doublegrid"):
        add_this(prop, p, ret)
    ret = Dict(dict=ret)
    return ret

@calcfunction
def calc_density_convergence(**kwargs):
    ret = {"density" : []}
    data = {}
    for k, v in kwargs.items():
        if "density" in k:
            index = int(k.replace("density_",""))
            if index not in data:
                data[index] = {}
            data[index]["density"] = v
        if "energy" in k:
            index = int(k.replace("energy_",""))
            if index not in data:
                data[index] = {}
            data[index]["energy"] = v
    for index, d in data.items():
        if len(d) != 2: continue
        ret["density"].append([d["density"], d["energy"]])

    return Dict(dict = ret)


@calcfunction
def get_energy():
    return Float(0.0)

class DFTPrecise(WorkChain):
    """
    A workflow for DFT precise calculation using TurboDFT
    """

    @classmethod
    def define(cls, spec):
        super(DFTPrecise, cls).define(spec)
        spec.input("mf10_code", valid_type = Code)
        spec.input("ap_code", valid_type = Code)
        spec.input("cf10m_code", valid_type = Code)
        spec.input("prep_code", valid_type = Code)
        spec.input("structure", valid_type = StructureData)
        spec.input("parameters", valid_type = Dict)
        spec.output("density_convergance", valid_type = Dict)
        spec.outline(
            cls.setup,
            cls.mf10,
            if_(cls.is_pseudo)(cls.ap),
            cls.cf10m,
            while_(cls.is_finished)(
                cls.prep),
            cls.energy
        )

    def setup(self):
        self.density = 0.10
        self.stopdensity = 0.08
        self.deltadensity = 0.005
        self.density += self.deltadensity
        self.index = -1

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
        parameters = prepare_PREP_pars(self.inputs.parameters,
                                                      self.inputs.structure,
                                                      Float(self.density))
        inputs = dict( code       = self.inputs.prep_code,
                       fort10     = self.ctx.cf10m.outputs.fort10,
                       parameters = parameters)
        try:
            inputs["pseudo"] = self.ctx.ap.outputs.pseudo
        except:
            pass
        self.report("Running density {}".format(self.density))
        future = self.submit(Prep, **inputs)
        tocontext = {f"prep_{self.index}" : future}
        self.report(f"Adding {tocontext} {parameters.get_dict()}")
        return ToContext(**tocontext)

    def is_finished(self):
        self.density -= self.deltadensity
        self.index += 1

        if self.stopdensity < self.density:
            return True
        return False

    def energy(self):
        data = {}
        while True:
            self.index -= 1
            if self.index < 0: break
            prep = getattr(self.ctx, f"prep_{self.index}")
            data[f"density_{self.index}"] = prep.inputs.parameters.get_dict()["grid"]
            data[f"energy_{self.index}"] = prep.outputs.energy

        self.report(data)
        density_conv = calc_density_convergence(**data)
        self.report(density_conv.get_dict())
        self.out("density_convergance", density_conv)


