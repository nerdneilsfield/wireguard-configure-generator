#!/usr/bin/env python3
"""
Test script for GUI proof of concept
"""
import sys
from pathlib import Path

# Add the GUI module to path
sys.path.append(str(Path(__file__).parent.parent / 'wg_mesh_gen' / 'gui'))

try:
    from nicegui import ui
    print("✓ NiceGUI imported successfully")
except ImportError as e:
    print(f"✗ Failed to import NiceGUI: {e}")
    print("Please install with: pip install nicegui")
    sys.exit(1)

try:
    from cytoscape_widget import CytoscapeWidget
    print("✓ CytoscapeWidget imported successfully")
except ImportError as e:
    print(f"✗ Failed to import CytoscapeWidget: {e}")
    sys.exit(1)

# Test basic functionality
def test_basic():
    """Test basic widget creation"""
    print("\nTesting basic functionality...")
    
    # Create widget
    widget = CytoscapeWidget()
    print("✓ Widget created")
    
    # Add a node
    widget.add_node('test1', 'Test Node 1', '10.0.0.1/24')
    print("✓ Node added")
    
    # Add another node
    widget.add_node('test2', 'Test Node 2', '10.0.0.2/24', role='relay')
    print("✓ Relay node added")
    
    # Add edge
    widget.add_edge('edge1', 'test1', 'test2', edge_type='peer')
    print("✓ Edge added")
    
    # Check elements
    elements = widget.get_elements()
    assert len(elements['nodes']) == 2, "Expected 2 nodes"
    assert len(elements['edges']) == 1, "Expected 1 edge"
    print("✓ Elements verified")
    
    print("\nAll basic tests passed!")
    
# Run POC if requested
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        print("\nStarting POC application...")
        from poc_app import main
        main()
    else:
        test_basic()
        print("\nTo run the POC app, use: python test_gui_poc.py run")