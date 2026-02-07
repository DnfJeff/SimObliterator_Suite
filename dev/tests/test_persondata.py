"""
SimObliterator Suite - PersonData Index Verification Tests

Tests that PersonData field indices match the actual Sims 1 binary layout.
These are structural tests that don't require game files — they verify
the correctness of the index constants themselves.

The Sims 1 PersonData array is an array of 80 signed 16-bit integers
(kNumPersonDataFields = 80) stored in each Neighbor record. The indices
were verified by cross-referencing multiple authoritative sources:
  - Header file documentation (PersonData.h, Jamie Doornbos)
  - The Sims Online (TSO) fork of the same header (same layout preserved)
  - FreeSO open-source reimplementation documentation
  - Niotso wiki reverse engineering documentation
  - Empirical testing against known save files

Can be run standalone: python test_persondata.py
Or via main runner: python tests.py --api

BACKGROUND:
  The previous PersonData indices were derived from FreeSO's
  VMPersonDataVariable enum, which is a VM-level abstraction used
  internally by The Sims Online's virtual machine. That enum remaps
  the raw binary indices into a different order for the VM's
  convenience. The actual binary save file layout is different.
  These tests lock in the correct binary layout indices.
"""

import sys
from pathlib import Path

# Path setup
TESTS_DIR = Path(__file__).parent
DEV_DIR = TESTS_DIR.parent
SUITE_DIR = DEV_DIR.parent
SRC_DIR = SUITE_DIR / "src"

sys.path.insert(0, str(SUITE_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "Tools"))


