#!/usr/bin/env python3
"""obliterator.py — One CLI to rule them all.

Hierarchical command tree, like gcloud. Every level has --help.

    obliterator character uplift <neighborhood.iff> <name>
    obliterator character come-home <neighborhood.iff> <uplift.yml>
    obliterator family list <neighborhood.iff>
    obliterator iff info <file.iff>
    obliterator far list <file.far>
    obliterator tmog export <file.iff>

HOW THIS FILE IS ORGANIZED:

1. COMMANDS tree    — declares every group, command, and argument
2. Global options   — cross-cutting flags (--format, --sims-data, etc.)
3. Reference data   — PersonData indices, trait names, career tracks
4. Helpers          — load files, find characters, read traits/skills
5. Output formatters — table/json/yaml/csv/raw
6. Command functions — one per leaf command (cmd_character_uplift, etc.)
7. Parser builder   — reads COMMANDS tree, builds argparse hierarchy

PersonData indices verified against original Sims 1 documentation.
"""

# COMMANDS tree. Each top-level key is a command group.
# Each group has a help string and a dict of subcommands.
# The parser builder walks this tree and creates argparse subparsers.
# `obliterator character --help` shows all character subcommands.

COMMANDS = {
    "character": {
        "help": "Sim character operations: inspect, edit, uplift, come home",
        "commands": {
            "inspect": {
                "help": "List all characters in a neighborhood",
                "args": [{"name": "file", "help": "Path to Neighborhood.iff"}],
            },
            "show": {
                "help": "Full character sheet: traits, skills, demographics, relationships",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name (partial match OK)"},
                ],
            },
            "traits": {
                "help": "Show personality traits with visual bars",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
                ],
            },
            "skills": {
                "help": "Show skill levels with visual bars",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
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
            },
            "set-skill": {
                "help": "Set a skill level (0-10 scale)",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
                    {"name": "skill", "help": "cooking|mechanical|charisma|logic|body|creativity|cleaning"},
                    {"name": "value", "help": "0-10", "type": int},
                ],
            },
            "dump-raw": {
                "help": "Dump raw PersonData array with field name annotations",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
                ],
            },
            "uplift": {
                "help": "Extract character data to SIMS-UPLIFT.yml for LLM processing",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
                ],
                "opts": [{"flags": ["-o", "--output"], "help": "Write to file (default: stdout)"}],
            },
            "come-home": {
                "help": "Write SIMS-UPLIFT.yml data back into save file (return to The Sims)",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "uplift_yml", "help": "Path to SIMS-UPLIFT.yml"},
                ],
            },
            "sync": {
                "help": "Compare save file against CHARACTER.yml, emit merge events for LLM",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "name", "help": "Character name"},
                    {"name": "character_yml", "help": "Path to existing CHARACTER.yml"},
                ],
            },
        },
    },

    "family": {
        "help": "Family and household operations",
        "commands": {
            "list": {
                "help": "List families with budgets, houses, and member counts",
                "args": [{"name": "file", "help": "Path to Neighborhood.iff"}],
            },
            "set-money": {
                "help": "Set a family's budget in Simoleons",
                "args": [
                    {"name": "file", "help": "Path to Neighborhood.iff"},
                    {"name": "family_id", "help": "Family ID number", "type": int},
                    {"name": "amount", "help": "Amount in Simoleons", "type": int},
                ],
            },
        },
    },

    "iff": {
        "help": "IFF file inspection (any .iff file)",
        "commands": {
            "info": {
                "help": "Show chunk count and type distribution",
                "args": [{"name": "file", "help": "Path to .iff file"}],
            },
            "chunks": {
                "help": "List all chunks with type, ID, label, size",
                "args": [{"name": "file", "help": "Path to .iff file"}],
                "opts": [{"flags": ["--type"], "help": "Filter by chunk type (BHAV, STR#, OBJD, etc.)"}],
            },
            "strings": {
                "help": "Show string tables (STR#/CTSS) with language filtering",
                "args": [{"name": "file", "help": "Path to .iff file"}],
                "opts": [
                    {"flags": ["--lang"], "help": "Language index (0=US English)", "type": int},
                    {"flags": ["--chunk-id"], "help": "Specific chunk ID", "type": int},
                ],
            },
            "objects": {
                "help": "List object definitions (OBJD) with GUID, name, price",
                "args": [{"name": "file", "help": "Path to .iff file"}],
            },
            "bhav": {
                "help": "List or disassemble BHAV behavior scripts",
                "args": [{"name": "file", "help": "Path to .iff file"}],
                "opts": [{"flags": ["--id"], "help": "Disassemble specific BHAV by chunk ID", "type": int}],
            },
        },
    },

    "far": {
        "help": "FAR archive operations (.far files)",
        "commands": {
            "list": {
                "help": "List contents of a .far archive",
                "args": [{"name": "file", "help": "Path to .far file"}],
            },
            "extract": {
                "help": "Extract files from a .far archive",
                "args": [
                    {"name": "file", "help": "Path to .far file"},
                    {"name": "output", "help": "Output directory"},
                ],
                "opts": [{"flags": ["--name"], "help": "Extract only this filename"}],
            },
        },
    },

    "tmog": {
        "help": "Transmogrifier: IFF object <-> YAML round-trip",
        "commands": {
            "export": {
                "help": "Export .iff object to IFF-OBJECT.yml (all chunks, symbolic names)",
                "args": [{"name": "file", "help": "Path to .iff object file"}],
                "opts": [{"flags": ["-o", "--output"], "help": "Output .yml path"}],
            },
            "import": {
                "help": "Import IFF-OBJECT.yml back to .iff binary",
                "args": [{"name": "yml", "help": "Path to IFF-OBJECT.yml"}],
                "opts": [{"flags": ["-o", "--output"], "help": "Output .iff path"}],
            },
        },
    },
}

