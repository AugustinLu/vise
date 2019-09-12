from pymatgen.io.vasp import Potcar
from vise.input_set.vise_settings_util import load_potcar_yaml
from vise.input_set.xc import Xc


class XcTaskPotcar:

    def __init__(self,
                 potcar: Potcar,
                 max_enmax: int):

        self.potcar = potcar
        self.max_enmax = max_enmax

    @classmethod
    def from_options(cls,
                     xc: Xc,
                     symbol_set: tuple,
                     potcar_set_name: str = None,
                     override_potcar_set: dict = None):
        """ Construct Potcar from xc and some options.

        Args: See ViseInputSet docstrings

        Return: XcTaskPotcar class object
        """

        potcar_functional = "LDA" if xc == Xc.lda else "PBE_54"
        potcar_set_name = potcar_set_name or "normal"

        potcar_list = load_potcar_yaml(potcar_set_name, override_potcar_set)
        potcar_symbols = [potcar_list.get(el, el) for el in symbol_set]
        potcar = Potcar(potcar_symbols, functional=potcar_functional)

        max_enmax = max([p.enmax for p in potcar])

        return cls(potcar, max_enmax)
