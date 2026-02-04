"""
Theme and color definitions for SimObliterator GUI.
Volcanic-inspired color scheme from FreeSO.
"""

import dearpygui.dearpygui as dpg


# =============================================================================
# APPLICATION COLORS (RGBA 0-255)
# =============================================================================
class Colors:
    """Global application color palette."""
    BG_DARK = (20, 20, 25, 255)
    BG_PANEL = (28, 28, 35, 255)
    BG_CHILD = (35, 35, 45, 255)
    TITLE_BG = (40, 45, 55, 255)
    TITLE_ACTIVE = (55, 65, 85, 255)
    FRAME_BG = (45, 45, 55, 255)
    BUTTON = (55, 75, 100, 255)
    BUTTON_HOVER = (75, 95, 130, 255)
    BUTTON_ACTIVE = (65, 85, 115, 255)
    TEXT_DIM = (140, 140, 150, 255)
    TEXT_BRIGHT = (220, 220, 230, 255)
    ACCENT_GREEN = (100, 200, 120, 255)
    ACCENT_BLUE = (100, 150, 220, 255)
    ACCENT_YELLOW = (220, 200, 100, 255)
    ACCENT_RED = (220, 100, 100, 255)
    SEPARATOR = (60, 60, 70, 255)
    SCROLLBAR = (50, 50, 60, 255)
    SCROLLBAR_GRAB = (80, 80, 95, 255)


# =============================================================================
# NODE COLORS (Volcanic/FreeSO inspired)
# =============================================================================
class NodeColors:
    """BHAV node category colors - based on Volcanic."""
    SUBROUTINE = (50, 180, 80, 255)      # Green
    CONTROL = (230, 200, 50, 255)        # Yellow
    DEBUG = (230, 80, 80, 255)           # Red
    MATH = (50, 200, 200, 255)           # Cyan
    SIM = (180, 80, 180, 255)            # Purple
    OBJECT = (80, 130, 230, 255)         # Blue
    LOOKS = (50, 80, 160, 255)           # Dark Blue
    POSITION = (40, 50, 130, 255)        # Navy
    UNKNOWN = (120, 120, 130, 255)       # Gray


def setup_theme():
    """Apply the global application theme."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, Colors.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.BG_CHILD)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, Colors.BG_PANEL)
            
            # Title bars
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, Colors.TITLE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, Colors.TITLE_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, Colors.TITLE_BG)
            
            # Frames
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Colors.FRAME_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (55, 55, 65, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (65, 65, 75, 255))
            
            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, Colors.BUTTON)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Colors.BUTTON_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, Colors.BUTTON_ACTIVE)
            
            # Headers (tree nodes, collapsing headers)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (50, 55, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (60, 70, 90, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (70, 80, 100, 255))
            
            # Scrollbar
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, Colors.SCROLLBAR)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, Colors.SCROLLBAR_GRAB)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (90, 90, 105, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (100, 100, 115, 255))
            
            # Misc
            dpg.add_theme_color(dpg.mvThemeCol_Separator, Colors.SEPARATOR)
            dpg.add_theme_color(dpg.mvThemeCol_Text, Colors.TEXT_BRIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, Colors.TEXT_DIM)
            
            # Tabs
            dpg.add_theme_color(dpg.mvThemeCol_Tab, Colors.TITLE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, Colors.BUTTON_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, Colors.TITLE_ACTIVE)
            
            # Style
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
    
    dpg.bind_theme(global_theme)
    return global_theme
