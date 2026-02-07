#!/usr/bin/env python3
"""obliterator.py — One CLI to rule them all.

Sniffable Python: the COMMANDS table below IS the interface.
Read it and you know everything. Single source of truth.

PersonData indices verified against original Sims 1 documentation
(PersonData.h, Jamie Doornbos, 12/17/99). NOT FreeSO/TSO VM indices.
"""

# ================================================================
# COMMAND TABLE — The single source of truth.
# Read this table and you know every command, every argument,
# every output format. The implementation below is driven by it.
# ================================================================

COMMANDS = {
    "inspect": {
        "help": "List all families and characters in a neighborhood",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
        ],
        "examples": [
            "obliterator inspect Neighborhood.iff",
            "obliterator inspect Neighborhood.iff -f json",
        ],
    },
    "families": {
        "help": "List families with budgets and house assignments",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
        ],
        "examples": [
            "obliterator families Neighborhood.iff",
            "obliterator families Neighborhood.iff -f csv",
        ],
    },
    "character": {
        "help": "Full character sheet: traits, skills, demographics, relationships",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name (partial match OK)"},
        ],
        "examples": [
            "obliterator character Neighborhood.iff 'Bella Goth'",
            "obliterator character Neighborhood.iff Mortimer -f yaml",
            "obliterator character Neighborhood.iff Mortimer -f json",
        ],
    },
    "traits": {
        "help": "Show personality traits with visual bars",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
        "examples": [
            "obliterator traits Neighborhood.iff 'Bob Newbie'",
        ],
    },
    "skills": {
        "help": "Show skill levels with visual bars",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
        "examples": [
            "obliterator skills Neighborhood.iff Mortimer",
        ],
    },
    "set-trait": {
        "help": "Set a personality trait (0-10 scale)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
            {"name": "trait", "help": "neat|outgoing|active|playful|nice|generous"},
            {"name": "value", "help": "0-10", "type": int},
        ],
        "examples": [
            "obliterator set-trait Neighborhood.iff Bob outgoing 3",
        ],
    },
    "set-skill": {
        "help": "Set a skill level (0-10 scale)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
            {"name": "skill", "help": "cooking|mechanical|charisma|logic|body|creativity|cleaning"},
            {"name": "value", "help": "0-10", "type": int},
        ],
        "examples": [
            "obliterator set-skill Neighborhood.iff Mortimer logic 10",
        ],
    },
    "set-money": {
        "help": "Set a family's budget in Simoleons",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "family_id", "help": "Family ID number", "type": int},
            {"name": "amount", "help": "Amount in Simoleons", "type": int},
        ],
        "examples": [
            "obliterator set-money Neighborhood.iff 1 99999",
        ],
    },
    "dump-raw": {
        "help": "Dump raw PersonData array with field name annotations",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
        "examples": [
            "obliterator dump-raw Neighborhood.iff Mortimer",
            "obliterator dump-raw Neighborhood.iff Bella -f json",
        ],
    },
    "uplift": {
        "help": "Generate MOOLLM CHARACTER.yml sims: block from save data",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
        "opts": [
            {"flags": ["-o", "--output"], "help": "Write to file instead of stdout"},
        ],
        "examples": [
            "obliterator uplift Neighborhood.iff 'Bella Goth'",
            "obliterator uplift Neighborhood.iff Mortimer -o mortimer-goth/CHARACTER.yml",
        ],
    },
}

# Output formats available for all commands
OUTPUT_FORMATS = ["table", "json", "yaml", "csv", "raw"]

# Global options available on every command
GLOBAL_OPTS = [
    {"flags": ["-f", "--format"], "choices": OUTPUT_FORMATS, "default": "table",
     "help": "Output format: table (default), json, yaml, csv, raw"},
]

# ================================================================
# REFERENCE DATA — Trait poles, career tracks, zodiac signs.
# Also data: also sniffable. Also single source of truth.
# ================================================================

