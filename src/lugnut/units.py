from typing import Literal

DistanceUnit = Literal["km", "mi"]
VolumeUnit = Literal["L", "gal_us", "gal_imp"]

KM_PER_MI = 1.609344
L_PER_GAL = {"L": 1.0, "gal_us": 3.785411784, "gal_imp": 4.54609}


def km_from(value: float, unit: DistanceUnit) -> int:
    return round(value * (KM_PER_MI if unit == "mi" else 1))


def km_to(km: int, unit: DistanceUnit) -> float:
    return round(km / (KM_PER_MI if unit == "mi" else 1), 1)


def l_from(value: float, unit: VolumeUnit) -> float:
    return value * L_PER_GAL[unit]


def l_to(litres: float, unit: VolumeUnit) -> float:
    return litres / L_PER_GAL[unit]
