#!/usr/bin/env python3
"""
SimObliterator Suite - IFF Editor & Analyzer

Standalone application for inspecting, analyzing, and editing The Sims 1 game files.

Usage:
    python launch.py
"""

import sys
import os
from pathlib import Path

# Setup paths
root_dir = Path(__file__).parent
src_dir = root_dir / "src"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(src_dir / "Tools"))
sys.path.insert(0, str(src_dir / "formats"))

os.chdir(root_dir)

# Version info
VERSION = "1.0.0"
APP_NAME = "SimObliterator Suite"


def get_version() -> str:
    """Get version from VERSION file or fallback."""
    version_file = root_dir / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return VERSION


def show_splash():
    """Show splash screen info."""
    version = get_version()
    banner = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ███████╗██╗███╗   ███╗ ██████╗ ██████╗ ██╗     ██╗████████╗       ║
║   ██╔════╝██║████╗ ████║██╔═══██╗██╔══██╗██║     ██║╚══██╔══╝       ║
║   ███████╗██║██╔████╔██║██║   ██║██████╔╝██║     ██║   ██║          ║
║   ╚════██║██║██║╚██╔╝██║██║   ██║██╔══██╗██║     ██║   ██║          ║
║   ███████║██║██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗██║   ██║          ║
║   ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝          ║
║                                                                      ║
║                    IFF Editor & Analyzer                             ║
║                       Version {version:<10}                             ║
║                                                                      ║
║   Professional tools for The Sims 1 modding & research               ║
║   Made by Dnf_Jeff                                                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """Check that required dependencies are available."""
    missing = []
    
    try:
        import dearpygui
    except ImportError:
        missing.append("dearpygui")
    
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    if missing:
        print("\n⚠️  Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\n   Install with: pip install -r requirements.txt\n")
        return False
    
    return True


def main():
    """Launch the application."""
    show_splash()
    
    if not check_dependencies():
        return 1
    
    try:
        from src.main_app import MainApp
        
        print("Starting application...")
        
        app = MainApp(width=1400, height=900)
        app.show()
        
        print("Application ready.\n")
        
        app.run()
        app.shutdown()
        
        print("\nApplication closed.")
        return 0
        
    except ImportError as e:
        print(f"\n❌ Error: Failed to import required modules: {e}")
        print("\n   Make sure you have installed dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