# Cross-cutting global options available on every command
GLOBAL_OPTS = [
    {"flags": ["-f", "--format"], "choices": ["table", "json", "yaml", "csv", "raw"],
     "default": "table", "help": "Output format"},
    {"flags": ["-d", "--sims-data"], "default": None,
     "help": "Sims data root directory (auto-detected if not set)"},
]

# Reference data
TRAIT_INFO = {
    "nice":     {"index": 2,  "low": "Grouchy",  "high": "Nice"},
    "active":   {"index": 3,  "low": "Lazy",     "high": "Active"},
    "generous": {"index": 4,  "low": "Selfish",  "high": "Generous"},
    "playful":  {"index": 5,  "low": "Serious",  "high": "Playful"},
    "outgoing": {"index": 6,  "low": "Shy",      "high": "Outgoing"},
    "neat":     {"index": 7,  "low": "Sloppy",   "high": "Neat"},
}
SKILL_INFO = {
    "cleaning":   {"index": 9},  "cooking":    {"index": 10},
    "charisma":   {"index": 11}, "mechanical": {"index": 12},
    "gardening":  {"index": 13, "hidden": True}, "music": {"index": 14, "hidden": True},
    "creativity": {"index": 15}, "literacy":   {"index": 16, "hidden": True},
    "body":       {"index": 17}, "logic":      {"index": 18},
}
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
DEMO_FIELDS = {"age": 58, "skin_color": 60, "family_number": 61,
               "gender": 65, "ghost": 68, "zodiac": 70}
CAREER_FIELDS = {"job_type": 56, "job_status": 57, "job_performance": 63}


# Implementation

import sys
import json
import csv
import io
import argparse
from pathlib import Path
from typing import Any, Optional

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

# Lazy imports
def _save_manager():
    """Import save file editing module."""
    from Tools.save_editor.save_manager import SaveManager, PersonData
    return SaveManager, PersonData

def _iff_file():
    """Import IFF file reader."""
    from formats.iff.iff_file import IffFile
    return IffFile

def _far1():
    """Import FAR v1 archive reader."""
    from formats.far.far1 import FAR1Archive
    return FAR1Archive

# Helpers
def _load_save(path):
    """Load a Neighborhood.iff save file. Exits on failure."""
    SaveManager, _ = _save_manager()
    mgr = SaveManager(path)
    if not mgr.load():
        print(f"ERROR: Failed to load {path}", file=sys.stderr)
        sys.exit(1)
    return mgr

def _find(mgr, name):
    """Find a Sim by name (case-insensitive partial match). Exits on ambiguity."""
    lo = name.lower()
    hits = [(nid, n) for nid, n in mgr.neighbors.items() if lo in n.name.lower()]
    if not hits:
        avail = sorted(n.name for n in mgr.neighbors.values() if n.name)
        print(f"ERROR: No match for '{name}'. Available: {', '.join(avail)}", file=sys.stderr)
        sys.exit(1)
    if len(hits) > 1:
        exact = [(nid, n) for nid, n in hits if n.name.lower() == lo]
        if len(exact) == 1:
            return exact[0]
        print(f"ERROR: Ambiguous '{name}':", file=sys.stderr)
        for nid, n in hits:
            print(f"  [{nid}] {n.name}", file=sys.stderr)
        sys.exit(1)
    return hits[0]

