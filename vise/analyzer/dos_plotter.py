# -*- coding: utf-8 -*-

from collections import OrderedDict, defaultdict

import numpy as np
from atomate.utils.utils import get_logger
from pymatgen.electronic_structure.core import Spin
from pymatgen.electronic_structure.dos import Dos
from pymatgen.electronic_structure.dos import add_densities
from pymatgen.electronic_structure.plotter import DosPlotter
from pymatgen.io.vasp import Vasprun
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from vise.config import SYMMETRY_TOLERANCE, ANGLE_TOL

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"

logger = get_logger(__name__)


class ViseDosPlotter(DosPlotter):

    def get_plot(self, xlim=None, ylims=None, cbm_vbm=None, legend=True,
                 crop_first_value=False, title=None):
        """
        Get a matplotlib plot showing the DOS.

        Args:
            xlim (list):
                Specifies the x-axis limits. Set to None for automatic
                determination.
            ylims (list):
                Specifies the y-axes limits. Two types of input.
                [[y1min, y1max], [y2min, y2max], ..]
            cbm_vbm (list):
                Specify cbm and vbm [cbm, vbm]
            legend (bool):
                Whether to show the figure legend.
            crop_first_value (bool):
                Whether to crop the fist DOS.
            title (str):
                Title of the figure
        """

        ncolors = max(3, len(self._doses))
        ncolors = min(9, ncolors)
        import palettable
        colors = palettable.colorbrewer.qualitative.Set1_9.mpl_colors

        y = None
        all_densities = []
        all_energies = []

        # The DOS calculated using VASP holds a spuriously large value at the
        # first mesh to keep the consistency with the integrated DOS in DOSCAR
        # file. An example is shown below.
        # ------------- DOSCAR --------------------
        # 10 10 1 0
        # 0.1173120E+02 0.5496895E-09 0.5496895E-09 0.5496895E-09 0.5000000E-15
        # 1.000000000000000E-004
        # CAR
        # unknown system
        #     23.00000000 - 9.00000000 3201 6.62000004 1.00000000
        #     -9.000 0.6000E+03 0.6000E+03 0.6000E+01 0.6000E+01 <-- large DOS
        #     -8.990 0.0000E+00 0.0000E+00 0.6000E+01 0.6000E+01

        i = 1 if crop_first_value else 0

        for key, dos in self._doses.items():
            energies = dos['energies'][i:]
            densities = {Spin(k): v[i:] for k, v in dos['densities'].items()}
            if not y:
                y = {Spin.up: np.zeros(energies.shape),
                     Spin.down: np.zeros(energies.shape)}
            all_energies.append(energies)
            all_densities.append(densities)

        # Make groups to be shown in the same figure.
        # Example, ZrTiSe4
        # keys = ['Total', 'Site:1 Zr-s', 'Site:1 Zr-p', 'Site:1 Zr-d',
        #         'Site:2 Ti-s', 'Site:2 Ti-p', 'Site:2 Ti-d', 'Site:3 Se-s',
        #         'Site:3 Se-p', 'Site:3 Se-d', 'Site:5 Se-s', 'Site:5 Se-p',
        #         'Site:5 Se-d']
        keys = list(self._doses.keys())
        grouped_keys = OrderedDict()
        for k in keys:
            first_word = k.split()[0]
            if first_word in grouped_keys:
                grouped_keys[first_word].append(k)
            else:
                grouped_keys[first_word] = [k]

        import matplotlib.pyplot as plt
        num_figs = len(grouped_keys)
        fig, axs = plt.subplots(num_figs, 1, sharex=True)

        if xlim:
            axs[0].set_xlim(xlim)

        n = 0
        for i, gk in enumerate(grouped_keys):
            all_pts = []
            for j, key in enumerate(grouped_keys[gk]):
                x = []
                y = []
                for spin in [Spin.up, Spin.down]:
                    if spin in all_densities[n]:
                        densities = list(int(spin) * all_densities[n][spin])
                        energies = list(all_energies[n])
                        x.extend(energies)
                        y.extend(densities)
                all_pts.extend(list(zip(x, y)))
                axs[i].plot(x, y, color=colors[j % ncolors], label=str(key),
                            linewidth=2)
                n += 1

            # plot vertical lines for band edges or Fermi level
            if self.zero_at_efermi:
                # plot a line
                axs[i].axvline(0, color="black", linestyle="--", linewidth=0.5)
                if cbm_vbm:
                    axs[i].axvline(cbm_vbm[0] - cbm_vbm[1], color="black",
                                   linestyle="--", linewidth=0.5)
            else:
                axs[i].axvline(self._doses[key]['efermi'],
                               color="black", linestyle="--", linewidth=0.5)
                if cbm_vbm:
                    axs[i].axvline(cbm_vbm[0], color="black", linestyle="--",
                                   linewidth=0.5)

            if legend:
                axs[i].legend(loc="best", markerscale=0.1)
                #                axs[i].legend(bbox_to_anchor=(1.1, 0.8), loc="best")
                leg = axs[i].get_legend()
                for legobj in leg.legendHandles:
                    legobj.set_linewidth(1.2)
                ltext = leg.get_texts()
                plt.setp(ltext, fontsize=7)
            else:
                axs[i].set_title(key, fontsize=7)

            axs[i].axhline(0, color="black", linewidth=0.5)

        if ylims and len(ylims) not in (num_figs, 2):
            raise ValueError("The number of y-ranges is not proper.")

        if ylims and len(ylims) == 2:
            if ylims[0][1] > 1.0:
                axs[0].set_ylim(ylims[0])
            for i in range(1, len(axs)):
                axs[i].set_ylim(ylims[1])

        elif ylims:
            for i in range(len(axs)):
                axs[i].set_ylim(ylims[i])
        # else:
        #     for i in range(len(axs)):
        #         ylim = axs[i].get_ylim()
        #         print(ylim)
        #         relevanty = [p[1] for p in all_pts
        #                      if ylim[0] < p[0] < ylim[1]]
        #         axs[i].set_ylim((min(relevanty), max(relevanty)))e

        axs[-1].set_xlabel('Energy (eV)')
        plt.tight_layout()

        plt.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.2, hspace=0.2)

        if title:
            axs[0].title.set_text(title)

        return plt