TRAIT_INFO = {
    "nice":     {"index": 2,  "low": "Grouchy",  "high": "Nice"},
    "active":   {"index": 3,  "low": "Lazy",     "high": "Active"},
    "generous": {"index": 4,  "low": "Selfish",  "high": "Generous"},
    "playful":  {"index": 5,  "low": "Serious",  "high": "Playful"},
    "outgoing": {"index": 6,  "low": "Shy",      "high": "Outgoing"},
    "neat":     {"index": 7,  "low": "Sloppy",   "high": "Neat"},
}

SKILL_INFO = {
    "cleaning":   {"index": 9},
    "cooking":    {"index": 10},
    "charisma":   {"index": 11},
    "mechanical": {"index": 12},
    "gardening":  {"index": 13, "hidden": True},
    "music":      {"index": 14, "hidden": True},
    "creativity": {"index": 15},
    "literacy":   {"index": 16, "hidden": True},
    "body":       {"index": 17},
    "logic":      {"index": 18},
}

# UI-visible skills in display order
VISIBLE_SKILLS = ["cooking", "mechanical", "charisma", "logic", "body", "creativity", "cleaning"]

CAREER_TRACKS = {
    0: "Unemployed", 1: "Cooking/Culinary", 2: "Entertainment",
    3: "Law Enforcement", 4: "Medicine", 5: "Military",
    6: "Politics", 7: "Pro Athlete", 8: "Science", 9: "Xtreme",
}

ZODIAC_SIGNS = {
    0: "Uncomputed", 1: "Aries", 2: "Taurus", 3: "Gemini",
    4: "Cancer", 5: "Leo", 6: "Virgo", 7: "Libra",
    8: "Scorpio", 9: "Sagittarius", 10: "Capricorn",
    11: "Aquarius", 12: "Pisces",
}

# PersonData demographic field indices
DEMO_FIELDS = {
    "age": 58, "skin_color": 60, "family_number": 61,
    "gender": 65, "ghost": 68, "zodiac": 70,
}

# PersonData career field indices
CAREER_FIELDS = {
    "job_type": 56, "job_status": 57, "job_performance": 63,
}


# ================================================================
# IMPLEMENTATION — Driven by the tables above.
# Everything below here is plumbing. The interface is above.
# ================================================================

import sys
import json
import csv
import io
import argparse
from pathlib import Path
from typing import Optional, Any

# Add SimObliterator src to path
_src_dir = Path(__file__).parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from Tools.save_editor.save_manager import SaveManager, PersonData


def _load(path: str) -> SaveManager:
    """Load neighborhood. Exit on failure."""
    mgr = SaveManager(path)
    if not mgr.load():
        print(f"ERROR: Failed to load {path}", file=sys.stderr)
        sys.exit(1)
    return mgr


def _find(mgr: SaveManager, name: str):
    """Find neighbor by name. Case-insensitive partial match. Exit on ambiguity."""
    name_lower = name.lower()
    hits = [(nid, n) for nid, n in mgr.neighbors.items()
            if name_lower in n.name.lower()]
    if not hits:
        avail = sorted(n.name for n in mgr.neighbors.values() if n.name)
        print(f"ERROR: No match for '{name}'. Available: {', '.join(avail)}", file=sys.stderr)
        sys.exit(1)
    if len(hits) > 1:
        exact = [(nid, n) for nid, n in hits if n.name.lower() == name_lower]
        if len(exact) == 1:
            return exact[0]
        print(f"ERROR: Ambiguous '{name}':", file=sys.stderr)
        for nid, n in hits:
            print(f"  [{nid}] {n.name}", file=sys.stderr)
        sys.exit(1)
    return hits[0]


def _pd(person_data, index):
    """Safe PersonData read."""
    if person_data and 0 <= index < len(person_data):
        return person_data[index]
    return None


def _bar(val, width=10):
    """Visual bar: val out of width."""
    v = max(0, min(val, width))
    return "\u2588" * v + "\u2591" * (width - v)


def _read_traits(pd_list):
    """Extract traits as {name: {raw, display, low, high}}."""
    out = {}
    for name, info in TRAIT_INFO.items():
        raw = _pd(pd_list, info["index"])
        if raw is not None:
            out[name] = {"raw": raw, "display": round(raw / 100),
                         "low": info["low"], "high": info["high"]}
    return out


