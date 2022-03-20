# coding: utf-8
"""Generate masks and normalizations.

Masks are provided explicitly for the 3x3 prescriptions, the usual ones, but
most of them are generalizable to an higher number of points, (squared or even
not, according to the prescriptions).

The generalized prescriptions are provided as separate functions.

Since prescriptions are realized through masks, and normalization are dependent
on mass weights, even weights different from 0 or 1 could be used.

"""
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import matplotlib.pyplot as plt
import rich
import seaborn as sns


@dataclass
class Prescription:
    mask: np.ndarray
    name: Optional[str] = None
    f0: Optional[int] = None
    r0: Optional[int] = None

    def __post_init__(self):
        for i, zero in enumerate(("f0", "r0")):
            if getattr(self, zero) is None:
                setattr(self, zero, self.mask.shape[i] // 2)

        self.nullify_central()

    def __repr__(self) -> str:
        return repr(self.mask)

    def nullify_central(self):
        # set to null
        self.mask[self.f0, self.r0] = 0

    @classmethod
    def ren(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 3 point ren"
        prescr = cls(np.zeros(shape), name="Renormalization only", f0=f0, r0=r0)
        prescr.mask[prescr.f0] = 1
        prescr.nullify_central()
        return prescr

    @classmethod
    def fact(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 3 point fact"
        prescr = cls(np.zeros(shape), name="Factorization only", f0=f0, r0=r0)
        prescr.mask[:, prescr.r0] = 1
        prescr.nullify_central()
        return prescr

    @classmethod
    def sum(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 3 point correlated"
        prescr = cls(np.zeros(shape), name="Fully correlated", f0=f0, r0=r0)
        np.fill_diagonal(prescr.mask, 1)
        prescr.nullify_central()
        return prescr

    @classmethod
    def antisum(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 3 point correlated"
        prescr = cls(np.zeros(shape), name="Fully anti-correlated", f0=f0, r0=r0)
        np.fill_diagonal(prescr.mask[::-1], 1)
        prescr.nullify_central()
        return prescr

    @classmethod
    def christ(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 5 point"
        el1 = cls.ren(shape, f0=f0, r0=r0)
        el2 = cls.fact(shape, f0=f0, r0=r0)
        return cls(np.logical_or(el1.mask, el2.mask) * 1.0, name="Christ", f0=f0, r0=r0)

    @classmethod
    def standrews(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 5 point correlated"
        el1 = cls.sum(shape, f0=f0, r0=r0)
        el2 = cls.antisum(shape, f0=f0, r0=r0)
        return cls(
            np.logical_or(el1.mask, el2.mask) * 1.0, name="St Andrews", f0=f0, r0=r0
        )

    @classmethod
    def tridiag(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 5 point correlated"
        prescr = cls(np.zeros(shape), name="Tridiagonal", f0=f0, r0=r0)
        np.fill_diagonal(prescr.mask, 1)
        np.fill_diagonal(prescr.mask[1:], 1)
        np.fill_diagonal(prescr.mask[:, 1:], 1)
        prescr.nullify_central()
        return prescr

    @classmethod
    def antitridiag(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 5 point correlated"
        prescr = cls(np.zeros(shape), name="Anti-tridiagonal", f0=f0, r0=r0)
        np.fill_diagonal(prescr.mask[::-1], 1)
        np.fill_diagonal(prescr.mask[::-1, 1:], 1)
        np.fill_diagonal(prescr.mask[-2::-1, :], 1)
        prescr.nullify_central()
        return prescr

    @classmethod
    def incoherent(
        cls, shape: Sequence[int], f0: Optional[int] = None, r0: Optional[int] = None
    ):
        "a.k.a. 9 point"
        prescr = cls(np.ones(shape), name="Fully incoherent", f0=f0, r0=r0)
        return prescr


def masks_nbyn(n: int = 3) -> dict[str, Prescription]:
    """Create integer masks' dictionary.

    Note
    ----
    The central scale is always enabled, but actually is never contributing:
    since the vector is a vector of shifts, the central one is always null, even
    without masking it.

    Returns
    -------
    dict
      a dictionary with all the different prescriptions for the 3x3 scales

    """
    names = ["3", "3b", "3c", "3cb", "5", "5b", "7", "7b", "9"]
    prescriptions = {name: Prescription(np.zeros((3, 3)), name) for name in names}

    prescriptions["3"] = Prescription.ren((n, n))
    prescriptions["3b"] = Prescription.fact((n, n))
    prescriptions["3c"] = Prescription.sum((n, n))
    prescriptions["3cb"] = Prescription.antisum((n, n))
    prescriptions["5"] = Prescription.christ((n, n))
    prescriptions["5b"] = Prescription.standrews((n, n))
    prescriptions["7"] = Prescription.tridiag((n, n))
    prescriptions["7b"] = Prescription.antitridiag((n, n))
    prescriptions["9"] = Prescription.incoherent((n, n))

    return prescriptions


def s(mask: np.ndarray) -> int:
    """Number of independent scales."""
    s = 0

    if mask.sum() > 1:
        s += 1
    if any(
        any(mask.sum(axis) > 1) and all(mask.sum((axis + 1) % 2)) for axis in (0, 1)
    ):
        s += 1

    return s


def m(mask: np.ndarray) -> int:
    """Number of prescription's points.

    Possibly weighted, for non-binary masks.

    """
    return np.sum(mask)


def normalization(mask: np.ndarray) -> float:
    """Normalization for given prescription"""
    return s(mask) / m(mask)


def plot_prescription(prescr: Prescription):
    plt.title(prescr.name)
    sns.heatmap(prescr.mask)
    plt.show()


def pprint_prescription(prescr: Prescription):
    rich.print(f"[green b]{prescr.name}[/], m: {m(prescr.mask)}, s: {s(prescr.mask)}")
    rich.print(*(f"    {line}" for line in str(prescr).splitlines()), sep="\n")