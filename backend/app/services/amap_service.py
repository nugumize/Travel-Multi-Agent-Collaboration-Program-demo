"""高德地图MCP服务封装"""

import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from hello_agents.tools import MCPTool
from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

# 全局MCP工具实例
_amap_mcp_tool = None

# 全局缓存和限流器
_amap_cache: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], Dict[str, Any]] = {}
cache_lock = threading.Lock()

class AmapRateLimiter:
    """简单令牌桶限流器，用于限制对高德 MCP 的调用频率。"""

    def __init__(self, rate: float = 2.0, capacity: int = 3):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                refill = elapsed * self.rate
                if refill > 0:
                    self.tokens = min(self.capacity, self.tokens + refill)
                    self.last_refill = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

_amap_rate_limiter = AmapRateLimiter(rate=2.0, capacity=3)


def get_amap_mcp_tool() -> MCPTool:
    """
    获取高德地图MCP工具实例(单例模式)
    
    Returns:
        MCPTool实例
    """
    global _amap_mcp_tool
    
    if _amap_mcp_tool is None:
        settings = get_settings()
        
        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")
        
        # 创建MCP工具
        _amap_mcp_tool = MCPTool(
            name="amap",
            description="高德地图服务,支持POI搜索、路线规划、天气查询等功能",
            server_command=["uvx", "amap-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            auto_expand=True  # 自动展开为独立工具
        )
        
        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_mcp_tool._available_tools)}")
        
        # 打印可用工具列表
        if _amap_mcp_tool._available_tools:
            print("   可用工具:")
            for tool in _amap_mcp_tool._available_tools[:5]:  # 只打印前5个
                print(f"     - {tool.get('name', 'unknown')}")
            if len(_amap_mcp_tool._available_tools) > 5:
                print(f"     ... 还有 {len(_amap_mcp_tool._available_tools) - 5} 个工具")
    
    return _amap_mcp_tool


class AmapService:
    """高德地图服务封装类"""
    
    def __init__(self):
        """初始化服务"""
        self.mcp_tool = get_amap_mcp_tool()
    
    def _build_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
        sorted_items = tuple(sorted(arguments.items()))
        return tool_name, sorted_items

    def _get_cached_result(self, key: Tuple[str, Tuple[Tuple[str, Any], ...]]) -> Optional[str]:
        with cache_lock:
            entry = _amap_cache.get(key)
            if not entry:
                return None
            if time.monotonic() - entry["ts"] > entry["ttl"]:
                del _amap_cache[key]
                return None
            return entry["result"]

    def _set_cached_result(self, key: Tuple[str, Tuple[Tuple[str, Any], ...]], result: str, ttl: float):
        with cache_lock:
            _amap_cache[key] = {"result": result, "ts": time.monotonic(), "ttl": ttl}

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(term in msg for term in ["429", "quota_exceeded", "rpm exhausted", "quota exceeded"])

    def _call_tool_with_retry(self, tool_name: str, arguments: Dict[str, Any], cache_ttl: float = 30.0) -> str:
        key = self._build_cache_key(tool_name, arguments)
        cached = self._get_cached_result(key)
        if cached is not None:
            print(f"🔁 缓存命中: {tool_name} {arguments}")
            return cached

        for attempt in range(1, 4):
            if not _amap_rate_limiter.acquire(timeout=5.0):
                raise RuntimeError("高德请求限流超时，请稍后重试")

            try:
                result = self.mcp_tool.run({
                    "action": "call_tool",
                    "tool_name": tool_name,
                    "arguments": arguments
                })
                self._set_cached_result(key, result, cache_ttl)
                return result
            except Exception as e:
                if self._is_rate_limit_error(e) and attempt < 3:
                    wait = 0.5 * attempt
                    print(f"⚠️  触发限流({tool_name})，第{attempt}次重试，等待{wait}s... {e}")
                    time.sleep(wait)
                    continue
                print(f"❌ 调用高德MCP工具失败: {tool_name} {arguments} -> {e}")
                raise

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI
        
        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内
            
        Returns:
            POI信息列表
        """
        try:
            result = self._call_tool_with_retry(
                tool_name="maps_text_search",
                arguments={
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower()
                },
                cache_ttl=30.0
            )
            print(f"POI搜索结果: {result[:200]}...")
            return []
        except Exception as e:
            print(f"❌ POI搜索失败: {e}")
            return []
    
    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气
        
        Args:
            city: 城市名称
            
        Returns:
            天气信息列表
        """
        try:
            result = self._call_tool_with_retry(
                tool_name="maps_weather",
                arguments={"city": city},
                cache_ttl=60.0
            )
            print(f"天气查询结果: {result[:200]}...")
            return []
        except Exception as e:
            print(f"❌ 天气查询失败: {e}")
            return []
    
    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线
        
        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)
            
        Returns:
            路线信息
        """
        try:
            tool_map = {
                "walking": "maps_direction_walking_by_address",
                "driving": "maps_direction_driving_by_address",
                "transit": "maps_direction_transit_integrated_by_address"
            }
            tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")

            arguments = {
                "origin_address": origin_address,
                "destination_address": destination_address
            }
            if origin_city:
                arguments["origin_city"] = origin_city
            if destination_city:
                arguments["destination_city"] = destination_city

            result = self._call_tool_with_retry(
                tool_name=tool_name,
                arguments=arguments,
                cache_ttl=10.0
            )
            print(f"路线规划结果: {result[:200]}...")
            return {}
        except Exception as e:
            print(f"❌ 路线规划失败: {e}")
            return {}
    
    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        try:
            arguments = {"address": address}
            if city:
                arguments["city"] = city

            result = self._call_tool_with_retry(
                tool_name="maps_geo",
                arguments=arguments,
                cache_ttl=60.0
            )
            print(f"地理编码结果: {result[:200]}...")
            return None
        except Exception as e:
            print(f"❌ 地理编码失败: {e}")
            return None

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            result = self._call_tool_with_retry(
                tool_name="maps_search_detail",
                arguments={"id": poi_id},
                cache_ttl=60.0
            )
            print(f"POI详情结果: {result[:200]}...")

            import json
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data

            return {"raw": result}
        except Exception as e:
            print(f"❌ 获取POI详情失败: {e}")
            return {}


# 创建全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service
    
    if _amap_service is None:
        _amap_service = AmapService()
    
    return _amap_service