def get_dos_plot(vasprun_file: str,
                 cbm_vbm: list = None,
                 pdos_type: str = "element",
                 specific: list = None,
                 orbital: list = True,
                 xlim: list = None,
                 ymaxs: list = None,
                 zero_at_efermi: bool = True,
                 legend: bool = True,
                 crop_first_value: bool = True,
                 show_spg: bool = True,
                 symprec: float = SYMMETRY_TOLERANCE,
                 angle_tolerance: float = ANGLE_TOL):
    """

    Args:
        vasprun_file (str):
            vasprun.xml-type file name
        cbm_vbm (list):
            List of [cbm, vbm]
        pdos_type (str): Plot type of PDOS.
            "element": PDOS grouped by element type
            "site": PDOS grouped by equivalent sites
            "none": PDOS are not grouped.
        specific (list): Show specific PDOS. If list elements are integers,
            PDOS at particular sites are shown. If elements are shown,
            PDOS of particular elements are shown.
            ["1", "2"] --> At site 1 and 2 compatible with pdos_type = "none"
            ["Mg", "O"] --> Summed at Mg and O sites coompatible with
                            pdos_type = "element"
        orbital (bool):
            Whether to show orbital decomposed PDOS.
        xlim (list):
            Specifies the x-axis limits. Set to None for automatic determination.
        ymaxs (list):
            Specifies the maxima of absolute y-axis limits.
        zero_at_efermi (bool):
            Whether to show the plot in the absolute scale.
        legend (bool):
            Whether to show the figure legend.
        crop_first_value (bool):
            Whether to crop the fist DOS.
        show_spg (bool):
            Whether to show space group number in the title.
        symprec (float):
            Symprec for determining the equivalent sites.
        angle_tolerance (float):
            Angle tolerance for symmetry analysis in degree.
    """

    v = Vasprun(vasprun_file, ionic_step_skip=True, parse_eigen=False)
    if v.converged_electronic is False:
        logger.warning("SCF is not attained in the vasp calculation.")

    complete_dos = v.complete_dos

    # check cbm
    if cbm_vbm is None:
        if complete_dos.get_gap() > 0.1:
            cbm_vbm = complete_dos.get_cbm_vbm()

    structure = v.final_structure

    dos = OrderedDict()
    # The CompleteDos behaves as DOS for total dos.
    dos["Total"] = complete_dos

    if specific and specific[0].isdigit():
        if pdos_type is not "none":
            logger.warning("pdos_type is changed from {} to none"
                           .format(pdos_type))
        pdos_type = "none"
    elif specific and specific[0].isalpha():
        if pdos_type is not "none":
            logger.warning("pdos_type is changed from {} to element"
                           .format(pdos_type))
        pdos_type = "element"

    sga = None
    grouped_indices = defaultdict(list)
    if pdos_type == "element":
        for indices, s in enumerate(structure):
            grouped_indices[str(s.specie)].append(indices)
    elif pdos_type == "site":
        # equivalent_sites: Equivalent site indices from SpacegroupAnalyzer.
        sga = SpacegroupAnalyzer(structure=structure,
                                 symprec=symprec,
                                 angle_tolerance=angle_tolerance)
        symmetrized_structure = sga.get_symmetrized_structure()
        # equiv_indices = [[0], [1], [2, 3], [4, 5]]
        equiv_index_lists = symmetrized_structure.equivalent_indices

        for l in equiv_index_lists:
            name = str(structure[l[0]].specie) + " " \
                   + sga.get_symmetry_dataset()["wyckoffs"][l[0]]
            grouped_indices[name] = l

    elif pdos_type == "none":
        for indices, s in enumerate(structure):
            grouped_indices[str(s.specie) + " site:" + str(indices)].append(indices)
    else:
        raise KeyError("The given pdos_type is not supported.")

    # TODO: Add specific handling
    # if specific:
    #     tmp = defaultdict(list)
    #     for key, value in grouped_indices.items():
    #         if pdos_type == "element" and key in specific:
    #             tmp[key] = value
    #         else:
    #             # type(index) is str
    #             index = ''.join(c for c in key if c.isdigit())
    #             if index in specific:
    #                 tmp[key] = value
    #     grouped_indices = tmp

    # efermi is set to VBM if exists.
    efermi = cbm_vbm[1] if cbm_vbm else complete_dos.efermi
    complete_dos.efermi = efermi
    energies = complete_dos.energies

    for key, value in grouped_indices.items():
        for indices in value:
            site = structure[indices]
            if orbital:
                for orb, pdos in complete_dos.get_site_spd_dos(site).items():
                    # " " is used for grouping the plots.
                    if pdos_type == "none":
                        name = key + " " + str(orb)
                    else:
                        name = \
                            key + " #" + str(len(value)) + " " + str(orb)
                    density = divide_densities(pdos.densities, len(value))
                    if name in dos:
                        density = add_densities(dos[name].densities, density)
                        dos[name] = Dos(efermi, energies, density)
                    else:
                        dos[name] = Dos(efermi, energies, density)
            else:
                name = key + "(" + str(len(key)) + ")"
                pdos = complete_dos.get_site_dos(site)
                if name in dos:
                    dos[name] = add_densities(dos[name], pdos)
                else:
                    dos[name] = pdos

    # use complete_dos.efermi for total dos.
    plotter = ViseDosPlotter(zero_at_efermi=zero_at_efermi)
    plotter.add_dos_dict(dos)

    if xlim is None:
        xlim = [-10, 10]

    if ymaxs:
        ylims = [[-y, y] for y in ymaxs] \
            if v.incar.get("ISPIN", 1) == 2 else [[0, y] for y in ymaxs]
    else:
        energies = complete_dos.energies - efermi
        tdos_max = max_density(complete_dos.densities, energies, xlim,
                               crop_first_value)
        tdos_max *= 1.1
        ylims = [[-tdos_max, tdos_max]] if v.incar.get("ISPIN", 1) == 2 \
            else [[0, tdos_max]]

        pdos_max = 0.0
        for k, d in dos.items():
            if k == "Total":
                continue
            pdos_max = \
                max(max_density(d.densities, energies, xlim), pdos_max)

        pdos_max *= 1.1
        ylims.append([-pdos_max, pdos_max] if v.incar.get("ISPIN", 1) == 2
                     else [0, pdos_max])

        print("y-range", ylims)

    if show_spg:
        if sga is None:
            sga = SpacegroupAnalyzer(structure, symprec=symprec)
        sg_num_str = str(sga.get_space_group_number())
        sg = f" {sga.get_space_group_symbol()} ({sg_num_str})"
        print(f"Space group number: {sg}")
        title = f"{structure.composition} SG: {sg}"
    else:
        title = str(structure.composition)

    return plotter.get_plot(xlim=xlim,
                            ylims=ylims,
                            cbm_vbm=cbm_vbm,
                            legend=legend,
                            crop_first_value=crop_first_value,
                            title=title)