def _pd(data, idx):
    """Read one value from PersonData, safely."""
    if data and 0 <= idx < len(data):
        return data[idx]
    return None

def _bar(v, w=10):
    """Visual bar [████████░░] for value 0-10."""
    v = max(0, min(v, w))
    return "\u2588" * v + "\u2591" * (w - v)

def _read_traits(pd):
    """Extract personality traits from PersonData."""
    return {n: {"raw": r, "display": round(r/100), "low": i["low"], "high": i["high"]}
            for n, i in TRAIT_INFO.items() if (r := _pd(pd, i["index"])) is not None}

def _read_skills(pd, hidden=False):
    """Extract skills from PersonData."""
    return {n: {"raw": r, "display": round(r/100)}
            for n, i in SKILL_INFO.items()
            if (hidden or not i.get("hidden")) and (r := _pd(pd, i["index"])) is not None}

def _read_demo(pd):
    """Extract demographics from PersonData."""
    age = _pd(pd, DEMO_FIELDS["age"])
    gen = _pd(pd, DEMO_FIELDS["gender"])
    skin = _pd(pd, DEMO_FIELDS["skin_color"])
    zod = _pd(pd, DEMO_FIELDS["zodiac"])
    jt = _pd(pd, CAREER_FIELDS["job_type"])
    jp = _pd(pd, CAREER_FIELDS["job_performance"])
    return {
        "age": {0:"child",1:"adult"}.get(age, str(age)),
        "gender": {0:"male",1:"female"}.get(gen, str(gen)),
        "skin_color": {0:"light",1:"medium",2:"dark"}.get(skin, str(skin)),
        "zodiac": ZODIAC_SIGNS.get(zod, f"unknown({zod})"),
        "career": CAREER_TRACKS.get(jt, f"unknown({jt})"),
        "job_performance": jp,
    }

# Output formatters
def _emit(data, fmt, headers=None):
    """Dispatch to the right output formatter."""
    if fmt == "json": print(json.dumps(data, indent=2, default=str))
    elif fmt == "yaml": _emit_yaml(data)
    elif fmt == "csv": _emit_csv(data, headers)
    elif fmt == "raw": _emit_raw(data)
    elif fmt == "table":
        if isinstance(data, str): print(data)
        elif isinstance(data, list) and data and isinstance(data[0], dict): _emit_table(data, headers)
        else: print(data)

def _emit_yaml(d, indent=0):
    """Simple YAML emitter (no pyyaml dependency)."""
    p = "  " * indent
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)): print(f"{p}{k}:"); _emit_yaml(v, indent+1)
            else: print(f"{p}{k}: {v}")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    print(f"{p}{'- ' if first else '  '}{k}: {v}"); first = False
            else: print(f"{p}- {item}")
    else: print(f"{p}{d}")

def _emit_csv(data, headers=None):
    """CSV output."""
    buf = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = headers or list(data[0].keys())
        w = csv.DictWriter(buf, fieldnames=keys); w.writeheader()
        for row in data: w.writerow({k: row.get(k,"") for k in keys})
    elif isinstance(data, dict):
        w = csv.writer(buf)
        for k, v in data.items(): w.writerow([k, v])
    print(buf.getvalue().rstrip())

