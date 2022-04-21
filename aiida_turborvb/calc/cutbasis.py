# -*- coding: utf-8 -*-

from aiida.plugins import DataFactory
from aiida.engine import calcfunction
"""

"""

BasisSet = DataFactory("gaussian.basisset")
BasisSetFree = DataFactory("gaussian.basissetfree")

@calcfunction
def cutbasis(basisset):
    """

    """
    from ase.data import atomic_numbers

    attr = basisset.attributes
    blocks = []
    for ii, block in enumerate(attr["blocks"]):
        n = block["n"]
        l = block["l"]
        coefs = [ [exp, cont] for exp, cont in block["coefficients"] if exp < atomic_numbers[basisset.attributes["element"]]**2 ]
        if len(coefs) == 0:
            continue
        blocks.append({"n": n,
                       "l": l,
                       "coefficients" : coefs})
    attr["blocks"] = blocks
    attr["name"] += "-cut"
    ret = BasisSetFree(**attr)
    return ret

