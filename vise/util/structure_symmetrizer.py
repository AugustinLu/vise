# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

from pymatgen import Structure, Element

import seekpath

import spglib

from vise.config import SYMMETRY_TOLERANCE, ANGLE_TOL, BAND_MESH_DISTANCE
from vise.util.logger import get_logger


logger = get_logger(__name__)


def cell_to_structure(cell: tuple) -> Structure:
    """Structure is returned from spglib cell

    Args:
        cell: Crystal structrue given either in Atoms object or tuple.
              In the case given by a tuple, it has to follow the form below,
              (Lattice parameters in a 3x3 array (see the detail below),
              Fractional atomic positions in an Nx3 array,
              Integer numbers to distinguish species in a length N array,
              (optional) Collinear magnetic moments in a length N array),
              where N is the number of atoms.
              Lattice parameters are given in the form:
                [[a_x, a_y, a_z],
                 [b_x, b_y, b_z],
                 [c_x, c_y, c_z]]
    """
    return Structure(lattice=cell[0], coords=cell[1],
                     species=[Element.from_Z(i) for i in cell[2]])


class StructureSymmetrizer:

    def __init__(self,
                 structure: Structure,
                 symprec: float = SYMMETRY_TOLERANCE,
                 angle_tolerance: float = ANGLE_TOL,
                 time_reversal: bool = True,
                 ref_distance: float = BAND_MESH_DISTANCE):
        """Get full information of seekpath band path.

        Note: site properties such as magmom are removed.

        The structures of aP (SG:1, 2), mC (5, 8, 9, 12, 15) and
        oA (38, 39, 40, 41) can be different between spglib and seekpath.
        see Y. Hinuma et al. Comput. Mater. Sci. 128 (2017) 140–184
        -- spglib mC
         6.048759 -3.479491 0.000000
         6.048759  3.479491 0.000000
        -4.030758  0.000000 6.044512
        -- seekpath mC
         6.048759  3.479491  0.000000
        -6.048759  3.479491  0.000000
        -4.030758  0.000000  6.044512

        Args:
            structure (Structure):
                Pymatgen Structure class object
            symprec (float):
                Distance tolerance in cartesian coordinates Unit is compatible
                with the structure.
            angle_tolerance (float):
                Angle tolerance used for symmetry analyzer.
            time_reversal (bool):
                If the time reversal symmetry exists. Used only for seekpath.
            ref_distance (float):
                Mesh distance for the k-point mesh.
        """
        self.structure = structure
        if structure.site_properties:
            logger.warning(f"Site property {structure.site_properties.keys()} "
                           f"removed in primitive and conventional structures.")
        self.symprec = symprec
        self.angle_tolerance = angle_tolerance
        self.time_reversal = time_reversal
        self.ref_distance = ref_distance
        lattice = list(structure.lattice.matrix)
        positions = structure.frac_coords.tolist()
        atomic_numbers = [i.specie.number for i in structure.sites]
        self.cell = (lattice, positions, atomic_numbers)
        self._spglib_sym_data = None
        self._conventional = None
        self._primitive = None
        self._seekpath_data = None
        self._band_primitive = None

    @property
    def spglib_sym_data(self):
        if not self._spglib_sym_data:
            self._spglib_sym_data = spglib.get_symmetry_dataset(
                self.cell, self.symprec, self.angle_tolerance)
        return self._spglib_sym_data

    @property
    def conventional(self):
        if self._conventional is None:
            conventional = spglib.standardize_cell(
                self.cell, self.symprec, self.angle_tolerance)
            if conventional is None:
                raise ViseSymmetryError(
                    "Spglib couldn't find the conventional cell. Change the "
                    "symprec and/or angle_tolerance.")
            else:
                self._conventional = cell_to_structure(conventional)
        return self._conventional

    @property
    def primitive(self):
        if self._primitive is None:
            primitive = spglib.find_primitive(
                self.cell, self.symprec, self.angle_tolerance)
            if primitive is None:
                raise ViseSymmetryError(
                    "Spglib couldn't find the primitive cell. "
                    "Change the symprec and/or angle_tolerance.")
            else:
                self._primitive = cell_to_structure(primitive)
        return self._primitive

    def find_seekpath_data(self):
        """Get full information of seekpath band path.

        Return:
            Dict with some properties. See docstrings of seekpath.
        """
        self._seekpath_data = \
            seekpath.get_explicit_k_path(structure=self.cell,
                                         symprec=self.symprec,
                                         angle_tolerance=self.angle_tolerance,
                                         with_time_reversal=self.time_reversal,
                                         reference_distance=self.ref_distance)
        lattice = self._seekpath_data["primitive_lattice"]
        element_types = self._seekpath_data["primitive_types"]
        species = [Element.from_Z(i) for i in element_types]
        positions = self._seekpath_data["primitive_positions"]
        self._band_primitive = Structure(lattice, species, positions)

    @property
    def seekpath_data(self):
        if self._seekpath_data is None:
            self.find_seekpath_data()
        return self._seekpath_data

    @property
    def band_primitive(self) -> Structure:
        if self._band_primitive is None:
            self.find_seekpath_data()
        return self._band_primitive

    @property
    def is_primitive_lattice_changed(self) -> bool:
        # For Lattice comparison, np.allclose is used.
        # def allclose(a, b, rtol=1.e-5, atol=1.e-8, equal_nan=False):
        return self.structure.lattice != self.primitive.lattice

    @property
    def is_band_primitive_lattice_changed(self) -> bool:
        return self.structure.lattice != self.band_primitive.lattice


class ViseSymmetryError(Exception):
    """Raised when the spglib return is inadequate."""
    pass
