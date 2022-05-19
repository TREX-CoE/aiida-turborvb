from aiida.orm import Int, Float, Dict, StructureData, Code, Str, SinglefileData
from aiida.engine import WorkChain, ToContext, calcfunction, if_
from aiida.plugins.factories import CalculationFactory

from aiida.engine import run

Vmcopt = CalculationFactory('turborvb.vmcoptwrp')
Vmc    = CalculationFactory('turborvb.vmcwrp')
Lrdmc  = CalculationFactory('turborvb.lrdmcwrp')

def add_this(name, src, dst):
    if name in src:
        dst[name] = src[name]

@calcfunction
def prepare_VMCOPT_pars(pars):
    p = pars.get_dict()
    ret = {}
    if "vmcopt_namelist_update" in p:
        ret["namelist_update"] = p["vmcopt_namelist_update"]
    if "vmcopt_eq" in p:
        ret["eq"] = p["vmcopt_eq"]
    ret = Dict(dict=ret)
    return ret

@calcfunction
def prepare_VMC_pars(pars):
    p = pars.get_dict()
    ret = {}
    if "vmc_namelist_update" in p:
        ret["namelist_update"] = p["vmc_namelist_update"]
    ret = Dict(dict=ret)
    return ret

@calcfunction
def prepare_LRDMC_pars(pars):
    p = pars.get_dict()
    ret = {}
    if "lrdmc_namelist_update" in p:
        ret["namelist_update"] = p["lrdmc_namelist_update"]
    ret = Dict(dict=ret)
    return ret

class QMC(WorkChain):
    """
    A workflow for QMC calculation using TurboRVB
    """

    @classmethod
    def define(cls, spec):
        super(QMC, cls).define(spec)
        spec.input("vmcopt_code", valid_type = Code)
        spec.input("vmc_code", valid_type = Code)
        spec.input("lrdmc_code", valid_type = Code)
        spec.input("fort10", valid_type = SinglefileData)
        spec.input("parameters", valid_type = Dict)
        spec.input("pseudo", valid_type = SinglefileData, required=False)
        spec.output("energy", valid_type = Float)
        spec.output("energy_err", valid_type = Float)
        spec.outline(
            cls.vmcopt,
            cls.vmc,
            cls.lrdmc,
            cls.energy,
        )

    def is_pseudo(self):
        parameters = self.inputs.parameters.get_dict()
        return "pseudo" in parameters

    def vmcopt(self):
        inputs = dict( code       = self.inputs.vmcopt_code,
                       fort10     = self.inputs.fort10,
                       parameters = prepare_VMCOPT_pars(self.inputs.parameters)
                     )
        if "pseudo" in self.inputs:
            inputs["pseudo"] = self.inputs.pseudo
            print("Doing pseudo")
        future = self.submit(Vmcopt, **inputs)
        return ToContext(vmcopt = future)

    def vmc(self):
        inputs = dict( code       = self.inputs.vmc_code,
                       fort10     = self.ctx.vmcopt.outputs.fort10_averaged,
                       parameters = prepare_VMC_pars(self.inputs.parameters)
                     )
        if "pseudo" in self.inputs:
            inputs["pseudo"] = self.inputs.pseudo
        future = self.submit(Vmc, **inputs)
        return ToContext(vmc = future)

    def lrdmc(self):
        inputs = dict( code         = self.inputs.lrdmc_code,
                       fort10       = self.ctx.vmcopt.outputs.fort10_averaged,
                       fort11       = self.ctx.vmc.outputs.fort11,
                       fort12       = self.ctx.vmc.outputs.fort12,
                       scratch      = self.ctx.vmc.outputs.scratch,
                       trial_energy = self.ctx.vmc.outputs.energy,
                       parameters   = prepare_LRDMC_pars(self.inputs.parameters) )
        if "pseudo" in self.inputs:
            inputs["pseudo"] = self.inputs.pseudo
        future = self.submit(Lrdmc, **inputs)
        return ToContext(lrdmc = future)

    def energy(self):
        self.out("energy", self.ctx.lrdmc.outputs.energy)
        self.out("energy_err", self.ctx.lrdmc.outputs.energy_err)