def divide_densities(density: dict,
                     denominator: float):
    """Method to didide charge density.

    Args:
        density: First density.
        denominator: Second density.

    Returns:
        {spin: np.array(density)}.
    """

    return {spin: np.array(value) / denominator
            for spin, value in density.items()}


def max_density(density: dict,
                energies: list,
                xlim: list,
                crop_first_value: bool = True) -> float:
    """Evaluate max of the density of states in the given energy range.

    Args:
        density (dict):
            Note that the first value may contains huge values when the
            lower limit of the calculation of density of states is larger than
            that of occupied states. Therefore, we need to crop the first value
            by default.
            {Spin.up: [...], Spin.down: [...] }
        energies (list):
            Energy mesh values.
        xlim (list):
             x-range with [x-min, x-max]
        crop_first_value (bool):
            Whether to crop the first value or not.

    Return (float):
        Max value in the density within the given x-range.
    """
    values = []
    for density_in_each_spin in density.values():
        for i, (d, e) in enumerate(zip(density_in_each_spin, energies)):
            if crop_first_value and i == 0:
                continue
            if xlim[0] < e < xlim[1]:
                values.append(d)

    if not values:
        raise ValueError("DOS is empty at the given energy {0[0]} - {0[1]} "
                         "range.".format(xlim))

    return max(values)
