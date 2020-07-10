# -*- coding: utf-8 -*-

#  Copyright (c) 2020. Distributed under the terms of the MIT License.

import re

from pymatgen.electronic_structure.plotter import BSPlotter
from pymatgen.io.vasp import Vasprun
from pymatgen.util.string import latexify
from vise.analyzer.plot_band import BandPlotInfo, BandInfo, XTicks, BandEdge


def greek_to_unicode(label: str) -> str:
    d = {"GAMMA": "Γ", "SIGMA": "Σ", "DELTA": "Δ"}
    for k, v in d.items():
        label = label.replace(k, v)
    return label


def italic_to_roman(label: str) -> str:
    return re.sub(r"([A-Z])_([0-9])", r"{\\rm \1}_\2", label)


class VaspBandPlotInfo(BandPlotInfo):
    def __init__(self,
                 vasprun: Vasprun,
                 kpoints_filename: str,
                 vasprun2: Vasprun = None):

        bs = vasprun.get_band_structure(kpoints_filename, line_mode=True)
        plot_data = BSPlotter(bs).bs_plot_data(zero_to_efermi=False)
        self._composition = vasprun.final_structure.composition

        band_info = [BandInfo(band_energies=self._remove_spin_key(plot_data),
                              band_edge=self._band_edge(bs, plot_data),
                              fermi_level=bs.efermi)]

        if vasprun2:
            bs2 = vasprun2.get_band_structure(kpoints_filename, line_mode=True)
            plot_data2 = BSPlotter(bs2).bs_plot_data(zero_to_efermi=False)
            band_info.append(
                BandInfo(band_energies=self._remove_spin_key(plot_data2),
                         band_edge=self._band_edge(bs2, plot_data2),
                         fermi_level=bs.efermi))

        super().__init__(band_info_set=band_info,
                         distances_by_branch=plot_data["distances"],
                         x_ticks=self._x_ticks(plot_data),
                         title=self._title)

    @staticmethod
    def _remove_spin_key(plot_data):
        result = []
        for _, branch_energies in enumerate(plot_data["energy"]):
            result.append([energy_by_spin for energy_by_spin
                           in branch_energies.values()])

        return result

    def _x_ticks(self, plot_data):
        labels = self._sanitize_labels(plot_data["ticks"]["label"])
        distances = plot_data["ticks"]["distance"]
        return XTicks(labels=labels, distances=distances)

    def _band_edge(self, bs, plot_data):
        if bs.is_metal():
            return None
        else:
            return BandEdge(
                vbm=plot_data["vbm"][0][1],
                cbm=plot_data["cbm"][0][1],
                vbm_distances=[i[0] for i in plot_data["vbm"]],
                cbm_distances=[i[0] for i in plot_data["cbm"]])

    @property
    def _title(self):
        return latexify(self._composition.reduced_formula)

    @staticmethod
    def _sanitize_labels(labels):
        return [italic_to_roman(greek_to_unicode(label)) for label in labels]
