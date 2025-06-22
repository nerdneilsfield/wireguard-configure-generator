# GUI Test Specifications

This document outlines comprehensive test specifications for the WireGuard Visual Configuration Editor GUI module. These specifications follow TDD principles and define what needs to be tested before implementation.

## Test Categories

### 1. Unit Tests

#### 1.1 Model Tests

**NodeModel Tests:**
- Validate all required properties are present and correctly typed
- Test IP address validation (IPv4 and IPv6)
- Test endpoint management (add, remove, get)
- Test role validation (client vs relay)
- Test IP forwarding logic (must be true for relay nodes)
- Test group assignment and removal
- Test position validation (x, y coordinates)
- Test serialization/deserialization
- Test cloning creates independent copy
- Test metadata storage

**EdgeModel Tests:**
- Validate source and target node IDs
- Test edge type validation (peer, mesh, star, relay)
- Test allowed IPs validation and management
- Test bidirectional edge detection
- Test persistent keepalive validation (positive integers or None)
- Test endpoint name assignment
- Test serialization with all properties
- Test edge direction determination

**GroupModel Tests:**
- Test topology validation (mesh, star, chain, single)
- Test node membership operations (add, remove, check)
- Test topology-specific node count validation:
  - Single: exactly 1 node
  - Mesh: at least 2 nodes
  - Star: at least 3 nodes
  - Chain: at least 2 nodes
- Test color validation (hex format)
- Test mesh endpoint configuration
- Test duplicate node prevention

#### 1.2 State Management Tests

**Command Tests:**
- Test command execution changes state
- Test undo restores previous state
- Test can_execute prevents invalid operations
- Test can_undo is false after execution
- Test command description is meaningful
- Test state preservation for undo

**HistoryManager Tests:**
- Test command execution adds to history
- Test undo/redo functionality
- Test history limit enforcement
- Test batch operations group commands
- Test redo stack cleared after new command
- Test descriptions for undo/redo operations

**AppState Tests:**
- Test CRUD operations for nodes, edges, groups
- Test selection management
- Test dirty state tracking
- Test event emission on state changes
- Test cascade deletion (removing node removes edges)
- Test group removal unassigns nodes
- Test state consistency after operations

#### 1.3 Business Logic Tests

**GraphManager Tests:**
- Test node creation with validation
- Test edge creation with endpoint validation
- Test group creation and topology application
- Test automatic layout algorithms
- Test path finding between nodes
- Test subnet conflict detection
- Test IP address suggestion
- Test topology validation

**ConfigManager Tests:**
- Test loading/saving configurations
- Test importing nodes and topology files
- Test exporting to different formats
- Test WireGuard config generation
- Test group configuration import/export
- Test backward compatibility
- Test validation during import

**ValidationManager Tests:**
- Test IP address validation (with/without subnet)
- Test endpoint validation (host:port format)
- Test allowed IPs validation
- Test node name validation (uniqueness, format)
- Test group topology validation
- Test subnet overlap detection
- Test comprehensive error messages

#### 1.4 Component Tests

**CytoscapeWidget Tests:**
- Test node/edge CRUD operations
- Test layout algorithm application
- Test element styling
- Test highlighting functionality
- Test image export
- Test event handler registration
- Test viewport operations (fit, zoom, pan)

**PropertyPanel Tests:**
- Test loading properties for different element types
- Test field validation
- Test save operation returns correct data
- Test reset functionality
- Test property change notifications
- Test dynamic field generation

**NodeTree Tests:**
- Test tree structure operations
- Test drag and drop functionality
- Test selection synchronization
- Test expand/collapse state
- Test icon display for different node types
- Test search/filter functionality

### 2. Integration Tests

#### 2.1 Component Integration

**Graph-Property Panel Integration:**
- Selecting node in graph loads properties
- Changing properties updates graph
- Validation errors prevent updates
- Multi-selection handling

**Tree-Graph Synchronization:**
- Tree selection updates graph
- Graph selection updates tree
- Drag and drop updates both views
- Group operations reflected in both

**State-Component Integration:**
- State changes update all components
- Component actions trigger state changes
- Undo/redo updates all views
- Event propagation works correctly

#### 2.2 Manager Integration

**GraphManager-ValidationManager:**
- Node creation validates IP addresses
- Edge creation validates allowed IPs
- Topology application respects validation rules
- Error messages are user-friendly

**ConfigManager-State Integration:**
- Loading configuration populates state
- Saving configuration preserves all data
- Import operations validate before applying
- Export includes all necessary data

### 3. End-to-End Tests

#### 3.1 User Workflows

**Create Network from Scratch:**
1. Add multiple nodes
2. Configure node properties
3. Create connections
4. Apply group topology
5. Validate configuration
6. Generate WireGuard configs

**Import and Modify:**
1. Import existing configuration
2. Add new nodes
3. Modify connections
4. Change group assignments
5. Export updated configuration

**Group Management:**
1. Create groups
2. Assign nodes to groups
3. Apply group topology
4. Modify group properties
5. Remove groups

#### 3.2 Error Scenarios

**Validation Failures:**
- Invalid IP addresses
- Subnet conflicts
- Missing required fields
- Invalid topology for node count
- Circular dependencies

**Recovery Operations:**
- Undo after errors
- Reset to last valid state
- Clear and start over
- Partial import handling

### 4. Performance Tests

**Large Network Handling:**
- 100+ nodes rendering
- 500+ edges rendering
- Layout algorithm performance
- Selection performance
- Serialization performance

**Memory Management:**
- No memory leaks in long sessions
- Proper cleanup on component destroy
- Event handler cleanup
- Command history limits

### 5. Accessibility Tests

**Keyboard Navigation:**
- Tab order is logical
- All functions keyboard accessible
- Shortcuts work correctly
- Focus indicators visible

**Screen Reader Support:**
- Proper ARIA labels
- Status announcements
- Error announcements
- Selection announcements

## Test Data Requirements

### Sample Configurations
- Small network (5 nodes)
- Medium network (20 nodes)
- Large network (100+ nodes)
- Complex topology (multiple groups)
- Edge cases (single nodes, disconnected graphs)

### Invalid Data Sets
- Malformed IP addresses
- Invalid JSON/YAML
- Circular group assignments
- Conflicting subnets
- Missing required fields

## Mock Requirements

### External Dependencies
- File system operations
- WireGuard command execution
- Network operations
- Async operations

### UI Framework Mocks
- NiceGUI components
- Cytoscape.js operations
- Event system
- Browser APIs

## Test Execution Strategy

### Test Order
1. Unit tests (models, then managers, then components)
2. Integration tests (component pairs, then full integration)
3. End-to-end tests (happy path, then error scenarios)
4. Performance tests (after functional tests pass)

### Continuous Integration
- Run unit tests on every commit
- Run integration tests on PR
- Run E2E tests before release
- Performance benchmarks tracked

## Success Criteria

- 100% interface coverage
- 90%+ implementation coverage
- All user workflows tested
- All error scenarios handled
- Performance within targets
- No memory leaks
- Accessibility compliance