def _read_skills(pd_list, include_hidden=False):
    """Extract skills as {name: {raw, display}}."""
    out = {}
    for name, info in SKILL_INFO.items():
        if not include_hidden and info.get("hidden"):
            continue
        raw = _pd(pd_list, info["index"])
        if raw is not None:
            out[name] = {"raw": raw, "display": round(raw / 100)}
    return out


def _read_demographics(pd_list):
    """Extract demographics as a flat dict."""
    age = _pd(pd_list, DEMO_FIELDS["age"])
    gender = _pd(pd_list, DEMO_FIELDS["gender"])
    skin = _pd(pd_list, DEMO_FIELDS["skin_color"])
    zodiac = _pd(pd_list, DEMO_FIELDS["zodiac"])
    job_type = _pd(pd_list, CAREER_FIELDS["job_type"])
    job_perf = _pd(pd_list, CAREER_FIELDS["job_performance"])
    return {
        "age": {0: "child", 1: "adult"}.get(age, str(age)),
        "gender": {0: "male", 1: "female"}.get(gender, str(gender)),
        "skin_color": {0: "light", 1: "medium", 2: "dark"}.get(skin, str(skin)),
        "zodiac": ZODIAC_SIGNS.get(zodiac, f"unknown({zodiac})"),
        "career": CAREER_TRACKS.get(job_type, f"unknown({job_type})"),
        "job_performance": job_perf,
    }


# ================================================================
# OUTPUT FORMATTERS — One per format. Commands return data dicts,
# formatters render them. Clean separation.
# ================================================================

def _emit(data: Any, fmt: str, headers: list = None):
    """Emit data in the requested format."""
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "yaml":
        _emit_yaml(data)
    elif fmt == "csv":
        _emit_csv(data, headers)
    elif fmt == "raw":
        _emit_raw(data)
    elif fmt == "table":
        if isinstance(data, str):
            print(data)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            _emit_table(data, headers)
        else:
            print(data)


def _emit_yaml(data, indent=0):
    """Simple YAML emitter. No dependency on pyyaml."""
    prefix = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                print(f"{prefix}{k}:")
                _emit_yaml(v, indent + 1)
            else:
                comment = ""
                print(f"{prefix}{k}: {v}{comment}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    marker = "- " if first else "  "
                    print(f"{prefix}{marker}{k}: {v}")
                    first = False
            else:
                print(f"{prefix}- {item}")
    else:
        print(f"{prefix}{data}")


def _emit_csv(data, headers=None):
    """Emit as CSV."""
    buf = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = headers or list(data[0].keys())
        writer = csv.DictWriter(buf, fieldnames=keys)
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, "") for k in keys})
    elif isinstance(data, dict):
        writer = csv.writer(buf)
        for k, v in data.items():
            writer.writerow([k, v])
    print(buf.getvalue().rstrip())


