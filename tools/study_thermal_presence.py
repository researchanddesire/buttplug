"""Preliminary cap warm-up study; this does not classify or certify wear.

Requires numpy, scipy and matplotlib. Run from any directory. --extract-geometry
also requires FreeCAD/Part and refreshes only this study's geometry snapshot.
The cap is an axisymmetric approximation, with an unqualified sensor lag.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.sparse import coo_matrix, bmat, csr_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware/design/thermal-presence"
ASSET = ROOT / "developer-docs/docs/assets/thermal-presence.png"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_geometry():
    # Read the saved STEP exports; never open/save or mutate a product native.
    sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
    import FreeCAD  # Initialize the native runtime before importing Part.
    import Part
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps
    base = ROOT / "hardware/cad/manufacturing-layout"
    report = json.loads((base / "review.json").read_text())
    data = {"length_unit": "mm", "sources": {}, "parts": {}}
    for name in ("MetalBody", "MotorThermistorCap"):
        path = base / f"{name}.step"
        expected = report["verified_parts"][name]["STEP_sha256"]
        assert digest(path) == expected, f"Unbound STEP: {name}"
        shape = Part.Shape()
        shape.read(str(path))
        assert shape.isValid() and len(shape.Solids) == 1
        props = GProp_GProps()
        brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(shape), props,
                                    1e-10, True, True, False, False, False)
        volume = props.Mass()
        native_volume = report["verified_parts"][name]["native_adaptive_volume_mm3"]
        assert abs(volume - native_volume) < 0.1
        data["sources"][str(path.relative_to(ROOT))] = digest(path)
        data["parts"][name] = {"volume_mm3": volume}
        if name == "MotorThermistorCap":
            dome = [f for f in shape.Faces if f.BoundBox.YMax > 98]
            assert len(dome) == 1 and abs(dome[0].BoundBox.YMin - 64) < 1e-5
            data["dome_area_mm2"] = dome[0].Area
    for path in (base / "review.json", base / "ManufacturingLayout.FCStd"):
        data["sources"][str(path.relative_to(ROOT))] = digest(path)
    assert digest(base / "ManufacturingLayout.FCStd") == report["native_sha256"]
    data["sensor_drill"] = report["cap_sensor"]
    data["sensor_head_reference"] = {
        "r_mm": 7.8, "y_center_mm": 89.7, "diameter_mm": 1.2,
        "length_mm": 1.2,
        "source": "tools/build_manufacturing_layout.py, TipThermistorHeadReference",
    }
    data["sources"]["tools/build_manufacturing_layout.py"] = digest(
        ROOT / "tools/build_manufacturing_layout.py")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "geometry.json").write_text(json.dumps(data, indent=2) + "\n")


def outer_radius(y):
    if y < 55.75:
        return 13.5 + (y - 54.75) * (14.07985 - 13.5)
    if y < 61.75:
        return 14.07985
    if y < 64:
        return 13.8
    return 18.669 * math.sqrt(max(0.0, 1 - ((y - 55) / 43.1) ** 2))


def inner_radius(y):
    return 12.25 if y < 78 else (5.55 if y < 93.3 else 0.0)


def dome_area(y0, y1):
    # Integrate in ellipse angle to avoid the infinite dr/dy at the nose.
    a, b = 18.669e-3, 43.1e-3
    t0 = math.acos(np.clip((y1 - 55) / 43.1, -1, 1))
    t1 = math.acos(np.clip((y0 - 55) / 43.1, -1, 1))
    return quad(lambda t: 2 * math.pi * a * math.sin(t)
                * math.hypot(a * math.cos(t), b * math.sin(t)), t0, t1,
                epsabs=1e-12)[0]


class CapMesh:
    def __init__(self, pitch_mm):
        # Align axial rows with the rear entry, shoulders and motor stop.
        edges = []
        for lo, hi in zip((54.75, 55.75, 61.75, 64, 78, 93.3),
                          (55.75, 61.75, 64, 78, 93.3, 98.1)):
            edges.extend(np.linspace(lo, hi, math.ceil((hi-lo)/pitch_mm)+1)[:-1])
        self.edges = np.array(edges + [98.1])
        self.y = (self.edges[1:] + self.edges[:-1]) / 2
        self.dy = np.diff(self.edges) * 1e-3
        self.dr = pitch_mm * 1e-3
        nr = math.ceil(18.669/pitch_mm)
        self.ids = {}
        coords, volumes = [], []
        for j, y in enumerate(self.y):
            for i in range(nr):
                r = (i + 0.5) * pitch_mm
                if inner_radius(y) <= r <= outer_radius(y):
                    self.ids[j, i] = len(coords)
                    coords.append((r, y))
                    volumes.append(2 * math.pi * r * 1e-3 * self.dr * self.dy[j])
        self.coords = np.array(coords)
        self.volumes = np.array(volumes)
        self.n = len(coords)
        rows, cols, vals = [], [], []
        diagonal = np.zeros(self.n)
        for (j, i), p in self.ids.items():
            for key, factor in (
                ((j, i+1), 2 * math.pi * (i+1) * self.dy[j]),
                ((j+1, i), 2 * math.pi * (i+0.5) * self.dr ** 2
                 / ((self.dy[j] + self.dy[j+1])/2) if j+1 < len(self.dy) else 0),
            ):
                if key in self.ids:
                    q = self.ids[key]
                    # 'factor' is area/distance, in metres; k is applied later.
                    diagonal[p] -= factor
                    diagonal[q] -= factor
                    rows.extend((p, q)); cols.extend((q, p)); vals.extend((factor, factor))
        rows.extend(range(self.n)); cols.extend(range(self.n)); vals.extend(diagonal)
        self.conduction = coo_matrix((vals, (rows, cols)), shape=(self.n, self.n)).tocsr()
        self.area = np.zeros(self.n)
        self.wall_distance = np.zeros(self.n)
        for j, y in enumerate(self.y):
            if y < 64:
                continue
            last = max(i for jj, i in self.ids if jj == j)
            p = self.ids[j, last]
            self.area[p] = dome_area(self.edges[j], self.edges[j+1])
            radius = outer_radius(y)
            slope = -18.669 ** 2 * (y-55) / (43.1 ** 2 * radius)
            self.wall_distance[p] = (radius - self.coords[p, 0]) * 1e-3 / math.hypot(1, slope)
        # Two radial walls of the omitted offset drill, at the bead's axial centre.
        # Equal weighting is a study assumption, not a measured potting conductance.
        self.sensor_weights = np.zeros(self.n)
        for r in (6.55, 9.05):
            distances = ((self.coords - (r, 89.7)) ** 2).sum(axis=1)
            self.sensor_weights[np.argmin(distances)] += 0.5

    def solve(self, material, h, tau=3.0, initial=22.0, bath=37.0,
              duration=1200.0, coating_m=0.0, coating_k=0.2,
              capacity_scale=1.0, targets=(23.0, 24.0, 34.0)):
        k, rho, cp = (material[x] for x in ("k_W_mK", "rho_kg_m3", "cp_J_kgK"))
        capacity = rho * cp * self.volumes * capacity_scale
        conductance = self.area / (1/h + self.wall_distance/k + coating_m/coating_k)
        heat = self.conduction * k - coo_matrix(
            (conductance, (np.arange(self.n), np.arange(self.n))), shape=(self.n, self.n))
        op = heat.multiply((1/capacity)[:, None]).tocsr()
        # Sensor is a passive, negligible-mass observation filter, not a heat sink.
        jac = bmat([[op, csr_matrix((self.n, 1))],
                    [csr_matrix(self.sensor_weights[None, :] / tau),
                     csr_matrix([[-1/tau]])]], format="csc")
        def event(target):
            def crossing(t, theta):
                return theta[-1] + bath - target
            crossing.direction = 1 if bath > initial else -1
            return crossing
        solution = solve_ivp(lambda t, z: jac @ z, (0, duration),
                             np.full(self.n+1, initial-bath), method="BDF",
                             jac=jac, rtol=2e-7, atol=2e-8,
                             events=[event(t) for t in targets])
        assert solution.success, solution.message
        times = [0.0 if (initial >= target if bath > initial else initial <= target)
                 else (float(t[0]) if len(t) else None)
                 for target, t in zip(targets, solution.t_events)]
        # Passive network maximum principle and energy balance on every solver step.
        assert solution.y.min() >= min(initial-bath, 0) - 1e-5
        assert solution.y.max() <= max(initial-bath, 0) + 1e-5
        metal = solution.y[:-1]
        rate = op @ metal
        energy_rate = capacity @ rate
        boundary_rate = -(conductance @ metal)
        residual = float(np.max(np.abs(energy_rate-boundary_rate)))
        assert residual < 1e-7
        return {
            "threshold_seconds": dict(zip((str(t) for t in targets), times)),
            "time_s": solution.t.tolist(),
            "sensor_C": (solution.y[-1] + bath).tolist(),
            "mean_cap_C": ((self.volumes @ metal)/self.volumes.sum() + bath).tolist(),
            "energy_balance_residual_W": residual,
            "h_W_m2K": h, "sensor_tau_s": tau, "initial_C": initial,
            "bath_C": bath, "coating_m": coating_m, "capacity_scale": capacity_scale,
        }


def run():
    inputs = json.loads((OUT / "inputs.json").read_text())
    geometry = json.loads((OUT / "geometry.json").read_text())
    for path, expected in geometry["sources"].items():
        assert digest(ROOT/path) == expected, f"Geometry source changed: {path}"
    mesh = CapMesh(0.25)
    exact_cap = geometry["parts"]["MotorThermistorCap"]["volume_mm3"]
    exact_body = geometry["parts"]["MetalBody"]["volume_mm3"]
    assert abs(mesh.area.sum()*1e6/geometry["dome_area_mm2"] - 1) < 0.001
    assert abs(mesh.volumes.sum()*1e9/exact_cap - 1) < 0.015
    assert np.max(np.abs(np.asarray(mesh.conduction.sum(axis=1)))) < 1e-12
    results = {
        "status": "UNVALIDATED_ENGINEERING_SCREEN_NOT_WEAR_DETECTION",
        "inputs_sha256": digest(OUT/"inputs.json"), "geometry_sha256": digest(OUT/"geometry.json"),
        "script_sha256": digest(__file__),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                    "scipy": version("scipy"), "matplotlib": version("matplotlib")},
        "mesh": {"pitch_mm": 0.25, "cells": mesh.n,
                 "volume_mm3": float(mesh.volumes.sum()*1e9),
                 "actual_cap_volume_mm3": exact_cap,
                 "heated_area_mm2": float(mesh.area.sum()*1e6)},
        "materials": {}, "convergence": [], "sensitivities": {},
    }
    records = []
    for key, material in inputs["materials"].items():
        print(f"Solving {key}", flush=True)
        rho, cp, k = (material[x] for x in ("rho_kg_m3", "cp_J_kgK", "k_W_mK"))
        runs = {str(h): mesh.solve(material, h) for h in inputs["contact_h_W_m2K"]}
        results["materials"][key] = {
            "metal_body_cap_mass_g": (exact_body+exact_cap)*1e-6*rho,
            "cap_heat_capacity_J_K": exact_cap*1e-9*rho*cp,
            "diffusivity_mm2_s": k/(rho*cp)*1e6,
            "runs": runs,
            "lumped_cap_seconds": {
                str(h): {str(target): -exact_cap*1e-9*rho*cp/(h*mesh.area.sum())
                         * math.log((37-target)/15) for target in (23, 24, 34)}
                for h in inputs["contact_h_W_m2K"]},
        }
        for h, run in runs.items():
            records.append({"material": key, "h_W_m2K": h,
                            **{f"time_to_{target}C_s": seconds
                               for target, seconds in run["threshold_seconds"].items()}})
    steel = inputs["materials"]["316L"]
    nominal = results["materials"]["316L"]["runs"]["150"]
    for pitch in (0.5, 0.125):
        refined = CapMesh(pitch)
        trial = refined.solve(steel, 150)
        results["convergence"].append({"pitch_mm": pitch, "cells": refined.n,
            "volume_mm3": float(refined.volumes.sum()*1e9),
            "threshold_seconds": trial["threshold_seconds"]})
    fine = results["convergence"][-1]["threshold_seconds"]
    for target, value in nominal["threshold_seconds"].items():
        assert abs(value-fine[target]) / fine[target] < 0.05
    for tau in (1, 10):
        results["sensitivities"][f"sensor_tau_{tau}s"] = mesh.solve(steel, 150, tau=tau)
    for start in (12, 32, 36):
        results["sensitivities"][f"start_{start}C"] = mesh.solve(
            steel, 150, initial=start, targets=(start+1, start+2, 34.0))
    results["sensitivities"]["1mm_polymer_k0.2"] = mesh.solve(steel, 150, coating_m=0.001)
    # Artificial added-capacity stress case, not an assembly heat-flow simulation.
    results["sensitivities"]["body_mass_no_extra_area"] = mesh.solve(
        steel, 150, capacity_scale=(exact_body+exact_cap)/exact_cap)
    for h in (5, 15):
        results["sensitivities"][f"removal_air_h{h}"] = mesh.solve(
            steel, h, initial=37, bath=22, duration=2400, targets=(36, 34, 30))
    # In the high-k limit, the spatial mean must approach the lumped energy model.
    limit = {**steel, "k_W_mK": 15000}
    high_k = mesh.solve(limit, 150)
    lump_time = mesh.volumes.sum()*steel["rho_kg_m3"]*steel["cp_J_kgK"] / (150*mesh.area.sum())
    mean_exact = 37 - 15*np.exp(-np.array(high_k["time_s"])/lump_time)
    error = float(np.max(np.abs(mean_exact-np.array(high_k["mean_cap_C"]))))
    assert error < 0.02
    results["checks"] = {"energy_and_temperature_bounds": "PASS", "source_hashes": "PASS",
                         "high_k_lumped_mean_max_error_C": error,
                         "mesh_refinement_threshold_relative_limit": 0.05}
    (OUT/"results.json").write_text(json.dumps(results, indent=2, allow_nan=False)+"\n")
    with (OUT/"warmup-times.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    plot(inputs, results)
    print(json.dumps({"mesh": results["mesh"], "times": records,
                      "convergence": results["convergence"], "checks": results["checks"]}, indent=2))


def plot(inputs, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    colors = {"316L": "#2563a6", "Ti-grade-2": "#16816a", "C10100": "#b96024"}
    for key, material in inputs["materials"].items():
        runs = results["materials"][key]["runs"]
        for index, xmax in ((0, 60), (1, 600)):
            ax = axes[0, index]
            nominal, low, high = (runs[str(h)] for h in (150, 50, 500))
            t = np.linspace(0, xmax, 500)
            ax.fill_between(t, np.interp(t, low["time_s"], low["sensor_C"]),
                            np.interp(t, high["time_s"], high["sensor_C"]), color=colors[key], alpha=.09)
            ax.plot(nominal["time_s"], nominal["sensor_C"], label=material["label"], color=colors[key], lw=2)
            ax.set(xlim=(0, xmax), ylim=(22, 37.5), xlabel="Time (s)", ylabel="Modeled sensor temperature (°C)")
            ax.grid(alpha=.2)
    axes[0, 0].set_title("Early response, 22 → 37°C")
    axes[0, 1].set_title("Approaching body temperature takes longer")
    axes[0, 0].legend(loc="lower right", frameon=False)
    axes[0, 1].axhline(34, color="#777777", ls=":", lw=1)
    ax = axes[1, 0]
    cases = {"Nominal sensor lag 3s": results["materials"]["316L"]["runs"]["150"],
             "Sensor lag 10s": results["sensitivities"]["sensor_tau_10s"],
             "1mm polymer, k=0.2": results["sensitivities"]["1mm_polymer_k0.2"],
             "Added body mass; same area": results["sensitivities"]["body_mass_no_extra_area"]}
    for label, case in cases.items():
        ax.plot(case["time_s"], case["sensor_C"], label=label, lw=1.8)
    ax.set(title="316L mounting / coating / mass sensitivity", xlim=(0, 120), ylim=(22, 33),
           xlabel="Time (s)", ylabel="Modeled sensor temperature (°C)")
    ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.2)
    ax = axes[1, 1]
    for h in (5, 15):
        case = results["sensitivities"][f"removal_air_h{h}"]
        ax.plot(np.array(case["time_s"])/60, case["sensor_C"], label=f"Air h={h} W/m²K", lw=2)
    ax.axhline(34, color="#777777", ls=":", lw=1)
    ax.set(title="Removal: retained warmth delays temperature evidence", xlim=(0, 40), ylim=(22, 38),
           xlabel="Time after removal (min)", ylabel="Modeled sensor temperature (°C)")
    ax.legend(frameon=False); ax.grid(alpha=.2)
    fig.suptitle("Preliminary cap thermal study — unvalidated, not proof of insertion", fontsize=16)
    fig.supxlabel("Warm-up: h=150 W/m²K, sensor lag=3s. Shading: h=50–500 (assumptions, not confidence intervals). Air cases labeled.", fontsize=10)
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSET, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-geometry", action="store_true")
    args = parser.parse_args()
    if args.extract_geometry:
        extract_geometry()
    run()
