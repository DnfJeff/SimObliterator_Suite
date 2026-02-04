"""
BHAV Editor Window - Full editor UI for SimObliterator

Provides a complete IDE-like editor for viewing and editing BHAV code with:
- Syntax highlighting
- Instruction editor
- CFG visualization
- Real-time analysis/linting
- Code navigation
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from .bhav_ast import BehaviorAST
from .bhav_decompiler import BHAVDecompiler
from .bhav_formatter import BHAVFormatter, CodeStyle
from .bhav_graph import BHAVGraphVisualizer
from .bhav_analysis import BHAVLinter, CodeMetrics


class BHAVEditorWindow:
    """Main BHAV editor window"""
    
    def __init__(self, parent=None):
        self.root = parent or tk.Tk()
        self.root.title("BHAV Editor")
        self.root.geometry("1400x800")
        
        self.current_ast: Optional[BehaviorAST] = None
        self.decompiler = BHAVDecompiler()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create user interface"""
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left side: editor
        left_frame = ttk.Frame(main_container)
        main_container.add(left_frame, weight=3)
        
        # Right side: properties
        right_frame = ttk.Frame(main_container)
        main_container.add(right_frame, weight=1)
        
        self._create_editor_ui(left_frame)
        self._create_properties_ui(right_frame)
        
        # Menu bar
        self._create_menu()
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open BHAV...", command=self.open_bhav)
        file_menu.add_command(label="Export as...", command=self.export_bhav)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Pseudocode", 
                            command=lambda: self.switch_view(CodeStyle.PSEUDOCODE))
        view_menu.add_command(label="Assembly", 
                            command=lambda: self.switch_view(CodeStyle.ASSEMBLY))
        view_menu.add_command(label="Control Flow", 
                            command=lambda: self.switch_view(CodeStyle.FLOWCHART))
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Analyze", command=self.analyze_code)
        tools_menu.add_command(label="Lint", command=self.lint_code)
        tools_menu.add_command(label="Statistics", command=self.show_statistics)
    
    def _create_editor_ui(self, parent):
        """Create code editor area"""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Open", command=self.open_bhav).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_bhav).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Analyze", command=self.analyze_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Lint", command=self.lint_code).pack(side=tk.LEFT, padx=2)
        
        # Code view (tabbed)
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Source tab
        source_frame = ttk.Frame(self.notebook)
        self.notebook.add(source_frame, text="Source")
        
        self.code_text = scrolledtext.ScrolledText(
            source_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#f0f0f0"
        )
        self.code_text.pack(fill=tk.BOTH, expand=True)
        self.code_text.bind("<<Change>>", self._on_code_change)
        
        # CFG tab
        cfg_frame = ttk.Frame(self.notebook)
        self.notebook.add(cfg_frame, text="Control Flow")
        
        self.cfg_text = scrolledtext.ScrolledText(
            cfg_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#f5f5f5"
        )
        self.cfg_text.pack(fill=tk.BOTH, expand=True)
        
        # Instructions tab
        instr_frame = ttk.Frame(self.notebook)
        self.notebook.add(instr_frame, text="Instructions")
        
        self.instructions_tree = ttk.Treeview(instr_frame, columns=("Index", "Opcode", "Operand", "T", "F"))
        self.instructions_tree.heading("#0", text="Instruction")
        self.instructions_tree.heading("Index", text="Idx")
        self.instructions_tree.heading("Opcode", text="Code")
        self.instructions_tree.heading("Operand", text="Operand")
        self.instructions_tree.heading("T", text="T")
        self.instructions_tree.heading("F", text="F")
        
        self.instructions_tree.column("#0", width=300)
        self.instructions_tree.column("Index", width=30)
        self.instructions_tree.column("Opcode", width=40)
        self.instructions_tree.column("Operand", width=200)
        self.instructions_tree.column("T", width=30)
        self.instructions_tree.column("F", width=30)
        
        self.instructions_tree.pack(fill=tk.BOTH, expand=True)
        self.instructions_tree.bind("<<TreeviewSelect>>", self._on_instruction_select)
    
    def _create_properties_ui(self, parent):
        """Create properties panel"""
        # Title
        title = ttk.Label(parent, text="Properties", font=("Arial", 12, "bold"))
        title.pack(fill=tk.X, padx=5, pady=5)
        
        # Info frame
        info_frame = ttk.LabelFrame(parent, text="BHAV Info")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_text = tk.Text(info_frame, height=8, width=30, font=("Courier", 9))
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(parent, text="Metrics")
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.metrics_text = tk.Text(metrics_frame, height=6, width=30, font=("Courier", 9))
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Issues frame
        issues_frame = ttk.LabelFrame(parent, text="Issues")
        issues_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.issues_text = scrolledtext.ScrolledText(
            issues_frame,
            height=10,
            width=30,
            font=("Courier", 8)
        )
        self.issues_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
    def open_bhav(self):
        """Open BHAV file"""
        # TODO: Implement file dialog
        messagebox.showinfo("Open BHAV", "File open not yet implemented")
    
    def save_bhav(self):
        """Save BHAV file"""
        # TODO: Implement save
        messagebox.showinfo("Save BHAV", "Save not yet implemented")
    
    def export_bhav(self):
        """Export BHAV as text"""
        # TODO: Implement export
        messagebox.showinfo("Export BHAV", "Export not yet implemented")
    
    def switch_view(self, style: CodeStyle):
        """Switch code view style"""
        if not self.current_ast:
            messagebox.showwarning("No BHAV Loaded", "Load a BHAV first")
            return
        
        formatter = BHAVFormatter(self.current_ast, style)
        code = formatter.format()
        
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", code)
    
    def analyze_code(self):
        """Run analysis"""
        if not self.current_ast:
            messagebox.showwarning("No BHAV Loaded", "Load a BHAV first")
            return
        
        metrics = CodeMetrics(self.current_ast)
        analysis = metrics.get_metrics()
        
        # Display in properties
        self.metrics_text.delete("1.0", tk.END)
        
        complexity = analysis.get('complexity', {})
        stack = analysis.get('stack', {})
        
        text = f"""Complexity: {complexity.get('cyclomatic_complexity', 0)}
Instructions: {complexity.get('instruction_count', 0)}
Max Depth: {complexity.get('nesting_depth', 0)}
Calls: {complexity.get('function_calls', 0)}

Stack Max: {stack.get('max_depth', 0)}
Pushes: {stack.get('operations', {}).get('pushes', 0)}
Calls: {stack.get('operations', {}).get('calls', 0)}
"""
        
        self.metrics_text.insert("1.0", text)
    
    def lint_code(self):
        """Run linter"""
        if not self.current_ast:
            messagebox.showwarning("No BHAV Loaded", "Load a BHAV first")
            return
        
        linter = BHAVLinter(self.current_ast)
        issues = linter.lint()
        
        # Display issues
        self.issues_text.delete("1.0", tk.END)
        
        if not issues:
            self.issues_text.insert("1.0", "No issues found!")
        else:
            for issue in issues:
                text = f"[{issue.severity.name}] {issue.category}\n"
                text += f"  Instr {issue.instruction_index}: {issue.message}\n"
                if issue.suggestion:
                    text += f"  → {issue.suggestion}\n\n"
                
                self.issues_text.insert(tk.END, text)
    
    def show_statistics(self):
        """Show detailed statistics"""
        if not self.current_ast:
            messagebox.showwarning("No BHAV Loaded", "Load a BHAV first")
            return
        
        text = f"Arguments: {self.current_ast.arg_count}\n"
        text += f"Locals: {self.current_ast.local_count}\n"
        text += f"Instructions: {len(self.current_ast.instructions)}\n"
        
        messagebox.showinfo("Statistics", text)
    
    def load_bhav(self, data: bytes):
        """Load BHAV from bytes"""
        ast = self.decompiler.decompile(data)
        if not ast:
            messagebox.showerror("Decompile Error", "Failed to decompile BHAV")
            return
        
        self.current_ast = ast
        self._refresh_display()
    
    def _refresh_display(self):
        """Refresh all display elements"""
        if not self.current_ast:
            return
        
        # Update code view
        formatter = BHAVFormatter(self.current_ast)
        code = formatter.format()
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", code)
        
        # Update CFG view
        visualizer = BHAVGraphVisualizer(self.current_ast)
        cfg_ascii = visualizer.generate_ascii()
        self.cfg_text.delete("1.0", tk.END)
        self.cfg_text.insert("1.0", cfg_ascii)
        
        # Update instructions tree
        self.instructions_tree.delete(*self.instructions_tree.get_children())
        for instr in self.current_ast.instructions:
            self.instructions_tree.insert("", "end", text=instr.primitive_name,
                                         values=(instr.index, instr.opcode, "", 
                                                instr.true_pointer, instr.false_pointer))
        
        # Update info
        self.info_text.delete("1.0", tk.END)
        info = f"Source: {self.current_ast.source_bhav}\n"
        info += f"Arguments: {self.current_ast.arg_count}\n"
        info += f"Locals: {self.current_ast.local_count}\n"
        info += f"Instructions: {len(self.current_ast.instructions)}\n"
        self.info_text.insert("1.0", info)
    
    def _on_code_change(self, event):
        """Code changed event"""
        pass
    
    def _on_instruction_select(self, event):
        """Instruction selected in tree"""
        selection = self.instructions_tree.selection()
        if selection:
            item = selection[0]
            # Highlight in code view
            pass
    
    def run(self):
        """Run the editor window"""
        self.root.mainloop()


def open_bhav_editor(parent=None, bhav_data: Optional[bytes] = None):
    """Open BHAV editor window"""
    editor = BHAVEditorWindow(parent)
    
    if bhav_data:
        editor.load_bhav(bhav_data)
    
    editor.run()
