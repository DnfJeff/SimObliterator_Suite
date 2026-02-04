"""
BHAV Control Flow Graph Analyzer and Visualizer

Analyzes control flow patterns and generates visualizations for debugging.
Identifies loops, branches, unreachable code, and complex flow patterns.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .bhav_ast import BehaviorAST, BasicBlock, Instruction


class BlockType(Enum):
    """Classification of basic blocks"""
    ENTRY = 0
    EXIT = 1
    LINEAR = 2
    BRANCH = 3
    MERGE = 4
    LOOP_HEAD = 5
    LOOP_BODY = 6


@dataclass
class FlowEdge:
    """Edge in control flow graph"""
    from_instr: Instruction
    to_block: BasicBlock
    edge_type: str = "unconditional"  # "conditional_true", "conditional_false"


class BHAVGraphAnalyzer:
    """Analyze BHAV control flow graph"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
        self.blocks = ast.cfg.blocks if ast.cfg else []
        self.edges = ast.cfg.edges if ast.cfg else []
        self.dominators = {}
        self.loops = []
        self.block_types = {}
    
    def analyze(self) -> Dict[str, any]:
        """Perform full CFG analysis"""
        if not self.ast.cfg:
            return {}
        
        stats = {
            'total_blocks': len(self.blocks),
            'total_instructions': len(self.ast.instructions),
            'branches': self._count_branches(),
            'loops': self._find_loops(),
            'dead_code': self._find_dead_code(),
            'branch_complexity': self._calculate_cyclomatic_complexity(),
            'block_types': self._classify_blocks()
        }
        
        return stats
    
    def _count_branches(self) -> int:
        """Count conditional branches"""
        count = 0
        for instr in self.ast.instructions:
            if instr.is_conditional():
                count += 1
        return count
    
    def _find_loops(self) -> List[Dict]:
        """Detect loop structures"""
        loops = []
        
        if not self.blocks:
            return loops
        
        # Simple loop detection: find back edges (edges that go to earlier blocks)
        block_indices = {block: i for i, block in enumerate(self.blocks)}
        
        for edge in self.edges:
            from_instr, to_block = edge
            
            # Find from block
            from_block = None
            for block in self.blocks:
                if from_instr in block.instructions:
                    from_block = block
                    break
            
            if from_block and to_block:
                from_idx = block_indices.get(from_block, -1)
                to_idx = block_indices.get(to_block, -1)
                
                if from_idx > to_idx and to_idx >= 0:
                    # Back edge detected = loop
                    loops.append({
                        'head': to_block.label,
                        'from': from_instr.index,
                        'type': 'while_loop' if from_instr.is_conditional() else 'do_while'
                    })
        
        return loops
    
    def _find_dead_code(self) -> List[int]:
        """Find unreachable instructions"""
        if not self.ast.cfg:
            return []
        
        reachable = set()
        stack = [self.ast.cfg.entry]
        visited_blocks = set()
        
        while stack:
            block = stack.pop()
            if block in visited_blocks:
                continue
            
            visited_blocks.add(block)
            
            for instr in block.instructions:
                reachable.add(instr.index)
            
            # Follow edges
            for edge in self.edges:
                from_instr, to_block = edge
                if any(instr in block.instructions for instr in [from_instr]):
                    if to_block not in visited_blocks:
                        stack.append(to_block)
        
        dead = []
        for i in range(len(self.ast.instructions)):
            if i not in reachable:
                dead.append(i)
        
        return dead
    
    def _calculate_cyclomatic_complexity(self) -> int:
        """Calculate cyclomatic complexity (M = E - N + 2)"""
        if not self.blocks or not self.edges:
            return 1
        
        # M = E - N + 2P, where:
        # E = number of edges
        # N = number of nodes
        # P = number of connected components (usually 1)
        
        E = len(self.edges)
        N = len(self.blocks)
        P = 1
        
        if N == 0:
            return 1
        
        return max(1, E - N + 2 * P)
    
    def _classify_blocks(self) -> Dict[str, List[str]]:
        """Classify blocks by type"""
        classification = {
            'ENTRY': [],
            'EXIT': [],
            'LINEAR': [],
            'BRANCH': [],
            'MERGE': []
        }
        
        if not self.blocks:
            return classification
        
        # Entry block
        if self.blocks:
            classification['ENTRY'].append(str(self.blocks[0].label))
        
        # Find exit blocks (have no outgoing edges or return)
        outgoing = set()
        for edge in self.edges:
            from_instr = edge[0]
            for block in self.blocks:
                if from_instr in block.instructions:
                    outgoing.add(block)
        
        for block in self.blocks:
            if block not in outgoing:
                classification['EXIT'].append(str(block.label))
        
        # Classify remaining blocks
        for block in self.blocks[1:]:  # Skip entry
            if str(block.label) in classification['EXIT']:
                continue
            
            # Check if block has branches
            has_conditional = any(instr.is_conditional() for instr in block.instructions)
            
            if has_conditional:
                classification['BRANCH'].append(str(block.label))
            else:
                classification['LINEAR'].append(str(block.label))
        
        return classification


