#!/usr/bin/env python3
"""
WireGuard 路由优化器
自动测量网络延迟并选择最优路径
"""

import subprocess
import time
import json
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RouteMetric:
    """路由度量信息"""
    target: str
    via: str
    rtt_avg: float
    rtt_std: float
    packet_loss: float
    bandwidth: Optional[float] = None


class RouteOptimizer:
    """路由优化器"""
    
    def __init__(self, interface: str = "wg0"):
        self.interface = interface
        self.ping_count = 5
        self.ping_timeout = 3
    
    def ping_test(self, target_ip: str, count: int = None) -> Tuple[float, float, float]:
        """
        执行 ping 测试
        返回: (平均RTT, RTT标准差, 丢包率)
        """
        count = count or self.ping_count
        
        try:
            # Windows ping 命令
            cmd = ["ping", "-n", str(count), "-w", str(self.ping_timeout * 1000), target_ip]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return float('inf'), float('inf'), 100.0
            
            output = result.stdout
            
            # 解析 ping 结果
            rtts = []
            lines = output.split('\n')
            
            for line in lines:
                if 'time=' in line or 'time<' in line:
                    # 提取 RTT 值
                    if 'time=' in line:
                        rtt_str = line.split('time=')[1].split('ms')[0]
                    else:  # time<1ms
                        rtt_str = "0.5"  # 假设小于1ms的为0.5ms
                    
                    try:
                        rtts.append(float(rtt_str))
                    except ValueError:
                        continue
            
            if not rtts:
                return float('inf'), float('inf'), 100.0
            
            # 计算统计信息
            avg_rtt = statistics.mean(rtts)
            std_rtt = statistics.stdev(rtts) if len(rtts) > 1 else 0.0
            loss_rate = max(0, (count - len(rtts)) / count * 100)
            
            return avg_rtt, std_rtt, loss_rate
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return float('inf'), float('inf'), 100.0
    
    def measure_routes(self, routes: Dict[str, List[str]]) -> Dict[str, List[RouteMetric]]:
        """
        测量多条路由的性能
        routes: {"target": ["via1", "via2", ...]}
        """
        results = {}
        
        for target, vias in routes.items():
            target_results = []
            
            for via in vias:
                print(f"Testing route to {target} via {via}...")
                
                # 这里需要根据实际情况调整IP地址映射
                via_ip = self._get_node_ip(via)
                if not via_ip:
                    continue
                
                avg_rtt, std_rtt, loss = self.ping_test(via_ip)
                
                metric = RouteMetric(
                    target=target,
                    via=via,
                    rtt_avg=avg_rtt,
                    rtt_std=std_rtt,
                    packet_loss=loss
                )
                
                target_results.append(metric)
                print(f"  RTT: {avg_rtt:.2f}±{std_rtt:.2f}ms, Loss: {loss:.1f}%")
            
            # 按性能排序（RTT越小越好，丢包率越小越好）
            target_results.sort(key=lambda x: (x.packet_loss, x.rtt_avg))
            results[target] = target_results
        
        return results
    
    def _get_node_ip(self, node_name: str) -> Optional[str]:
        """获取节点的IP地址"""
        # 这里应该从配置文件中读取节点IP映射
        # 暂时硬编码一些示例
        ip_map = {
            'D': '10.96.0.1',
            'H': '10.96.0.2',
            'A': '10.96.1.2',
            'B': '10.96.1.3',
            'C': '10.96.1.4',
            'E': '10.96.2.2',
            'F': '10.96.2.3'
        }
        return ip_map.get(node_name)
    
    def generate_optimized_routes(self, metrics: Dict[str, List[RouteMetric]]) -> Dict[str, str]:
        """
        基于测量结果生成优化的路由表
        """
        optimized = {}
        
        for target, route_list in metrics.items():
            if route_list:
                # 选择最优路由（丢包率最低，RTT最小）
                best_route = route_list[0]
                if best_route.packet_loss < 50:  # 只有丢包率小于50%才认为可用
                    optimized[target] = best_route.via
                    print(f"Best route to {target}: via {best_route.via} "
                          f"(RTT: {best_route.rtt_avg:.2f}ms, Loss: {best_route.packet_loss:.1f}%)")
        
        return optimized
    
    def update_wireguard_routes(self, optimized_routes: Dict[str, str]):
        """
        更新 WireGuard 路由配置
        这里只是示例，实际实现需要根据具体需求调整
        """
        print("\nOptimized routing recommendations:")
        for target, via in optimized_routes.items():
            print(f"  Route to {target} should use {via}")
        
        # 实际实现可能需要：
        # 1. 修改 WireGuard 配置文件
        # 2. 重新加载配置
        # 3. 更新系统路由表


def main():
    """主函数示例"""
    optimizer = RouteOptimizer()
    
    # 定义要测试的路由
    test_routes = {
        'E': ['D', 'H'],  # A到E可以通过D或H
        'F': ['D', 'H'],  # A到F可以通过D或H
    }
    
    print("Starting route optimization...")
    
    # 测量路由性能
    metrics = optimizer.measure_routes(test_routes)
    
    # 生成优化建议
    optimized = optimizer.generate_optimized_routes(metrics)
    
    # 应用优化（这里只是打印建议）
    optimizer.update_wireguard_routes(optimized)


if __name__ == "__main__":
    main()
