from __future__ import annotations

"""v2 ratio specification: loader and fail-closed validator.

The v1 set carried 33 ratios across two files: ``config/ratios.json`` held the
formulas and ``config/sectors.json`` held the per-sector ``allowed_ratios``
lists.  Splitting a ratio's definition across two files is why nobody noticed
that BANK ended up with 10 eligible CORE ratios against NONFIN's 26, which in
turn capped a bank's ``ek1`` at 10/18 = 0.56 and made the ``good_count < 5``
veto roughly 2.6x easier to trip for a bank than for an industrial.  In v2 a
ratio declares its own sector applicability, so that class of drift cannot
recur.

Nothing here computes a score.  This module only answers "is this ratio set
internally consistent", and does so loudly: every violation raises, none warn.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import ast
import json


DIRECTIONS = ("HIGHER_BETTER", "LOWER_BETTER", "BAND")
OUT_OF_DOMAIN = ("MISSING", "BEST", "WORST", "NOT_APPLICABLE")
TRANSFORMS = (None, "signed_log", "clip")
ROLE_SCORED = "SCORED"
ROLE_INTERMEDIATE = "INTERMEDIATE"

# Functions the v1 AST evaluator (ratios_calc.safe_eval_expr) accepts.  A v2
# formula reaching for anything else would raise at compute time on live data;
# it is rejected at load time instead.
ALLOWED_FUNCS = frozenset(
    {"avg", "lag", "lag4q", "sum4q", "ttm", "abs", "coalesce", "nz",
     "days_in_period", "log", "log1p", "max", "min"}
)


class RatioSpecError(ValueError):
    pass


@dataclass(frozen=True)
class Anchor:
    weak: float
    strong: float

    def score(self, value: float) -> float:
        """Map an absolute level onto [0.05, 0.95]; weak -> 0.30, strong -> 0.80.

        Direction is already encoded in the ordering: for a LOWER_BETTER ratio
        ``weak`` is numerically greater than ``strong``.  A pure percentile
        always crowns somebody, even in a quarter when the whole market is bad;
        the anchor is what lets a score say nobody is good.
        """
        span = self.strong - self.weak
        if span == 0:
            raise RatioSpecError("anchor weak ve strong esit olamaz")
        t = (value - self.weak) / span
        return max(0.05, min(0.95, 0.30 + t * 0.50))


@dataclass(frozen=True)
class RatioSpec:
    name: str
    role: str
    pillar: str
    family: str
    formula: str
    requires: tuple[str, ...]
    domain: tuple[str, ...]
    direction: str | None = None
    out_of_domain: str = "MISSING"
    anchor: Anchor | None = None
    band: Mapping[str, float] | None = None
    applies_to: frozenset[str] = frozenset()
    winsor: float = 0.02
    transform: str | None = None
    clip: Mapping[str, float] | None = None

    @property
    def is_scored(self) -> bool:
        return self.role == ROLE_SCORED

    def applicable_to(self, group: str) -> bool:
        return self.is_scored and group in self.applies_to


@dataclass(frozen=True)
class RatioSet:
    version: str
    field_set_version: str
    families: Mapping[str, str]
    sector_groups: frozenset[str]
    specs: Mapping[str, RatioSpec]
    order: tuple[str, ...]
    _composites: Mapping[str, tuple[str, ...]]
    _pillar_shares_default: Mapping[str, float]
    _pillar_shares_by_group: Mapping[str, Mapping[str, float]]

    def scored(self) -> tuple[RatioSpec, ...]:
        return tuple(self.specs[n] for n in self.order if self.specs[n].is_scored)

    def intermediates(self) -> tuple[RatioSpec, ...]:
        return tuple(self.specs[n] for n in self.order if not self.specs[n].is_scored)

    def applicable(self, group: str) -> tuple[RatioSpec, ...]:
        if group not in self.sector_groups:
            raise RatioSpecError(f"bilinmeyen sektor grubu: {group!r}")
        return tuple(s for s in self.scored() if s.applicable_to(group))

    def families_of(self, group: str) -> tuple[str, ...]:
        seen: list[str] = []
        for spec in self.applicable(group):
            if spec.family not in seen:
                seen.append(spec.family)
        return tuple(seen)

    def composites(self) -> Mapping[str, tuple[str, ...]]:
        return self._composites

    def pillar_of_composite(self, composite: str) -> tuple[str, ...]:
        if composite not in self._composites:
            raise RatioSpecError(f"bilinmeyen kompozit: {composite!r}")
        return self._composites[composite]

    def pillar_shares(self, group: str) -> Mapping[str, float]:
        if group not in self.sector_groups:
            raise RatioSpecError(f"bilinmeyen sektor grubu: {group!r}")
        override = self._pillar_shares_by_group.get(group)
        return dict(override) if override else dict(self._pillar_shares_default)


def _obj(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RatioSpecError(f"{name} nesne olmali")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RatioSpecError(f"{name} dolu metin olmali")
    return value.strip()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RatioSpecError(f"{name} sayi olmali")
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise RatioSpecError(f"{name} sonlu olmali")
    return out


def _str_tuple(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise RatioSpecError(f"{name} liste olmali")
    return tuple(_text(v, f"{name}[]") for v in value)


def load_field_registry(path: str | Path) -> dict[str, dict]:
    data = _obj(json.loads(Path(path).read_text(encoding="utf-8")), "field registry")
    fields = _obj(data.get("fields"), "fields")
    if not fields:
        raise RatioSpecError("field registry bos olamaz")
    for fname, fdef in fields.items():
        fdef = _obj(fdef, f"fields.{fname}")
        _text(fdef.get("tier"), f"fields.{fname}.tier")
        _text(fdef.get("flow"), f"fields.{fname}.flow")
    return {str(k): dict(v) for k, v in fields.items()}


def _formula_names(formula: str, ratio_name: str) -> set[str]:
    """Identifiers a formula reads, after rejecting disallowed calls."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise RatioSpecError(f"{ratio_name}: formul ayristirilamadi") from exc

    names: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func.id if isinstance(node.func, ast.Name) else None
            if fn is None or fn not in ALLOWED_FUNCS:
                raise RatioSpecError(f"{ratio_name}: izin verilmeyen fonksiyon {fn!r}")
            called.add(fn)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names - called


