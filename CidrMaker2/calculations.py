"""Pure production calculations. No GUI dependencies, so they can be tested independently."""
from __future__ import annotations
import math

def _num(value, default=0.0):
    try:
        n = float(value)
        return n if math.isfinite(n) else default
    except (ValueError, TypeError):
        return default

def pressure_from_sugar(sugar_g_l):
    return max(0.0, _num(sugar_g_l)) / 4.0

def sugar_from_pressure(pressure_bar):
    return max(0.0, _num(pressure_bar)) * 4.0

def brix_to_sg(brix):
    b = _num(brix, float("nan"))
    if not math.isfinite(b): return float("nan")
    return 1 + b / (258.6 - ((b / 258.2) * 227.1))

def sg_to_brix(sg):
    s = _num(sg, float("nan"))
    if not math.isfinite(s) or s <= 0: return float("nan")
    return 258.6 * ((s - 1) / (258.6 - 227.1 * (s - 1)))

def terrill_sg(original_brix, observed_brix):
    r, b = _num(observed_brix, float("nan")), _num(original_brix, float("nan"))
    if not math.isfinite(r) or not math.isfinite(b): return float("nan")
    return (1.001843 - 0.002318474*r - 0.000007775*r*r - 0.000000034*r**3
            + 0.00574*b + 0.00003344*b*b + 0.000000086*b**3)

def calculate_petnat(s):
    og = _num(s.get("originalBrix"), float("nan"))
    refr = _num(s.get("refractometerBrix"), float("nan"))
    hyd = _num(s.get("hydrometerSG"), float("nan"))
    pressure = _num(s.get("desiredPressure"), 5)
    if s.get("pressureUnit", "bar") == "atm": pressure *= 1.01325
    corrected_sg = hyd if math.isfinite(hyd) and hyd > 0 else float("nan")
    if math.isfinite(refr) and math.isfinite(og):
        corrected = terrill_sg(og, refr)
        if not math.isfinite(corrected_sg): corrected_sg = corrected
    corrected_brix = sg_to_brix(corrected_sg)
    abv_input = _num(s.get("measurementAlcohol"), 0)
    if abv_input > 0:
        abv = abv_input
    elif math.isfinite(corrected_sg) and math.isfinite(og):
        abv = max(0.0, (brix_to_sg(og) - corrected_sg) * 131.25)
    else:
        abv = float("nan")
    residual = _num(s.get("estimatedResidualSugar"), float("nan"))
    warnings = []
    if not math.isfinite(residual) or residual < 0:
        residual = max(0.0, corrected_brix * 10) if math.isfinite(corrected_brix) else float("nan")
        if math.isfinite(residual):
            warnings.append("Остаточный сахар оценён по Brix-equivalent, это не лабораторный анализ.")
    current_pressure = pressure_from_sugar(residual) if math.isfinite(residual) else float("nan")
    max_bottle = _num(s.get("maxBottlePressure"), 4.5)
    margin = min(90.0, max(0.0, _num(s.get("safetyMargin"), 15))) / 100
    if math.isfinite(current_pressure) and current_pressure >= max_bottle * (1-margin):
        warnings.append(f"ОПАСНО: оценка {current_pressure:.2f} bar близка к пределу бутылки с учётом запаса.")
    if not math.isfinite(refr) and not math.isfinite(hyd):
        warnings.append("Нет текущего Brix/SG: оценить фактический остаточный сахар нельзя.")
    warnings.append("Калькулятор даёт оценку, а не гарантию давления. Для розлива подтвердите остаточный сахар, температуру и рейтинг бутылки.")
    target_sugar = sugar_from_pressure(pressure)
    return {"correctedSG": corrected_sg, "correctedBrix": corrected_brix, "estimatedABV": abv,
            "residualSugar": residual, "pressureBar": current_pressure,
            "targetSugar": target_sugar, "targetBrixEquivalent": target_sugar/10,
            "warnings": warnings}

def solera_recalculate(stage3):
    ops = stage3.setdefault("operations", [])
    current_volume = max(0.0, _num(stage3.get("volume"), _num(stage3.get("initialVolume"))))
    current_age = max(0.0, _num(stage3.get("averageAgeYears")))
    raw_initial = stage3.get("initialVolume")
    if raw_initial not in (None, "") and _num(raw_initial) > 0:
        initial_volume = max(0.0, _num(raw_initial))
    elif ops:
        first = ops[0]
        if first.get("volumeBefore") not in (None, ""):
            initial_volume = max(0.0, _num(first.get("volumeBefore")))
        else:
            initial_volume = current_volume
            for op in reversed(ops):
                initial_volume = max(0.0, initial_volume + max(0.0, _num(op.get("removed"))) - max(0.0, _num(op.get("added"))))
        stage3["initialVolume"] = round(initial_volume, 3)
    else:
        initial_volume = current_volume
        stage3["initialVolume"] = round(initial_volume, 3)

    if stage3.get("initialAverageAgeYears") not in (None, ""):
        initial_age = max(0.0, _num(stage3.get("initialAverageAgeYears")))
    elif ops:
        age_after, volume_after = current_age, current_volume
        for op in reversed(ops):
            removed = max(0.0, _num(op.get("removed")))
            added = max(0.0, _num(op.get("added")))
            before = _num(op.get("volumeBefore"), volume_after - added + removed)
            if before <= 0: before = max(0.0, volume_after - added + removed)
            remaining = max(0.0, before - removed)
            source_age = max(0.0, _num(op.get("sourceAgeYears")))
            if remaining > 0:
                age_after = max(0.0, (age_after * volume_after - source_age * added) / remaining)
            volume_after = before
        initial_age = age_after
        stage3["initialAverageAgeYears"] = round(initial_age, 3)
    else:
        initial_age = current_age
        stage3["initialAverageAgeYears"] = round(initial_age, 3)

    volume, age = initial_volume, initial_age
    for op in sorted(ops, key=lambda x: str(x.get("date", ""))):
        removed, added = max(0.0, _num(op.get("removed"))), max(0.0, _num(op.get("added")))
        before = volume
        after = before - removed + added
        if removed > before:
            op["warning"] = "Отбор превышает доступный объём"
            after = max(0.0, after)
        else:
            op.pop("warning", None)
        source_age = max(0.0, _num(op.get("sourceAgeYears")))
        if after > 0:
            age = max(0.0, (age * max(0.0, before-removed) + source_age * added) / after)
        volume = after
        op["volumeBefore"] = round(before, 3)
        op["volumeAfter"] = round(after, 3)
    stage3["volume"] = round(volume, 3)
    stage3["averageAgeYears"] = round(age, 2)
    return volume, age