def _emit_raw(data):
    """Emit as raw key=value pairs. Grep-friendly."""
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print(f"{k}.{k2}={v2}")
            else:
                print(f"{k}={v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                print("\t".join(str(v) for v in item.values()))
            else:
                print(item)
    else:
        print(data)


def _emit_table(rows, headers=None):
    """Emit as aligned text table."""
    if not rows:
        return
    keys = headers or list(rows[0].keys())
    widths = {k: len(str(k)) for k in keys}
    for row in rows:
        for k in keys:
            widths[k] = max(widths[k], len(str(row.get(k, ""))))
    header = "  ".join(str(k).ljust(widths[k]) for k in keys)
    print(header)
    print("  ".join("-" * widths[k] for k in keys))
    for row in rows:
        print("  ".join(str(row.get(k, "")).ljust(widths[k]) for k in keys))


# ================================================================
# COMMAND IMPLEMENTATIONS — Each returns data (not strings).
# Formatting is handled by _emit().
# ================================================================

def cmd_inspect(args):
    mgr = _load(args.file)
    families = []
    for fid, fam in sorted(mgr.families.items()):
        families.append({
            "id": fid, "house": fam.house_number,
            "budget": fam.budget, "members": fam.num_members,
            "status": "townie" if fam.is_townie else "resident",
        })
    characters = []
    for nid, neigh in sorted(mgr.neighbors.items()):
        traits = _read_traits(neigh.person_data) if neigh.person_data else {}
        trait_str = " ".join(
            f"{k[0].upper()}{v['display']}"
            for k, v in traits.items() if k in ["neat", "outgoing", "active", "playful", "nice"]
        )
        characters.append({
            "id": nid, "name": neigh.name, "traits": trait_str,
        })

    if args.format == "table":
        print(f"Neighborhood: {args.file}")
        print(f"Families: {len(families)}  |  Characters: {len(characters)}\n")
        if families:
            print("FAMILIES")
            _emit_table(families, ["id", "house", "budget", "members", "status"])
        if characters:
            print("\nCHARACTERS")
            _emit_table(characters, ["id", "name", "traits"])
    else:
        _emit({"families": families, "characters": characters}, args.format)


def cmd_families(args):
    mgr = _load(args.file)
    rows = []
    for fid, fam in sorted(mgr.families.items()):
        rows.append({
            "id": fid, "house": fam.house_number,
            "budget": fam.budget, "members": fam.num_members,
            "status": "townie" if fam.is_townie else "resident",
        })
    _emit(rows, args.format, ["id", "house", "budget", "members", "status"])


def cmd_character(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    traits = _read_traits(neigh.person_data)
    skills = _read_skills(neigh.person_data)
    demo = _read_demographics(neigh.person_data)

    data = {
        "name": neigh.name, "neighbor_id": nid,
        "demographics": demo,
        "traits": {k: v["display"] for k, v in traits.items()},
        "traits_raw": {k: v["raw"] for k, v in traits.items()},
        "skills": {k: v["display"] for k, v in skills.items()},
        "skills_raw": {k: v["raw"] for k, v in skills.items()},
        "relationships": {str(k): v for k, v in neigh.relationships.items()},
    }

    if args.format == "table":
        print(f"{'=' * 50}")
        print(f"  {neigh.name}  (neighbor #{nid})")
        print(f"{'=' * 50}")
        print(f"\n  {demo['age']}  |  {demo['gender']}  |  {demo['zodiac']}  |  {demo['career']}")
        print(f"\n  PERSONALITY")
        print(f"  {'─' * 44}")
        for t in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
            if t in traits:
                v = traits[t]
                print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}")
        print(f"\n  SKILLS")
        print(f"  {'─' * 44}")
        for s in VISIBLE_SKILLS:
            if s in skills:
                v = skills[s]
                print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}")
        if neigh.relationships:
            print(f"\n  RELATIONSHIPS")
            print(f"  {'─' * 44}")
            for rid, rv in list(neigh.relationships.items())[:10]:
                daily = rv[0] if len(rv) > 0 else "?"
                life = rv[1] if len(rv) > 1 else "?"
                print(f"  Neighbor {rid}: daily={daily}, lifetime={life}")
    else:
        _emit(data, args.format)


def cmd_traits(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)
    traits = _read_traits(neigh.person_data)
    if args.format == "table":
        print(f"{neigh.name} — Personality")
        for t in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
            if t in traits:
                v = traits[t]
                print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}  (raw {v['raw']})")
    else:
        _emit({"name": neigh.name, "traits": {k: v["display"] for k, v in traits.items()}}, args.format)


def cmd_skills(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)
    skills = _read_skills(neigh.person_data)
    if args.format == "table":
        print(f"{neigh.name} — Skills")
        for s in VISIBLE_SKILLS:
            if s in skills:
                v = skills[s]
                print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}  (raw {v['raw']})")
    else:
        _emit({"name": neigh.name, "skills": {k: v["display"] for k, v in skills.items()}}, args.format)