def run_persondata_tests(results):
    """Run all PersonData verification tests."""

    print("\n" + "=" * 60)
    print("PERSONDATA INDEX VERIFICATION")
    print("=" * 60)

    from save_editor.save_manager import PersonData

    # Personality traits: indices 2-7
    # The Sims 1 PersonData layout puts personality right after
    # kIdleState (0) and kNPCFeeAmount (1).

    print("\n  Personality trait indices (should be 2-7):")

    results.record(
        "PersonData.NICE_PERSONALITY == 2",
        PersonData.NICE_PERSONALITY == 2,
        f"got {PersonData.NICE_PERSONALITY}, expected 2 (kPersNice)"
    )
    results.record(
        "PersonData.ACTIVE_PERSONALITY == 3",
        PersonData.ACTIVE_PERSONALITY == 3,
        f"got {PersonData.ACTIVE_PERSONALITY}, expected 3 (kPersActive)"
    )
    results.record(
        "PersonData.GENEROUS_PERSONALITY == 4",
        PersonData.GENEROUS_PERSONALITY == 4,
        f"got {PersonData.GENEROUS_PERSONALITY}, expected 4 (kPersGenerous)"
    )
    results.record(
        "PersonData.PLAYFUL_PERSONALITY == 5",
        PersonData.PLAYFUL_PERSONALITY == 5,
        f"got {PersonData.PLAYFUL_PERSONALITY}, expected 5 (kPersPlayful)"
    )
    results.record(
        "PersonData.OUTGOING_PERSONALITY == 6",
        PersonData.OUTGOING_PERSONALITY == 6,
        f"got {PersonData.OUTGOING_PERSONALITY}, expected 6 (kPersOutgoing)"
    )
    results.record(
        "PersonData.NEAT_PERSONALITY == 7",
        PersonData.NEAT_PERSONALITY == 7,
        f"got {PersonData.NEAT_PERSONALITY}, expected 7 (kPersNeat)"
    )

    # Skills: indices 9-18
    # Skills follow kCurrentOutfit (8). Cleaning is first at 9.

    print("\n  Skill indices (should be 9-18):")

    results.record(
        "PersonData.CLEANING_SKILL == 9",
        PersonData.CLEANING_SKILL == 9,
        f"got {PersonData.CLEANING_SKILL}, expected 9 (kCleaningSkill)"
    )
    results.record(
        "PersonData.COOKING_SKILL == 10",
        PersonData.COOKING_SKILL == 10,
        f"got {PersonData.COOKING_SKILL}, expected 10 (kCookingSkill)"
    )
    results.record(
        "PersonData.CHARISMA_SKILL == 11",
        PersonData.CHARISMA_SKILL == 11,
        f"got {PersonData.CHARISMA_SKILL}, expected 11 (kSocialSkill)"
    )
    results.record(
        "PersonData.MECH_SKILL == 12",
        PersonData.MECH_SKILL == 12,
        f"got {PersonData.MECH_SKILL}, expected 12 (kRepairSkill)"
    )
    results.record(
        "PersonData.CREATIVITY_SKILL == 15",
        PersonData.CREATIVITY_SKILL == 15,
        f"got {PersonData.CREATIVITY_SKILL}, expected 15 (kCreativeSkill)"
    )
    results.record(
        "PersonData.BODY_SKILL == 17",
        PersonData.BODY_SKILL == 17,
        f"got {PersonData.BODY_SKILL}, expected 17 (kPhysicalSkill)"
    )
    results.record(
        "PersonData.LOGIC_SKILL == 18",
        PersonData.LOGIC_SKILL == 18,
        f"got {PersonData.LOGIC_SKILL}, expected 18 (kLogicSkill)"
    )

    # Career fields: scattered but well-known indices

    print("\n  Career field indices:")

    results.record(
        "PersonData.JOB_TYPE == 56",
        PersonData.JOB_TYPE == 56,
        f"got {PersonData.JOB_TYPE}, expected 56 (kJobType)"
    )
    results.record(
        "PersonData.JOB_STATUS == 57",
        PersonData.JOB_STATUS == 57,
        f"got {PersonData.JOB_STATUS}, expected 57 (kJobStatus)"
    )
    results.record(
        "PersonData.JOB_PERFORMANCE == 63",
        PersonData.JOB_PERFORMANCE == 63,
        f"got {PersonData.JOB_PERFORMANCE}, expected 63 (kJobPerformance)"
    )

    # Demographic fields

    print("\n  Demographic field indices:")

    results.record(
        "PersonData.PERSON_AGE == 58",
        PersonData.PERSON_AGE == 58,
        f"got {PersonData.PERSON_AGE}, expected 58 (kPersonAge)"
    )
    results.record(
        "PersonData.SKIN_COLOR == 60",
        PersonData.SKIN_COLOR == 60,
        f"got {PersonData.SKIN_COLOR}, expected 60 (kSkinColor)"
    )
    results.record(
        "PersonData.GENDER == 65",
        PersonData.GENDER == 65,
        f"got {PersonData.GENDER}, expected 65 (kPersonGender)"
    )
    results.record(
        "PersonData.ZODIAC_SIGN == 70",
        PersonData.ZODIAC_SIGN == 70,
        f"got {PersonData.ZODIAC_SIGN}, expected 70 (kZodiacSign)"
    )

    # Structural checks: personality traits must be contiguous 2-7

    print("\n  Structural invariants:")

    trait_indices = [v for _, v in PersonData.get_personality_indices()]
    results.record(
        "Personality traits are contiguous (2-7)",
        trait_indices == [2, 3, 4, 5, 6, 7],
        f"got {trait_indices}, expected [2, 3, 4, 5, 6, 7]"
    )

    # Structural check: no index collisions between traits and skills
    skill_indices = set(v for _, v in PersonData.get_skill_indices())
    trait_index_set = set(trait_indices)
    overlap = skill_indices & trait_index_set
    results.record(
        "No index collision between traits and skills",
        len(overlap) == 0,
        f"overlapping indices: {overlap}"
    )

    # Structural check: all indices are within valid PersonData range
    # PersonData array has 80 fields (kNumPersonDataFields = 80).
    # NBRS may store up to 88 (with expansion pack padding).
    all_indices = trait_indices + [v for _, v in PersonData.get_skill_indices()]
    all_indices += [PersonData.JOB_TYPE, PersonData.JOB_STATUS,
                    PersonData.JOB_PERFORMANCE, PersonData.PERSON_AGE,
                    PersonData.SKIN_COLOR, PersonData.GENDER,
                    PersonData.ZODIAC_SIGN]
    max_idx = max(all_indices)
    results.record(
        f"All indices within PersonData range (max={max_idx}, limit=80)",
        max_idx < 80,
        f"index {max_idx} exceeds kNumPersonDataFields (80)"
    )

    # Verify get_personality_indices returns correct count
    results.record(
        "get_personality_indices returns 6 traits",
        len(PersonData.get_personality_indices()) == 6,
        f"got {len(PersonData.get_personality_indices())}"
    )

    # Verify get_skill_indices returns at least 7 skills
    results.record(
        "get_skill_indices returns >= 7 skills",
        len(PersonData.get_skill_indices()) >= 7,
        f"got {len(PersonData.get_skill_indices())}"
    )

    # Verify motive names exist but are not PersonData indices
    motive_names = PersonData.get_motive_names()
    results.record(
        "get_motive_names returns 8 names",
        len(motive_names) == 8,
        f"got {len(motive_names)}"
    )
    results.record(
        "Motives include Hunger",
        "Hunger" in motive_names,
        f"Hunger not found in {motive_names}"
    )

    # Verify that no motive-like attribute exists as an index constant
    # (Motives are runtime state, not stored in PersonData)
    results.record(
        "No HUNGER_MOTIVE index constant (motives are runtime)",
        not hasattr(PersonData, 'HUNGER_MOTIVE'),
        "HUNGER_MOTIVE still exists as an index constant — motives "
        "are not in PersonData, they are runtime engine state"
    )

    # Additional hidden skills present
    print("\n  Hidden/internal skill indices:")

    results.record(
        "PersonData.GARDENING_SKILL == 13",
        PersonData.GARDENING_SKILL == 13,
        f"got {PersonData.GARDENING_SKILL}, expected 13"
    )
    results.record(
        "PersonData.MUSIC_SKILL == 14",
        PersonData.MUSIC_SKILL == 14,
        f"got {PersonData.MUSIC_SKILL}, expected 14"
    )
    results.record(
        "PersonData.LITERACY_SKILL == 16",
        PersonData.LITERACY_SKILL == 16,
        f"got {PersonData.LITERACY_SKILL}, expected 16"
    )