class BHAVGraphVisualizer:
    """Generate visualizations of BHAV control flow"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
        self.analyzer = BHAVGraphAnalyzer(ast)
    
    def generate_mermaid(self) -> str:
        """Generate Mermaid diagram code"""
        if not self.ast.cfg:
            return "No CFG available"
        
        lines = ["graph TD"]
        
        # Add nodes
        for block in self.ast.cfg.blocks:
            label = self._format_block_label(block)
            lines.append(f'    {block.label}["{label}"]')
        
        # Add edges
        for from_instr, to_block in self.ast.cfg.edges:
            from_block_label = None
            edge_label = ""
            
            for block in self.ast.cfg.blocks:
                if from_instr in block.instructions:
                    from_block_label = block.label
                    break
            
            if from_block_label:
                if from_instr.is_conditional():
                    edge_label = "T" if from_instr.true_pointer == to_block.instructions[0].index else "F"
                
                if edge_label:
                    lines.append(f'    {from_block_label} -->|{edge_label}| {to_block.label}')
                else:
                    lines.append(f'    {from_block_label} --> {to_block.label}')
        
        return "\n".join(lines)
    
    def generate_ascii(self) -> str:
        """Generate ASCII art visualization"""
        if not self.ast.cfg:
            return "No CFG available"
        
        lines = []
        lines.append("=" * 60)
        lines.append("BHAV Control Flow Graph")
        lines.append("=" * 60)
        
        for i, block in enumerate(self.ast.cfg.blocks):
            lines.append("")
            lines.append(f"[Block {i}: {block.label}]")
            
            for instr in block.instructions:
                lines.append(f"  {instr.index:3d}: {instr.primitive_name}")
            
            # Find outgoing edges
            outgoing = []
            for edge in self.ast.cfg.edges:
                if any(instr in block.instructions for instr in [edge[0]]):
                    outgoing.append(edge)
            
            if outgoing:
                for from_instr, to_block in outgoing:
                    to_idx = self.ast.cfg.blocks.index(to_block)
                    
                    if from_instr.is_conditional():
                        branch_type = "true" if from_instr.true_pointer == to_block.instructions[0].index else "false"
                        lines.append(f"  → [Block {to_idx}] ({branch_type} branch)")
                    else:
                        lines.append(f"  → [Block {to_idx}] (unconditional)")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _format_block_label(self, block: BasicBlock) -> str:
        """Format block label for display"""
        instr_count = len(block.instructions)
        first_instr = block.instructions[0].primitive_name if block.instructions else "?"
        
        return f"Block {block.label}\\n({instr_count} instrs)\\n{first_instr}..."
    
    def generate_dot(self) -> str:
        """Generate Graphviz DOT format"""
        if not self.ast.cfg:
            return "// No CFG available"
        
        lines = ["digraph BHAV {"]
        lines.append('    rankdir="TB";')
        
        # Add nodes
        for block in self.ast.cfg.blocks:
            label = f"Block {block.label}\\n"
            for instr in block.instructions[:3]:  # Show first 3 instructions
                label += f"{instr.index}: {instr.primitive_name}\\n"
            if len(block.instructions) > 3:
                label += "..."
            
            lines.append(f'    "{block.label}" [label="{label}"];')
        
        # Add edges
        edge_count = 0
        for from_instr, to_block in self.ast.cfg.edges:
            from_block = None
            
            for block in self.ast.cfg.blocks:
                if from_instr in block.instructions:
                    from_block = block
                    break
            
            if from_block:
                edge_label = ""
                if from_instr.is_conditional():
                    edge_label = " [label=\"T\"]" if from_instr.true_pointer == to_block.instructions[0].index else " [label=\"F\"]"
                
                lines.append(f'    "{from_block.label}" -> "{to_block.label}"{edge_label};')
                edge_count += 1
        
        lines.append("}")
        
        return "\n".join(lines)


def analyze_bhav_flow(ast: BehaviorAST) -> Dict[str, any]:
    """Quick analysis function"""
    analyzer = BHAVGraphAnalyzer(ast)
    return analyzer.analyze()


def visualize_bhav_ascii(ast: BehaviorAST) -> str:
    """Quick ASCII visualization function"""
    visualizer = BHAVGraphVisualizer(ast)
    return visualizer.generate_ascii()