def cmd_set_trait(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_personality(nid, args.trait, raw):
        mgr.save()
        print(f"Saved. {neigh.name} {args.trait} = {args.value}")
    else:
        sys.exit(1)


def cmd_set_skill(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_skill(nid, args.skill, raw):
        mgr.save()
        print(f"Saved. {neigh.name} {args.skill} = {args.value}")
    else:
        sys.exit(1)


def cmd_set_money(args):
    mgr = _load(args.file)
    if mgr.set_family_money(args.family_id, args.amount):
        mgr.save()
        print(f"Saved. Family {args.family_id} budget = {args.amount}")
    else:
        sys.exit(1)


def cmd_dump_raw(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    # Build reverse index of field names from our reference tables
    known = {}
    for name, info in TRAIT_INFO.items():
        known[info["index"]] = f"personality.{name}"
    for name, info in SKILL_INFO.items():
        known[info["index"]] = f"skill.{name}"
    for name, idx in DEMO_FIELDS.items():
        known[idx] = f"demo.{name}"
    for name, idx in CAREER_FIELDS.items():
        known[idx] = f"career.{name}"
    known[0] = "idle_state"
    known[1] = "npc_fee_amount"
    known[8] = "current_outfit"

    rows = []
    for i, val in enumerate(neigh.person_data):
        rows.append({
            "index": i, "value": val,
            "field": known.get(i, ""),
            "nonzero": "*" if val != 0 else "",
        })

    if args.format == "table":
        print(f"PersonData for {neigh.name} ({len(neigh.person_data)} fields)")
        print(f"{'─' * 55}")
        for r in rows:
            print(f"  [{r['index']:>3}] {r['value']:>6}{r['nonzero']:>2}  {r['field']}")
    else:
        _emit(rows, args.format, ["index", "value", "field"])


def cmd_uplift(args):
    mgr = _load(args.file)
    nid, neigh = _find(mgr, args.name)
    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    traits = _read_traits(neigh.person_data)
    skills = _read_skills(neigh.person_data)
    demo = _read_demographics(neigh.person_data)

    # Always emit YAML for uplift (it's a YAML generator)
    lines = [f"# {neigh.name} — Uplifted from Sims 1 save data"]
    lines.append(f"# Neighbor ID: {nid}  |  Source: {args.file}")
    lines.append(f"\nsims:")
    lines.append(f"  traits:")
    for t in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
        if t in traits:
            v = traits[t]
            lines.append(f"    {t}: {v['display']:<3}  # {v['low']} {v['display']}/10 {v['high']}")
    lines.append(f"  skills:")
    for s in VISIBLE_SKILLS:
        if s in skills:
            lines.append(f"    {s}: {skills[s]['display']}")
    lines.append(f"  career:")
    lines.append(f"    track: {demo['career'].lower().replace('/', '_')}")
    lines.append(f"    performance: {demo['job_performance']}")
    lines.append(f"  identity:")
    lines.append(f"    age: {demo['age']}")
    lines.append(f"    gender: {demo['gender']}")
    lines.append(f"    zodiac: {demo['zodiac'].lower()}")
    lines.append(f"    skin_color: {demo['skin_color']}")

    output = "\n".join(lines) + "\n"
    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(output)
        print(f"Wrote {p}")
    else:
        print(output, end="")


# ================================================================
# PARSER BUILDER — Driven by COMMANDS table. Not hand-wired.
# ================================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="obliterator",
        description="One CLI to rule The Sims 1 save files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Output formats: table (default), json, yaml, csv, raw\n"
               "PersonData indices verified against original Sims 1 documentation.",
    )
    # Global options
    for opt in GLOBAL_OPTS:
        parser.add_argument(*opt["flags"], choices=opt.get("choices"),
                            default=opt.get("default"), help=opt["help"])

    sub = parser.add_subparsers(dest="command")

    # Wire each command from the COMMANDS table
    dispatch = {}
    for cmd_name, spec in COMMANDS.items():
        p = sub.add_parser(cmd_name, help=spec["help"])
        for arg in spec.get("args", []):
            kwargs = {"help": arg["help"]}
            if "type" in arg:
                kwargs["type"] = arg["type"]
            p.add_argument(arg["name"], **kwargs)
        for opt in spec.get("opts", []):
            kwargs = {"help": opt["help"]}
            p.add_argument(*opt["flags"], **kwargs)
        # Map command name to function
        fn_name = "cmd_" + cmd_name.replace("-", "_")
        dispatch[cmd_name] = globals().get(fn_name)

    return parser, dispatch


def main():
    parser, dispatch = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