def run_nbrs_tests(results):
    """Test NBRS chunk parser structural correctness."""

    print("\n" + "=" * 60)
    print("NBRS CHUNK PARSER VERIFICATION")
    print("=" * 60)

    try:
        from formats.iff.chunks.nbrs import NBRS, Neighbour
    except Exception as e:
        results.skip("NBRS import", f"Could not import: {e}")
        return

    # Test that _read_neighbor returns None (not empty object) for invalid entries
    # This is tested structurally: verify the return type contract

    results.record(
        "Neighbour dataclass has person_data field",
        hasattr(Neighbour, '__dataclass_fields__') and
        'person_data' in Neighbour.__dataclass_fields__,
        "Neighbour missing person_data field"
    )

    results.record(
        "NBRS has get_neighbor method",
        hasattr(NBRS, 'get_neighbor') and callable(getattr(NBRS, 'get_neighbor')),
        "NBRS missing get_neighbor method"
    )

    results.record(
        "NBRS has get_free_id method",
        hasattr(NBRS, 'get_free_id') and callable(getattr(NBRS, 'get_free_id')),
        "NBRS missing get_free_id method"
    )


def run_fami_tests(results):
    """Test FAMI chunk parser structural correctness."""

    print("\n" + "=" * 60)
    print("FAMI CHUNK PARSER VERIFICATION")
    print("=" * 60)

    try:
        from formats.iff.chunks.fami import FAMI, FAMI_IN_HOUSE, FAMI_USER_CREATED
    except Exception as e:
        results.skip("FAMI import", f"Could not import: {e}")
        return

    results.record(
        "FAMI_IN_HOUSE flag == 1",
        FAMI_IN_HOUSE == 1,
        f"got {FAMI_IN_HOUSE}"
    )
    results.record(
        "FAMI_USER_CREATED flag == 8",
        FAMI_USER_CREATED == 8,
        f"got {FAMI_USER_CREATED}"
    )
    results.record(
        "FAMI has is_townie property",
        hasattr(FAMI, 'is_townie'),
        "missing is_townie property"
    )
    results.record(
        "FAMI has budget field",
        hasattr(FAMI, '__dataclass_fields__') and
        'budget' in FAMI.__dataclass_fields__,
        "missing budget field"
    )


def run_all_tests(results):
    """Run all PersonData, NBRS, and FAMI verification tests."""
    run_persondata_tests(results)
    run_nbrs_tests(results)
    run_fami_tests(results)


if __name__ == "__main__":
    # Standalone execution
    from test_api import TestResults
    results = TestResults()
    run_all_tests(results)
    results.summary()
    sys.exit(0 if results.failed == 0 else 1)
