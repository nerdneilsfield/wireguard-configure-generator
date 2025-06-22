"""
Test the network simulator module
"""

import pytest
import asyncio
import json
from pathlib import Path
from wg_mesh_gen.simulator import NetworkSimulator, run_simulation


class TestNetworkSimulator:
    """Test network simulation functionality"""
    
    @pytest.fixture
    def simple_nodes_file(self, tmp_path):
        """Create a simple nodes configuration"""
        nodes = {
            "nodes": [
                {
                    "name": "node1",
                    "wireguard_ip": "10.0.0.1/24",
                    "endpoints": ["192.168.1.1:51820"]
                },
                {
                    "name": "node2",
                    "wireguard_ip": "10.0.0.2/24",
                    "endpoints": ["192.168.1.2:51820"]
                },
                {
                    "name": "relay",
                    "wireguard_ip": "10.0.0.254/24",
                    "role": "relay",
                    "enable_ip_forward": True,
                    "endpoints": ["192.168.1.254:51820"]
                }
            ]
        }
        
        nodes_file = tmp_path / "nodes.json"
        with open(nodes_file, 'w') as f:
            json.dump(nodes, f)
        
        return str(nodes_file)
    
    @pytest.fixture
    def simple_topology_file(self, tmp_path):
        """Create a simple topology configuration"""
        topology = {
            "peers": [
                {
                    "from": "node1",
                    "to": "relay",
                    "allowed_ips": ["10.0.0.254/32", "10.0.0.2/32"]
                },
                {
                    "from": "node2",
                    "to": "relay",
                    "allowed_ips": ["10.0.0.254/32", "10.0.0.1/32"]
                },
                {
                    "from": "relay",
                    "to": "node1",
                    "allowed_ips": ["10.0.0.1/32"]
                },
                {
                    "from": "relay",
                    "to": "node2",
                    "allowed_ips": ["10.0.0.2/32"]
                }
            ]
        }
        
        topo_file = tmp_path / "topology.json"
        with open(topo_file, 'w') as f:
            json.dump(topology, f)
        
        return str(topo_file)
    
    @pytest.mark.asyncio
    async def test_basic_simulation(self, simple_nodes_file, simple_topology_file):
        """Test basic network simulation"""
        simulator = NetworkSimulator()
        
        results = await simulator.simulate_network(
            nodes_file=simple_nodes_file,
            topo_file=simple_topology_file,
            duration=1
        )
        
        assert 'initial_status' in results
        assert 'final_status' in results
        assert results['initial_status']['statistics']['total_nodes'] == 3
    
    @pytest.mark.asyncio
    async def test_connectivity_testing(self, simple_nodes_file, simple_topology_file):
        """Test connectivity testing feature"""
        simulator = NetworkSimulator()
        
        results = await simulator.simulate_network(
            nodes_file=simple_nodes_file,
            topo_file=simple_topology_file,
            test_connectivity=True,
            duration=1
        )
        
        assert 'connectivity_tests' in results
        assert len(results['connectivity_tests']) > 0
        
        # Check that some connections are reachable
        reachable = [r for r in results['connectivity_tests'] if r['reachable']]
        assert len(reachable) > 0
    
    @pytest.mark.asyncio
    async def test_route_testing(self, simple_nodes_file, simple_topology_file):
        """Test route testing feature"""
        simulator = NetworkSimulator()
        
        results = await simulator.simulate_network(
            nodes_file=simple_nodes_file,
            topo_file=simple_topology_file,
            test_routes=True,
            duration=1
        )
        
        assert 'routing_tests' in results
        # Should find the relay node
        assert len(results['routing_tests']) == 1
        assert results['routing_tests'][0]['relay'] == 'relay'
    
    @pytest.mark.asyncio
    async def test_failure_simulation(self, simple_nodes_file, simple_topology_file):
        """Test node failure simulation"""
        simulator = NetworkSimulator()
        
        results = await simulator.simulate_network(
            nodes_file=simple_nodes_file,
            topo_file=simple_topology_file,
            failure_node='relay',
            duration=1
        )
        
        assert 'failure_tests' in results
        failure_test = results['failure_tests']
        assert failure_test['failed_node'] == 'relay'
        
        # Connections should drop when relay fails
        assert failure_test['during_failure']['connected_pairs'] < failure_test['before_failure']['connected_pairs']
        
        # Connections should start to recover (may not fully recover in short time)
        assert failure_test['after_recovery']['connected_pairs'] >= failure_test['during_failure']['connected_pairs']
    
    def test_sync_wrapper(self, simple_nodes_file, simple_topology_file):
        """Test synchronous wrapper function"""
        results = run_simulation(
            nodes_file=simple_nodes_file,
            topo_file=simple_topology_file,
            duration=1
        )
        
        assert 'initial_status' in results
        assert 'final_status' in results
    
    def test_missing_files(self):
        """Test handling of missing files"""
        with pytest.raises(FileNotFoundError):
            run_simulation(
                nodes_file='/nonexistent/nodes.json',
                topo_file='/nonexistent/topo.json'
            )
    
    def test_invalid_arguments(self):
        """Test handling of invalid arguments"""
        with pytest.raises(ValueError):
            run_simulation()  # No files provided