def _parse_anchor(raw: Any, name: str, direction: str | None) -> Anchor | None:
    if raw is None:
        return None
    obj = _obj(raw, f"{name}.anchor")
    weak = _number(obj.get("weak"), f"{name}.anchor.weak")
    strong = _number(obj.get("strong"), f"{name}.anchor.strong")
    if weak == strong:
        raise RatioSpecError(f"{name}.anchor weak ve strong esit olamaz")
    if direction == "HIGHER_BETTER" and strong <= weak:
        raise RatioSpecError(f"{name}.anchor: HIGHER_BETTER icin strong > weak olmali")
    if direction == "LOWER_BETTER" and strong >= weak:
        raise RatioSpecError(f"{name}.anchor: LOWER_BETTER icin strong < weak olmali")
    if direction == "BAND":
        raise RatioSpecError(f"{name}: BAND rasyosu anchor tasiyamaz, band kullanir")
    return Anchor(weak=weak, strong=strong)


def load_ratio_set(ratios_path: str | Path, fields_path: str | Path) -> RatioSet:
    data = _obj(json.loads(Path(ratios_path).read_text(encoding="utf-8")), "ratio set")
    meta = _obj(data.get("meta"), "meta")
    families = _obj(meta.get("families"), "meta.families")
    groups = frozenset(_str_tuple(meta.get("sector_groups"), "meta.sector_groups"))
    if not groups:
        raise RatioSpecError("meta.sector_groups bos olamaz")

    registry = load_field_registry(fields_path)
    raw_ratios = _obj(data.get("ratios"), "ratios")
    if not raw_ratios:
        raise RatioSpecError("ratios bos olamaz")

    specs: dict[str, RatioSpec] = {}
    order: list[str] = []
    defined_so_far: set[str] = set()

    for name, raw in raw_ratios.items():
        raw = _obj(raw, f"ratios.{name}")
        role = raw.get("role", ROLE_SCORED)
        if role not in (ROLE_SCORED, ROLE_INTERMEDIATE):
            raise RatioSpecError(f"{name}: gecersiz role {role!r}")

        family = _text(raw.get("family"), f"{name}.family")
        if family not in families:
            raise RatioSpecError(f"{name}: meta.families icinde olmayan aile {family!r}")
        pillar = str(families[family])

        formula = _text(raw.get("formula"), f"{name}.formula")
        requires = _str_tuple(raw.get("requires"), f"{name}.requires")
        domain = _str_tuple(raw.get("domain"), f"{name}.domain")

        unknown_fields = [f for f in requires if f not in registry]
        if unknown_fields:
            raise RatioSpecError(
                f"{name}: alan kaydinda olmayan alan(lar): {sorted(unknown_fields)}"
            )

        # Every identifier a formula reads must be either a registry field or a
        # ratio already defined above it.  This is what keeps intermediates in
        # dependency order instead of relying on dict iteration luck.
        for ident in sorted(_formula_names(formula, name)):
            if ident in registry or ident in defined_so_far:
                continue
            raise RatioSpecError(
                f"{name}: formul tanimsiz {ident!r} okuyor "
                f"(alan kaydinda yok ve bu satirdan once tanimlanmamis)"
            )

        direction = raw.get("direction")
        out_of_domain = raw.get("out_of_domain", "MISSING")
        band = raw.get("band")
        applies_to: frozenset[str] = frozenset()

        if role == ROLE_SCORED:
            direction = _text(direction, f"{name}.direction")
            if direction not in DIRECTIONS:
                raise RatioSpecError(f"{name}: gecersiz direction {direction!r}")
            if out_of_domain not in OUT_OF_DOMAIN:
                raise RatioSpecError(f"{name}: gecersiz out_of_domain {out_of_domain!r}")
            applies_to = frozenset(_str_tuple(raw.get("applies_to"), f"{name}.applies_to"))
            if not applies_to:
                raise RatioSpecError(f"{name}: applies_to bos olamaz")
            unknown_groups = applies_to - groups
            if unknown_groups:
                raise RatioSpecError(f"{name}: bilinmeyen grup(lar) {sorted(unknown_groups)}")
            if direction == "BAND":
                bobj = _obj(band, f"{name}.band")
                low = _number(bobj.get("low"), f"{name}.band.low")
                high = _number(bobj.get("high"), f"{name}.band.high")
                if low >= high:
                    raise RatioSpecError(f"{name}.band: low < high olmali")
                band = {"low": low, "high": high}
            elif band is not None:
                raise RatioSpecError(f"{name}: band yalniz BAND rasyosunda olabilir")
        else:
            direction = None
            band = None

        anchor = _parse_anchor(raw.get("anchor"), name, direction)

        transform = raw.get("transform")
        if transform not in TRANSFORMS:
            raise RatioSpecError(f"{name}: gecersiz transform {transform!r}")
        clip = raw.get("clip")
        if transform == "clip":
            cobj = _obj(clip, f"{name}.clip")
            clip = {
                "low": _number(cobj.get("low"), f"{name}.clip.low"),
                "high": _number(cobj.get("high"), f"{name}.clip.high"),
            }
            if clip["low"] >= clip["high"]:
                raise RatioSpecError(f"{name}.clip: low < high olmali")
        elif clip is not None:
            raise RatioSpecError(f"{name}: clip yalniz transform=clip ile olabilir")

        winsor = _number(raw.get("winsor", 0.02), f"{name}.winsor")
        if not 0.0 <= winsor < 0.5:
            raise RatioSpecError(f"{name}.winsor [0, 0.5) araliginda olmali")

        specs[name] = RatioSpec(
            name=name, role=role, pillar=pillar, family=family, formula=formula,
            requires=requires, domain=domain, direction=direction,
            out_of_domain=out_of_domain, anchor=anchor, band=band,
            applies_to=applies_to, winsor=winsor, transform=transform, clip=clip,
        )
        order.append(name)
        defined_so_far.add(name)

    all_pillars = {str(p) for p in families.values()}

    raw_composites = _obj(meta.get("composites"), "meta.composites")
    if not raw_composites:
        raise RatioSpecError("meta.composites bos olamaz")
    composites: dict[str, tuple[str, ...]] = {}
    seen_pillars: set[str] = set()
    for cname, pillars in raw_composites.items():
        plist = _str_tuple(pillars, f"meta.composites.{cname}")
        if not plist:
            raise RatioSpecError(f"meta.composites.{cname} bos olamaz")
        unknown = set(plist) - all_pillars
        if unknown:
            raise RatioSpecError(f"meta.composites.{cname}: bilinmeyen pillar {sorted(unknown)}")
        overlap = seen_pillars & set(plist)
        if overlap:
            raise RatioSpecError(
                f"meta.composites.{cname}: pillar birden fazla kompozitte {sorted(overlap)}"
            )
        seen_pillars |= set(plist)
        composites[str(cname)] = plist
    missing_pillars = all_pillars - seen_pillars
    if missing_pillars:
        raise RatioSpecError(f"hicbir kompozite girmeyen pillar(lar): {sorted(missing_pillars)}")

    shares_obj = _obj(meta.get("pillar_shares"), "meta.pillar_shares")
    default_shares = _obj(shares_obj.get("default"), "meta.pillar_shares.default")
    parsed_default = {
        str(k): _number(v, f"meta.pillar_shares.default.{k}") for k, v in default_shares.items()
    }
    unknown = set(parsed_default) - all_pillars
    if unknown:
        raise RatioSpecError(f"meta.pillar_shares.default: bilinmeyen pillar {sorted(unknown)}")
    absent = all_pillars - set(parsed_default)
    if absent:
        raise RatioSpecError(f"meta.pillar_shares.default eksik pillar: {sorted(absent)}")
    if any(v < 0 for v in parsed_default.values()):
        raise RatioSpecError("meta.pillar_shares.default negatif pay tasiyamaz")

    by_group_raw = shares_obj.get("by_group") or {}
    by_group: dict[str, dict[str, float]] = {}
    for gname, gshares in _obj(by_group_raw, "meta.pillar_shares.by_group").items():
        if gname not in groups:
            raise RatioSpecError(f"meta.pillar_shares.by_group: bilinmeyen grup {gname!r}")
        parsed = {
            str(k): _number(v, f"meta.pillar_shares.by_group.{gname}.{k}")
            for k, v in _obj(gshares, f"meta.pillar_shares.by_group.{gname}").items()
        }
        if set(parsed) != all_pillars:
            raise RatioSpecError(
                f"meta.pillar_shares.by_group.{gname}: pillar kumesi default ile ayni olmali"
            )
        if any(v < 0 for v in parsed.values()):
            raise RatioSpecError(f"meta.pillar_shares.by_group.{gname} negatif pay tasiyamaz")
        by_group[str(gname)] = parsed

    ratio_set = RatioSet(
        version=_text(meta.get("ratio_set_version"), "meta.ratio_set_version"),
        field_set_version=_text(meta.get("field_set_version"), "meta.field_set_version"),
        families={str(k): str(v) for k, v in families.items()},
        sector_groups=groups,
        specs=specs,
        order=tuple(order),
        _composites=composites,
        _pillar_shares_default=parsed_default,
        _pillar_shares_by_group=by_group,
    )

    # A sector group with no applicable ratio would score every one of its
    # companies as YETERSIZ_KAPSAM forever, silently.
    for group in sorted(groups):
        if not ratio_set.applicable(group):
            raise RatioSpecError(f"{group}: hicbir rasyo uygulanabilir degil")
        shares = ratio_set.pillar_shares(group)
        live = {
            s.pillar for s in ratio_set.applicable(group) if shares.get(s.pillar, 0.0) > 0
        }
        for cname, pillars in composites.items():
            if not (live & set(pillars)):
                raise RatioSpecError(
                    f"{group}: {cname!r} kompoziti icin payi sifirdan buyuk hicbir "
                    f"pillar uygulanabilir degil"
                )

    return ratio_set


def coverage_report(ratio_set: RatioSet, registry: Mapping[str, dict]) -> dict[str, dict]:
    """Per sector group: how many ratios apply, and what blocks the rest.

    ``blocked_by_tier`` counts applicable ratios that cannot be computed until a
    field of that tier is actually populated.  This is the ingestion backlog
    expressed in the currency that matters: ratios unlocked per field landed.
    """
    out: dict[str, dict] = {}
    for group in sorted(ratio_set.sector_groups):
        applicable = ratio_set.applicable(group)
        blocked: dict[str, set[str]] = {}
        for spec in applicable:
            for fld in spec.requires:
                tier = registry[fld]["tier"]
                if tier == "CURRENT":
                    continue
                blocked.setdefault(tier, set()).add(spec.name)
        out[group] = {
            "applicable": len(applicable),
            "families": len(ratio_set.families_of(group)),
            "computable_today": len(
                [s for s in applicable
                 if all(registry[f]["tier"] == "CURRENT" for f in s.requires)]
            ),
            "blocked_by_tier": {k: len(v) for k, v in sorted(blocked.items())},
        }
    return out
