#!/usr/bin/env python3
"""obliterator.py — LLM-friendly CLI for SimObliterator Suite.

Sniffable Python wrapper providing a coherent command structure
for reading, inspecting, and editing The Sims 1 save files.
Designed for both human and LLM consumption.

Usage:
    python obliterator.py inspect <neighborhood.iff>
    python obliterator.py families <neighborhood.iff>
    python obliterator.py character <neighborhood.iff> <name>
    python obliterator.py traits <neighborhood.iff> <name>
    python obliterator.py set-trait <neighborhood.iff> <name> <trait> <value>
    python obliterator.py set-skill <neighborhood.iff> <name> <skill> <value>
    python obliterator.py set-money <neighborhood.iff> <family-id> <amount>
    python obliterator.py uplift <neighborhood.iff> <name> [--output <path>]
    python obliterator.py dump-raw <neighborhood.iff> <name>

Output formats (append to any command):
    --format table    (default, human-readable)
    --format json     (machine-readable)
    --format yaml     (MOOLLM-compatible)

PersonData indices verified against original Sims 1 source code
(PersonData.h, 12/17/99). NOT FreeSO/TSO indices.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add SimObliterator src to path
_src_dir = Path(__file__).parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from Tools.save_editor.save_manager import SaveManager, PersonData


# Personality trait display names and their 0-10 scale poles
TRAIT_POLES = {
    "nice":     ("Grouchy", "Nice"),
    "active":   ("Lazy", "Active"),
    "generous": ("Selfish", "Generous"),
    "playful":  ("Serious", "Playful"),
    "outgoing": ("Shy", "Outgoing"),
    "neat":     ("Sloppy", "Neat"),
}

# Skill display names
SKILL_NAMES = [
    "cooking", "mechanical", "charisma", "logic",
    "body", "creativity", "cleaning",
]

# Career track names (from Careers.iff, IDs 1-9 plus 0=unemployed)
CAREER_TRACKS = {
    0: "Unemployed",
    1: "Cooking/Culinary",
    2: "Entertainment",
    3: "Law Enforcement",
    4: "Medicine",
    5: "Military",
    6: "Politics",
    7: "Pro Athlete",
    8: "Science",
    9: "Xtreme",
}

# Zodiac signs (PersonData[70], 0=uncomputed, 1-12)
ZODIAC_SIGNS = {
    0: "Uncomputed", 1: "Aries", 2: "Taurus", 3: "Gemini",
    4: "Cancer", 5: "Leo", 6: "Virgo", 7: "Libra",
    8: "Scorpio", 9: "Sagittarius", 10: "Capricorn",
    11: "Aquarius", 12: "Pisces",
}


def load_save(path: str) -> SaveManager:
    """Load a neighborhood save file. Exits on failure."""
    mgr = SaveManager(path)
    if not mgr.load():
        print(f"ERROR: Failed to load {path}", file=sys.stderr)
        sys.exit(1)
    return mgr


def find_neighbor(mgr: SaveManager, name: str):
    """Find a neighbor by name (case-insensitive partial match).

    Returns (neighbor_id, neighbor_data) or exits with error.
    """
    name_lower = name.lower()
    matches = []
    for nid, neigh in mgr.neighbors.items():
        if name_lower in neigh.name.lower():
            matches.append((nid, neigh))

    if not matches:
        print(f"ERROR: No character matching '{name}' found.", file=sys.stderr)
        available = [n.name for n in mgr.neighbors.values() if n.name]
        if available:
            print(f"Available: {', '.join(sorted(available))}", file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        exact = [(nid, n) for nid, n in matches if n.name.lower() == name_lower]
        if len(exact) == 1:
            return exact[0]
        print(f"ERROR: Multiple matches for '{name}':", file=sys.stderr)
        for nid, n in matches:
            print(f"  [{nid}] {n.name}", file=sys.stderr)
        sys.exit(1)

    return matches[0]


def get_person_data_value(person_data: list, index: int) -> Optional[int]:
    """Safely read a value from the person_data array."""
    if person_data and 0 <= index < len(person_data):
        return person_data[index]
    return None


def read_traits(person_data: list) -> dict:
    """Extract personality traits from person_data.

    Returns dict of trait_name -> (raw_value, display_value).
    Raw values are 0-1000 internal scale. Display is 0-10.
    """
    result = {}
    for name, index in PersonData.get_personality_indices():
        raw = get_person_data_value(person_data, index)
        if raw is not None:
            display = round(raw / 100)
            result[name.lower()] = {"raw": raw, "display": display}
    return result


def read_skills(person_data: list) -> dict:
    """Extract skills from person_data.

    Returns dict of skill_name -> (raw_value, display_value).
    """
    result = {}
    for name, index in PersonData.get_skill_indices():
        raw = get_person_data_value(person_data, index)
        if raw is not None:
            display = round(raw / 100)
            result[name.lower()] = {"raw": raw, "display": display}
    return result


def read_demographics(person_data: list) -> dict:
    """Extract demographic fields from person_data."""
    age_val = get_person_data_value(person_data, PersonData.PERSON_AGE)
    gender_val = get_person_data_value(person_data, PersonData.GENDER)
    skin_val = get_person_data_value(person_data, PersonData.SKIN_COLOR)
    zodiac_val = get_person_data_value(person_data, PersonData.ZODIAC_SIGN)
    job_type = get_person_data_value(person_data, PersonData.JOB_TYPE)
    job_perf = get_person_data_value(person_data, PersonData.JOB_PERFORMANCE)

    return {
        "age": "child" if age_val == 0 else "adult" if age_val == 1 else str(age_val),
        "gender": "male" if gender_val == 0 else "female" if gender_val == 1 else str(gender_val),
        "skin_color": {0: "light", 1: "medium", 2: "dark"}.get(skin_val, str(skin_val)),
        "zodiac": ZODIAC_SIGNS.get(zodiac_val, f"unknown ({zodiac_val})"),
        "career": CAREER_TRACKS.get(job_type, f"unknown ({job_type})"),
        "job_performance": job_perf,
    }


def format_character_table(name: str, traits: dict, skills: dict,
                           demographics: dict, relationships: dict) -> str:
    """Format character data as a human-readable table."""
    lines = [f"{'=' * 50}", f"  {name}", f"{'=' * 50}"]

    lines.append(f"\n  Age: {demographics['age']}  |  Gender: {demographics['gender']}  |  Zodiac: {demographics['zodiac']}")
    lines.append(f"  Career: {demographics['career']}  |  Performance: {demographics['job_performance']}")

    lines.append(f"\n  PERSONALITY TRAITS (0-10)")
    lines.append(f"  {'─' * 40}")
    for trait_name in ["neat", "outgoing", "active", "playful", "nice"]:
        if trait_name in traits:
            val = traits[trait_name]["display"]
            low, high = TRAIT_POLES.get(trait_name, ("", ""))
            bar = "█" * val + "░" * (10 - val)
            lines.append(f"  {low:>8} [{bar}] {high:<8}  {val:>2}")

    lines.append(f"\n  SKILLS (0-10)")
    lines.append(f"  {'─' * 40}")
    for skill_name in SKILL_NAMES:
        if skill_name in skills:
            val = skills[skill_name]["display"]
            bar = "█" * val + "░" * (10 - val)
            lines.append(f"  {skill_name:>12} [{bar}] {val:>2}")

    if relationships:
        lines.append(f"\n  RELATIONSHIPS")
        lines.append(f"  {'─' * 40}")
        for rel_id, rel_vals in list(relationships.items())[:10]:
            daily = rel_vals[0] if len(rel_vals) > 0 else "?"
            lifetime = rel_vals[1] if len(rel_vals) > 1 else "?"
            lines.append(f"  Neighbor {rel_id}: daily={daily}, lifetime={lifetime}")

    return "\n".join(lines)


def format_character_json(name: str, nid: int, traits: dict, skills: dict,
                          demographics: dict, relationships: dict) -> str:
    """Format character data as JSON."""
    data = {
        "name": name,
        "neighbor_id": nid,
        "demographics": demographics,
        "traits": {k: v["display"] for k, v in traits.items()},
        "traits_raw": {k: v["raw"] for k, v in traits.items()},
        "skills": {k: v["display"] for k, v in skills.items()},
        "skills_raw": {k: v["raw"] for k, v in skills.items()},
        "relationships": {str(k): v for k, v in relationships.items()},
    }
    return json.dumps(data, indent=2)


def format_character_yaml(name: str, nid: int, traits: dict, skills: dict,
                          demographics: dict, relationships: dict) -> str:
    """Format character data as MOOLLM-compatible YAML.

    Outputs a sims: block ready for inclusion in CHARACTER.yml.
    """
    lines = [f"# {name} — Sims 1 PersonData (verified against source)"]
    lines.append(f"# Neighbor ID: {nid}")

    lines.append(f"\nsims:")
    lines.append(f"  traits:")
    for trait_name in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
        if trait_name in traits:
            val = traits[trait_name]["display"]
            low, high = TRAIT_POLES.get(trait_name, ("", ""))
            lines.append(f"    {trait_name}: {val:<3}  # {low} {val}/10 {high}")

    lines.append(f"  skills:")
    for skill_name in SKILL_NAMES:
        if skill_name in skills:
            val = skills[skill_name]["display"]
            lines.append(f"    {skill_name}: {val}")

    lines.append(f"  career:")
    lines.append(f"    track: {demographics['career'].lower().replace('/', '_')}")
    lines.append(f"    performance: {demographics['job_performance']}")

    lines.append(f"  identity:")
    lines.append(f"    age: {demographics['age']}")
    lines.append(f"    gender: {demographics['gender']}")
    lines.append(f"    zodiac: {demographics['zodiac'].lower()}")

    return "\n".join(lines)


def cmd_inspect(args):
    """List all characters and families in a neighborhood save."""
    mgr = load_save(args.file)
    print(f"Neighborhood: {args.file}")
    print(f"Families: {len(mgr.families)}  |  Characters: {len(mgr.neighbors)}\n")

    if mgr.families:
        print("FAMILIES")
        print("─" * 50)
        for fid, fam in sorted(mgr.families.items()):
            status = "townie" if fam.is_townie else f"house {fam.house_number}"
            print(f"  [{fid}] {fam.chunk_id:>4}  §{fam.budget:>8,}  "
                  f"{fam.num_members} members  ({status})")

    if mgr.neighbors:
        print("\nCHARACTERS")
        print("─" * 50)
        for nid, neigh in sorted(mgr.neighbors.items()):
            traits = read_traits(neigh.person_data) if neigh.person_data else {}
            trait_str = " ".join(
                f"{k[0].upper()}{v['display']}"
                for k, v in traits.items()
                if k in ["neat", "outgoing", "active", "playful", "nice"]
            )
            print(f"  [{nid:>3}] {neigh.name:<25} {trait_str}")


def cmd_families(args):
    """List families with budget details."""
    mgr = load_save(args.file)
    for fid, fam in sorted(mgr.families.items()):
        print(f"Family {fid}: §{fam.budget:,}  "
              f"house={fam.house_number}  members={fam.num_members}  "
              f"{'townie' if fam.is_townie else 'resident'}")


def cmd_character(args):
    """Show full character data."""
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    traits = read_traits(neigh.person_data)
    skills = read_skills(neigh.person_data)
    demographics = read_demographics(neigh.person_data)

    if args.format == "json":
        print(format_character_json(neigh.name, nid, traits, skills,
                                    demographics, neigh.relationships))
    elif args.format == "yaml":
        print(format_character_yaml(neigh.name, nid, traits, skills,
                                    demographics, neigh.relationships))
    else:
        print(format_character_table(neigh.name, traits, skills,
                                     demographics, neigh.relationships))


def cmd_traits(args):
    """Show just personality traits for a character."""
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    traits = read_traits(neigh.person_data)
    print(f"{neigh.name} — Personality Traits")
    for trait_name in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
        if trait_name in traits:
            val = traits[trait_name]["display"]
            raw = traits[trait_name]["raw"]
            low, high = TRAIT_POLES.get(trait_name, ("", ""))
            bar = "█" * val + "░" * (10 - val)
            print(f"  {low:>8} [{bar}] {high:<8}  {val:>2}  (raw: {raw})")


def cmd_set_trait(args):
    """Set a personality trait value."""
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    raw_value = int(args.value) * 100
    if mgr.set_sim_personality(nid, args.trait, raw_value):
        mgr.save()
        print(f"Saved to {args.file}")
    else:
        sys.exit(1)


def cmd_set_skill(args):
    """Set a skill level."""
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    raw_value = int(args.value) * 100
    if mgr.set_sim_skill(nid, args.skill, raw_value):
        mgr.save()
        print(f"Saved to {args.file}")
    else:
        sys.exit(1)


def cmd_set_money(args):
    """Set a family's budget."""
    mgr = load_save(args.file)
    family_id = int(args.family_id)
    amount = int(args.amount)
    if mgr.set_family_money(family_id, amount):
        mgr.save()
        print(f"Saved to {args.file}")
    else:
        sys.exit(1)


