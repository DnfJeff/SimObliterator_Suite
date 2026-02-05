#!/usr/bin/env python3
"""
SimObliterator Suite - UNIFIED TEST SYSTEM

Main test runner that loads and executes test modules.

USAGE:
  python tests.py                    # Run ALL tests (API + Game)
  python tests.py --api              # API tests only (no game files needed)
  python tests.py --game             # Game file tests only
  python tests.py --verbose          # Verbose output
  python tests.py --quick            # Quick API tests only

TEST MODULES:
  test_api.py   - API/import tests (174 tests) - no game files required
  test_game.py  - Real game file tests (73 tests) - requires test_paths.txt config

TOTAL: 247+ tests
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(
        description="SimObliterator Suite - Unified Test System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests.py           # Run all tests
  python tests.py --api     # API tests only
  python tests.py --game    # Game file tests only
  python tests.py --verbose # Detailed output
"""
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--api', action='store_true', help='Run API tests only')
    parser.add_argument('--game', action='store_true', help='Run game file tests only')
    parser.add_argument('-q', '--quick', action='store_true', help='Quick API tests only (alias for --api)')
    args = parser.parse_args()
    
    # Default: run both if neither specified
    run_api = args.api or args.quick or (not args.api and not args.game)
    run_game = args.game or (not args.api and not args.game and not args.quick)
    
    # Print header (ASCII-safe for .txt export)
    print("+" + "="*60 + "+")
    print("|  SIMOBLITERATOR SUITE - UNIFIED TEST SYSTEM               |")
    print("|  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                        |")
    print("+" + "="*60 + "+")
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    # API Tests
    if run_api:
        print("\n" + "="*60)
        print("  MODULE: API TESTS (test_api.py)")
        print("="*60)
        
        try:
            from test_api import run_all_tests as run_api_tests, TestResults
            results = TestResults()
            run_api_tests(results)
            
            total_passed += results.passed
            total_failed += results.failed
            total_skipped += results.skipped
            
            print(f"\n  -- API: {results.passed} passed, {results.failed} failed, {results.skipped} skipped")
            
        except ImportError as e:
            print(f"  [FAIL] Failed to import test_api: {e}")
            total_failed += 1
        except Exception as e:
            print(f"  [FAIL] API tests error: {e}")
            total_failed += 1
    
    # Game File Tests
    if run_game:
        print("\n" + "="*60)
        print("  MODULE: GAME FILE TESTS (test_game.py)")
        print("="*60)
        
        try:
            from test_game import run_all_tests as run_game_tests
            passed, failed, skipped = run_game_tests(verbose=args.verbose)
            
            total_passed += passed
            total_failed += failed
            total_skipped += skipped
            
            print(f"\n  -- Game: {passed} passed, {failed} failed, {skipped} skipped")
            
        except ImportError as e:
            print(f"  [FAIL] Failed to import test_game: {e}")
            total_failed += 1
        except Exception as e:
            print(f"  [FAIL] Game tests error: {e}")
            total_failed += 1
    
    # Final Summary
    total = total_passed + total_failed + total_skipped
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total:   {total}")
    print(f"Passed:  {total_passed} [OK]")
    print(f"Failed:  {total_failed} [FAIL]")
    print(f"Skipped: {total_skipped} [SKIP]")
    
    if total_failed == 0:
        print("\n*** ALL TESTS PASSED! ***")
        return 0
    else:
        print(f"\n(!!) {total_failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
