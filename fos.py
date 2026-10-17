"""Infinite-slope Factor of Safety with pore-water pressure from soil saturation.

FoS = [ c' + (gamma*z*cos^2(beta) - u) * tan(phi') ] / ( gamma*z*sin(beta)*cos(beta) )
u   = gamma_w * m * z * cos^2(beta)         m = saturated fraction of the soil column (0..1)
"""
from dataclasses import dataclass
import math

GAMMA_W = 9.81  # kN/m^3


@dataclass
class SoilParams:
    cohesion_kpa: float = 10.0       # c'
    friction_deg: float = 33.0       # phi'
    unit_weight: float = 18.0        # gamma, kN/m^3
    depth_m: float = 2.0             # failure-plane depth z


def factor_of_safety(slope_deg: float, saturation: float, p: SoilParams = SoilParams()) -> float:
    beta = math.radians(max(slope_deg, 0.1))
    m = min(max(saturation, 0.0), 1.0)
    cos2 = math.cos(beta) ** 2
    u = GAMMA_W * m * p.depth_m * cos2
    resisting = p.cohesion_kpa + (p.unit_weight * p.depth_m * cos2 - u) * math.tan(math.radians(p.friction_deg))
    driving = p.unit_weight * p.depth_m * math.sin(beta) * math.cos(beta)
    return resisting / driving


def risk_level(fos: float) -> str:
    if fos < 1.2:
        return "EVACUATE"
    if fos < 1.5:
        return "WATCH"
    return "NORMAL"


if __name__ == "__main__":
    for sat in (0.2, 0.6, 1.0):
        f = factor_of_safety(slope_deg=30, saturation=sat)
        print(f"slope 30 deg, saturation {sat:.1f} -> FoS {f:.2f} ({risk_level(f)})")