def _emit_raw(data):
    """Key=value output for grep."""
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                for k2, v2 in v.items(): print(f"{k}.{k2}={v2}")
            else: print(f"{k}={v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict): print("\t".join(str(v) for v in item.values()))
            else: print(item)
    else: print(data)

def _emit_table(rows, headers=None):
    """Aligned text table."""
    if not rows: return
    keys = headers or list(rows[0].keys())
    widths = {k: max(len(str(k)), max((len(str(r.get(k,""))) for r in rows), default=0)) for k in keys}
    print("  ".join(str(k).ljust(widths[k]) for k in keys))
    print("  ".join("-"*widths[k] for k in keys))
    for row in rows:
        print("  ".join(str(row.get(k,"")).ljust(widths[k]) for k in keys))


# Command functions
# Named: cmd_<group>_<subcommand> (dashes become underscores)

def cmd_character_inspect(args):
    """List all characters in a neighborhood with trait summaries."""
    mgr = _load_save(args.file)
    families = [{"id": fid, "house": f.house_number, "budget": f.budget,
                 "members": f.num_members, "status": "townie" if f.is_townie else "resident"}
                for fid, f in sorted(mgr.families.items())]
    characters = []
    for nid, n in sorted(mgr.neighbors.items()):
        tr = _read_traits(n.person_data) if n.person_data else {}
        ts = " ".join(f"{k[0].upper()}{v['display']}" for k,v in tr.items()
                      if k in ["neat","outgoing","active","playful","nice"])
        characters.append({"id": nid, "name": n.name, "traits": ts})
    if args.format == "table":
        print(f"Neighborhood: {args.file}")
        print(f"Families: {len(families)}  |  Characters: {len(characters)}\n")
        if families: print("FAMILIES"); _emit_table(families, ["id","house","budget","members","status"])
        if characters: print("\nCHARACTERS"); _emit_table(characters, ["id","name","traits"])
    else:
        _emit({"families": families, "characters": characters}, args.format)

def cmd_character_show(args):
    """Full character sheet for one Sim."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: {n.name} has no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data); sk = _read_skills(n.person_data); dm = _read_demo(n.person_data)
    data = {"name": n.name, "neighbor_id": nid, "demographics": dm,
            "traits": {k:v["display"] for k,v in tr.items()},
            "skills": {k:v["display"] for k,v in sk.items()},
            "relationships": {str(k):v for k,v in n.relationships.items()}}
    if args.format == "table":
        print(f"  {n.name}  (neighbor #{nid})")
        print(f"\n  {dm['age']}  |  {dm['gender']}  |  {dm['zodiac']}  |  {dm['career']}")
        print(f"\n  PERSONALITY")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr: v=tr[t]; print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}")
        print(f"\n  SKILLS")
        for s in VISIBLE_SKILLS:
            if s in sk: v=sk[s]; print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}")
        if n.relationships:
            print(f"\n  RELATIONSHIPS")
            for rid, rv in list(n.relationships.items())[:10]:
                d = rv[0] if len(rv)>0 else "?"; l = rv[1] if len(rv)>1 else "?"
                print(f"  Neighbor {rid}: daily={d}, lifetime={l}")
    else: _emit(data, args.format)

def cmd_character_traits(args):
    """Show personality traits with visual bars."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Personality")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr: v=tr[t]; print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}  (raw {v['raw']})")
    else: _emit({"name": n.name, "traits": {k:v["display"] for k,v in tr.items()}}, args.format)

def cmd_character_skills(args):
    """Show skill levels with visual bars."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    sk = _read_skills(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Skills")
        for s in VISIBLE_SKILLS:
            if s in sk: v=sk[s]; print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}  (raw {v['raw']})")
    else: _emit({"name": n.name, "skills": {k:v["display"] for k,v in sk.items()}}, args.format)

def cmd_character_set_trait(args):
    """Write a personality trait value to the save file (0-10)."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_personality(nid, args.trait, raw):
        mgr.save(); print(f"Saved. {n.name} {args.trait} = {args.value}")
    else: sys.exit(1)

def cmd_character_set_skill(args):
    """Write a skill level to the save file (0-10)."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_skill(nid, args.skill, raw):
        mgr.save(); print(f"Saved. {n.name} {args.skill} = {args.value}")
    else: sys.exit(1)

def cmd_character_dump_raw(args):
    """Dump raw PersonData array with field name annotations."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    known = {}
    for name, info in TRAIT_INFO.items(): known[info["index"]] = f"personality.{name}"
    for name, info in SKILL_INFO.items(): known[info["index"]] = f"skill.{name}"
    for name, idx in DEMO_FIELDS.items(): known[idx] = f"demo.{name}"
    for name, idx in CAREER_FIELDS.items(): known[idx] = f"career.{name}"
    known.update({0:"idle_state", 1:"npc_fee_amount", 8:"current_outfit"})
    rows = [{"index":i, "value":v, "field":known.get(i,""), "nz":"*" if v!=0 else ""}
            for i,v in enumerate(n.person_data)]
    if args.format == "table":
        print(f"PersonData for {n.name} ({len(n.person_data)} fields)")
        for r in rows: print(f"  [{r['index']:>3}] {r['value']:>6}{r['nz']:>2}  {r['field']}")
    else: _emit(rows, args.format, ["index","value","field"])

