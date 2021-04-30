# -*- coding: utf-8 -*-
#  Copyright (c) 2021. Distributed under the terms of the MIT License.
from math import prod
from pathlib import Path
from typing import List

import numpy as np
from pymatgen.io.vasp import Poscar, VolumetricData
from vise.util.logger import get_logger

logger = get_logger(__name__)

_minor = 1e-3
default_border_fractions = [0.1, 0.5, 0.8]


def write_light_weight_vol_data(volumetric_data: VolumetricData,
                                filename: Path,
                                border_fractions: List[float] = None):
    data = np.zeros(prod(volumetric_data.dim), dtype=int)
    normalized_values = (volumetric_data.data["total"]
                         / np.max(volumetric_data.data["total"])) + _minor

    border_fractions = border_fractions or default_border_fractions
    for border in border_fractions:
        # transpose needed as vasp is based on column measure (Fortran)
        data += (normalized_values > border).T.flatten()

    lines = [Poscar(volumetric_data.structure).get_string(),
             " ".join([str(d) for d in volumetric_data.dim]),
             " ".join(data.astype(str))]
    filename.write_text("\n".join(lines))