def cmd_dump_raw(args):
    """Dump raw person_data array for debugging.

    Shows all 80+ fields with their indices and values.
    Cross-references known field names from PersonData.h.
    """
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    # Build reverse index of known field names
    known = {}
    for attr_name in dir(PersonData):
        val = getattr(PersonData, attr_name)
        if isinstance(val, int) and not attr_name.startswith("_"):
            known.setdefault(val, []).append(attr_name)

    print(f"Raw PersonData for {neigh.name} ({len(neigh.person_data)} fields)")
    print(f"{'─' * 60}")
    for i, value in enumerate(neigh.person_data):
        names = known.get(i, [])
        name_str = ", ".join(names) if names else ""
        flag = " *" if value != 0 else ""
        print(f"  [{i:>3}] {value:>6}{flag:>2}  {name_str}")


def cmd_uplift(args):
    """Generate MOOLLM CHARACTER.yml from a Sim's save data.

    Reads PersonData, extracts traits/skills/demographics, and outputs
    a YAML file ready for inclusion in a MOOLLM character directory.
    """
    mgr = load_save(args.file)
    nid, neigh = find_neighbor(mgr, args.name)

    if not neigh.person_data:
        print(f"ERROR: {neigh.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    traits = read_traits(neigh.person_data)
    skills = read_skills(neigh.person_data)
    demographics = read_demographics(neigh.person_data)

    yaml_output = format_character_yaml(neigh.name, nid, traits, skills,
                                        demographics, neigh.relationships)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_output + "\n")
        print(f"Wrote {output_path}")
    else:
        print(yaml_output)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="obliterator",
        description="LLM-friendly CLI for SimObliterator Suite. "
                    "Read, inspect, and edit The Sims 1 save files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="PersonData indices verified against Sims 1 source "
               "(PersonData.h, 12/17/99).",
    )
    parser.add_argument("--format", choices=["table", "json", "yaml"],
                        default="table", help="Output format (default: table)")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # inspect
    p = sub.add_parser("inspect", help="List all characters and families")
    p.add_argument("file", help="Path to Neighborhood.iff")

    # families
    p = sub.add_parser("families", help="List families with budgets")
    p.add_argument("file", help="Path to Neighborhood.iff")

    # character
    p = sub.add_parser("character", help="Show full character data")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name (partial match OK)")

    # traits
    p = sub.add_parser("traits", help="Show personality traits")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name")

    # set-trait
    p = sub.add_parser("set-trait", help="Set a personality trait")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name")
    p.add_argument("trait", choices=list(TRAIT_POLES.keys()), help="Trait name")
    p.add_argument("value", type=int, help="Value 0-10")

    # set-skill
    p = sub.add_parser("set-skill", help="Set a skill level")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name")
    p.add_argument("skill", choices=SKILL_NAMES, help="Skill name")
    p.add_argument("value", type=int, help="Value 0-10")

    # set-money
    p = sub.add_parser("set-money", help="Set family budget")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("family_id", help="Family ID number")
    p.add_argument("amount", help="Amount in Simoleons")

    # dump-raw
    p = sub.add_parser("dump-raw", help="Dump raw PersonData array")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name")

    # uplift
    p = sub.add_parser("uplift", help="Generate MOOLLM YAML from save data")
    p.add_argument("file", help="Path to Neighborhood.iff")
    p.add_argument("name", help="Character name")
    p.add_argument("--output", "-o", help="Output file path (default: stdout)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "inspect": cmd_inspect,
        "families": cmd_families,
        "character": cmd_character,
        "traits": cmd_traits,
        "set-trait": cmd_set_trait,
        "set-skill": cmd_set_skill,
        "set-money": cmd_set_money,
        "dump-raw": cmd_dump_raw,
        "uplift": cmd_uplift,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