def cmd_character_uplift(args):
    """Extract Sim data from save file into SIMS-UPLIFT.yml format.
    The LLM reads this to generate CHARACTER.yml."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data); sk = _read_skills(n.person_data); dm = _read_demo(n.person_data)
    family_id = family_budget = house_number = 0; family_members = []
    for fid, fam in mgr.families.items():
        if n.guid in fam.member_guids:
            family_id = fid; family_budget = fam.budget; house_number = fam.house_number
            family_members = [g for g in fam.member_guids if g != n.guid]; break
    lines = [f"# SIMS-UPLIFT.yml — {n.name}", f"# Source: {args.file}", "",
             "schema_version: 1", "", "source:",
             f"  file: {args.file}", f"  neighbor_id: {nid}", f"  guid: {n.guid}",
             f"  family_id: {family_id}", f"  family_budget: {family_budget}",
             f"  house_number: {house_number}", f"  direction: uplift", "",
             "identity:", f"  name: {n.name}", f"  age: {dm['age']}",
             f"  gender: {dm['gender']}", f"  skin_color: {dm['skin_color']}",
             f"  zodiac: {dm['zodiac'].lower()}", "", "traits:"]
    for t in ["neat","outgoing","active","playful","nice","generous"]:
        if t in tr: lines.append(f"  {t}: {tr[t]['display']}")
    lines += ["", "skills:"]
    for s in VISIBLE_SKILLS:
        if s in sk: lines.append(f"  {s}: {sk[s]['display']}")
    lines += ["", "career:", f"  track: {dm['career'].lower().replace('/','_')}",
              f"  performance: {dm['job_performance']}", "", "relationships:"]
    if n.relationships:
        for rel_id, rv in n.relationships.items():
            d = rv[0] if len(rv)>0 else 0; l = rv[1] if len(rv)>1 else 0
            rn = next((o.name for oid, o in mgr.neighbors.items() if oid == rel_id), "")
            lines += [f"  {rel_id}:", f"    daily: {d}", f"    lifetime: {l}"]
            if rn: lines.append(f"    name: {rn}")
    else: lines.append("  {}")
    lines += ["", f"family_members: {family_members}", ""]
    out = "\n".join(lines)
    if args.output:
        p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out); print(f"Wrote {p}")
    else: print(out, end="")

def cmd_character_come_home(args):
    """Write SIMS-UPLIFT.yml back into save file. Welcome home."""
    mgr = _load_save(args.file)
    up = Path(args.uplift_yml)
    if not up.is_file(): print(f"ERROR: {up} not found", file=sys.stderr); sys.exit(1)
    data = _parse_uplift_yml(up.read_text())
    nid = data.get("neighbor_id")
    if nid is None or nid not in mgr.neighbors:
        name = data.get("name", "")
        if name: nid, _ = _find(mgr, name)
        else: print(f"ERROR: No neighbor_id or name in uplift file", file=sys.stderr); sys.exit(1)
    changes = 0
    for t in ["neat","outgoing","active","playful","nice","generous"]:
        v = data.get("traits",{}).get(t)
        if v is not None:
            if mgr.set_sim_personality(nid, t, max(0,min(int(v),10))*100): changes += 1
    for s in VISIBLE_SKILLS:
        v = data.get("skills",{}).get(s)
        if v is not None:
            if mgr.set_sim_skill(nid, s, max(0,min(int(v),10))*100): changes += 1
    career = data.get("career",{})
    tn = career.get("track","").lower()
    tid = next((k for k,v in CAREER_TRACKS.items() if v.lower().replace("/","_")==tn or v.lower()==tn), None)
    perf = career.get("performance")
    if tid is not None or perf is not None:
        mgr.set_sim_career(nid, job_type=tid, job_performance=perf); changes += 1
    budget = data.get("family_budget"); fid = data.get("family_id")
    if budget is not None and fid is not None and fid in mgr.families:
        mgr.set_family_money(fid, int(budget)); changes += 1
    if changes > 0:
        mgr.save()
        print(f"Homecoming complete. {changes} fields written to {args.file}")
        print(f"Welcome home, {data.get('name', 'Sim')}.")
    else: print("No changes to write.")

def cmd_character_sync(args):
    """Compare save file against CHARACTER.yml, emit merge events for the LLM."""
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    save_tr = _read_traits(n.person_data); save_sk = _read_skills(n.person_data); save_dm = _read_demo(n.person_data)
    yp = Path(args.character_yml)
    if not yp.is_file():
        _emit([{"type":"NEW_CHARACTER","severity":"action",
                "message":f"No CHARACTER.yml at {yp}. Run: obliterator character uplift {args.file} '{args.name}'"}], args.format)
        return
    yt, ys, yd, yr = _parse_character_yml(yp.read_text())
    events = []; drift = 0
    for t in ["neat","outgoing","active","playful","nice","generous"]:
        sv = save_tr.get(t,{}).get("display"); yv = yt.get(t)
        if sv is None: continue
        if yv is None or sv != yv:
            events.append({"type":"TRAIT_DRIFT","severity":"warning","field":t,"save":sv,"yaml":yv,
                           "message":f"{t}: save={sv} vs yaml={yv}"}); drift += 1
        else: events.append({"type":"TRAIT_MATCH","severity":"ok","field":t,"value":sv,"message":f"{t}: {sv} (matches)"})
    for s in VISIBLE_SKILLS:
        sv = save_sk.get(s,{}).get("display"); yv = ys.get(s)
        if sv is None: continue
        if yv is None or sv > (yv or 0):
            events.append({"type":"SKILL_GAINED","severity":"info","field":s,"save":sv,"yaml":yv or 0,
                           "message":f"{s}: {yv or 0} -> {sv}"})
        elif sv < yv:
            events.append({"type":"SKILL_LOST","severity":"warning","field":s,"save":sv,"yaml":yv,
                           "message":f"{s}: {yv} -> {sv}"})
        else: events.append({"type":"SKILL_MATCH","severity":"ok","field":s,"value":sv,"message":f"{s}: {sv} (matches)"})
    if drift >= 2:
        events.append({"type":"NARRATIVE_STALE","severity":"action","drift_count":drift,
                       "message":f"{drift} traits drifted. soul_philosophy may need revision."})
    events.append({"type":"NEEDS_NOTE","severity":"info","message":"Motives are runtime state, not in save file."})
    if args.format == "table":
        actions = sum(1 for e in events if e["severity"]=="action")
        warnings = sum(1 for e in events if e["severity"]=="warning")
        print(f"SYNC: {n.name}\nSave: {args.file}  |  YAML: {args.character_yml}")
        print(f"Events: {len(events)} ({actions} actions, {warnings} warnings)\n")
        for e in events:
            icon = {"ok":"  ","info":"->","warning":"!!","action":">>"}
            print(f"  {icon.get(e['severity'],'  ')} [{e['type']}] {e['message']}")
    else: _emit({"name":n.name,"events":events}, args.format)

def cmd_family_list(args):
    """List families with budgets and house assignments."""
    mgr = _load_save(args.file)
    rows = [{"id": fid, "house": f.house_number, "budget": f.budget,
             "members": f.num_members, "status": "townie" if f.is_townie else "resident"}
            for fid, f in sorted(mgr.families.items())]
    _emit(rows, args.format, ["id","house","budget","members","status"])

def cmd_family_set_money(args):
    """Set family budget in Simoleons."""
    mgr = _load_save(args.file)
    if mgr.set_family_money(args.family_id, args.amount):
        mgr.save(); print(f"Saved. Family {args.family_id} = \u00a7{args.amount:,}")
    else: sys.exit(1)

def cmd_iff_info(args):
    """Show IFF file summary."""
    IffFile = _iff_file(); iff = IffFile.read(args.file)
    types = {}
    for c in iff.chunks:
        t = c.type_code if hasattr(c,'type_code') else type(c).__name__
        types[t] = types.get(t,0)+1
    if args.format == "table":
        print(f"IFF: {args.file}\nChunks: {len(iff.chunks)}\n\nType    Count\n----    -----")
        for t,c in sorted(types.items(), key=lambda x:-x[1]): print(f"{t:<8} {c}")
    else: _emit({"file":args.file,"chunks":len(iff.chunks),"types":types}, args.format)

def cmd_iff_chunks(args):
    """List all chunks in an IFF file."""
    IffFile = _iff_file(); iff = IffFile.read(args.file)
    rows = []
    for c in iff.chunks:
        t = c.type_code if hasattr(c,'type_code') else type(c).__name__
        if args.type and t != args.type: continue
        rows.append({"type":t,"id":c.chunk_id,"label":getattr(c,'chunk_label',''),"size":getattr(c,'chunk_size',0)})
    _emit(rows, args.format, ["type","id","label","size"])

def cmd_iff_strings(args):
    """Show string tables in an IFF file."""
    IffFile = _iff_file(); iff = IffFile.read(args.file)
    from formats.iff.chunks.str_ import STR, CTSS
    results = []
    for chunk in iff.chunks:
        if not isinstance(chunk,(STR,CTSS)): continue
        if args.chunk_id is not None and chunk.chunk_id != args.chunk_id: continue
        for idx, ls in enumerate(chunk.strings):
            for lc, entry in ls.languages.items():
                if args.lang is not None and lc != args.lang: continue
                results.append({"chunk_id":chunk.chunk_id,"index":idx,"lang":lc,"text":entry.value})
    _emit(results, args.format, ["chunk_id","index","lang","text"])

def cmd_iff_objects(args):
    """List OBJD object definitions."""
    IffFile = _iff_file(); iff = IffFile.read(args.file)
    from formats.iff.chunks.objd import OBJD
    rows = [{"id":c.chunk_id,"guid":f"0x{c.guid:08X}" if c.guid else "0x00000000",
             "label":getattr(c,'chunk_label',''),"price":c.price if hasattr(c,'price') else 0}
            for c in iff.chunks if isinstance(c,OBJD)]
    _emit(rows, args.format, ["id","guid","label","price"])

def cmd_iff_bhav(args):
    """List or disassemble BHAV behavior scripts."""
    IffFile = _iff_file(); iff = IffFile.read(args.file)
    from formats.iff.chunks.bhav import BHAV
    if args.id is not None:
        for c in iff.chunks:
            if isinstance(c,BHAV) and c.chunk_id == args.id:
                print(f"BHAV #{c.chunk_id}: {getattr(c,'chunk_label','')}\nInstructions: {len(c.instructions)}")
                for i,inst in enumerate(c.instructions):
                    op = inst.opcode if hasattr(inst,'opcode') else 0
                    tt = inst.true_pointer if hasattr(inst,'true_pointer') else 0
                    ft = inst.false_pointer if hasattr(inst,'false_pointer') else 0
                    print(f"  [{i:>3}] opcode=0x{op:04X}  T->{tt}  F->{ft}")
                return
        print(f"ERROR: BHAV #{args.id} not found", file=sys.stderr); sys.exit(1)
    rows = [{"id":c.chunk_id,"label":getattr(c,'chunk_label',''),"instructions":len(c.instructions)}
            for c in iff.chunks if isinstance(c,BHAV)]
    _emit(rows, args.format, ["id","label","instructions"])

def cmd_far_list(args):
    """List contents of a .far archive."""
    try:
        FAR1Archive = _far1(); arc = FAR1Archive(args.file)
        rows = [{"index":i,"name":e.filename,"size":e.file_size1} for i,e in enumerate(arc.entries)]
        if args.format == "table": print(f"FAR: {args.file} ({len(rows)} files)")
        _emit(rows, args.format, ["index","name","size"])
    except Exception as e: print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)

def cmd_far_extract(args):
    """Extract files from .far archive."""
    try:
        FAR1Archive = _far1(); arc = FAR1Archive(args.file)
        out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
        if args.name:
            data = arc.get_entry(args.name)
            if data is None: print(f"ERROR: '{args.name}' not found", file=sys.stderr); sys.exit(1)
            (out/args.name).write_bytes(data); print(f"Extracted: {args.name} ({len(data)} bytes)")
        else:
            arc.extract_all(str(out)); print(f"Extracted {len(arc.entries)} files to {out}")
    except Exception as e: print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)

def cmd_tmog_export(args):
    """Export .iff to IFF-OBJECT.yml (placeholder — schema defined, assembler not yet built)."""
    print("tmog export: not yet implemented. See IFF-OBJECT-SCHEMA.yml for the target format.")
    print("The BHAV assembler/disassembler and symbol table resolver are needed first.")
    print(f"File: {args.file}")

def cmd_tmog_import(args):
    """Import IFF-OBJECT.yml to .iff (placeholder — assembler not yet built)."""
    print("tmog import: not yet implemented. See IFF-OBJECT-SCHEMA.yml for the source format.")
    print(f"File: {args.yml}")


# YAML parsers for sync and come-home

def _parse_uplift_yml(text):
    """Parse SIMS-UPLIFT.yml into a dict for homecoming."""
    result = {"traits":{},"skills":{},"career":{}}; section = None
    for line in text.split("\n"):
        s = line.split("#")[0].rstrip()
        if not s: continue
        indent = len(line)-len(line.lstrip())
        if indent==0 and s.endswith(":") and not s.startswith(" "):
            w = s[:-1].strip()
            if w in ("source","identity","traits","skills","career","relationships"): section=w; continue
            else: section=None; continue
        if ":" not in s: continue
        k,_,v = s.partition(":"); k=k.strip(); v=v.strip()
        if not v or v=="{}": continue
        try: num=int(v)
        except: num=None
        if section=="source":
            if k=="neighbor_id" and num is not None: result["neighbor_id"]=num
            elif k=="guid" and num is not None: result["guid"]=num
            elif k=="family_id" and num is not None: result["family_id"]=num
            elif k=="family_budget" and num is not None: result["family_budget"]=num
        elif section=="identity":
            if k=="name": result["name"]=v
            elif k in ("age","gender","skin_color","zodiac"): result[k]=v
        elif section=="traits" and num is not None: result["traits"][k]=num
        elif section=="skills" and num is not None: result["skills"][k]=num
        elif section=="career":
            if k=="track": result["career"]["track"]=v
            elif k=="performance" and num is not None: result["career"]["performance"]=num
    return result

def _parse_character_yml(text):
    """Parse CHARACTER.yml sims: block for sync comparison."""
    traits={}; skills={}; demo={}; rels={}; section=None; sub=None
    for line in text.split("\n"):
        s = line.split("#")[0].rstrip()
        if not s: continue
        indent = len(line)-len(line.lstrip())
        if indent<=2 and "sims:" in s: section="sims"; continue
        if indent<=2 and "relationships:" in s and section!="sims": section="rels"; continue
        if s.endswith(":") and indent==0: section=None; continue
        if section=="sims":
            if "traits:" in s and indent<=4: sub="traits"; continue
            elif "skills:" in s and indent<=4: sub="skills"; continue
            elif "career:" in s and indent<=4: sub="career"; continue
            elif "identity:" in s and indent<=4: sub="identity"; continue
            elif s.endswith(":") and indent<=4: sub=None; continue
            if ":" in s:
                k,_,v = s.partition(":"); k=k.strip(); v=v.strip()
                if not v: continue
                try: num=int(v)
                except: num=None
                if sub=="traits" and num is not None: traits[k]=num
                elif sub=="skills" and num is not None: skills[k]=num
                elif sub=="career":
                    if k=="track": demo["career"]=v
                elif sub=="identity": demo[k]=v
    return traits, skills, demo, rels


# Parser builder — walks the COMMANDS tree and creates argparse hierarchy.
# Each group becomes a subparser. Each command within becomes a sub-subparser.
# `obliterator character --help` lists character subcommands.
# `obliterator character uplift --help` shows uplift arguments.

def build_parser():
    """Build argparse hierarchy from COMMANDS tree."""
    parser = argparse.ArgumentParser(
        prog="obliterator",
        description="One CLI to rule The Sims 1 files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Use 'obliterator <group> --help' to see subcommands.\n"
               "Formats: table json yaml csv raw",
    )
    for opt in GLOBAL_OPTS:
        kw = {"help": opt["help"]}
        if "choices" in opt: kw["choices"] = opt["choices"]
        if "default" in opt: kw["default"] = opt["default"]
        parser.add_argument(*opt["flags"], **kw)

    groups = parser.add_subparsers(dest="group", help="Command group")
    dispatch = {}

    for group_name, group_spec in COMMANDS.items():
        group_parser = groups.add_parser(group_name, help=group_spec["help"])
        commands = group_parser.add_subparsers(dest="command", help="Command")

        for cmd_name, cmd_spec in group_spec["commands"].items():
            cmd_parser = commands.add_parser(cmd_name, help=cmd_spec["help"])
            for a in cmd_spec.get("args", []):
                kw = {"help": a["help"]}
                if "type" in a: kw["type"] = a["type"]
                cmd_parser.add_argument(a["name"], **kw)
            for o in cmd_spec.get("opts", []):
                kw = {"help": o["help"]}
                if "type" in o: kw["type"] = o["type"]
                if "choices" in o: kw["choices"] = o["choices"]
                if "default" in o: kw["default"] = o["default"]
                cmd_parser.add_argument(*o["flags"], **kw)

            fn_name = f"cmd_{group_name}_{cmd_name}".replace("-", "_")
            dispatch[(group_name, cmd_name)] = globals().get(fn_name)

    return parser, dispatch


def main():
    """Parse args and run the requested command."""
    parser, dispatch = build_parser()
    args = parser.parse_args()
    if not args.group:
        parser.print_help(); sys.exit(0)
    if not getattr(args, 'command', None):
        # Show group help
        for act in parser._subparsers._actions:
            if isinstance(act, argparse._SubParsersAction):
                act.choices[args.group].print_help()
        sys.exit(0)
    fn = dispatch.get((args.group, args.command))
    if fn: fn(args)
    else:
        print(f"Command not implemented: {args.group} {args.command}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
