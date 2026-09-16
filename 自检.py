"""
STEP4 · 自检脚本
================
对应操作手册 第一部分 STEP4

【这个脚本做什么】
不需要任何密钥, 不调用 LLM, 只检查后端【装配】是否正确:
  - 依赖装齐了没
  - 模块导入通不通
  - 路由注册上没有
  - 请求模型的字段对不对

【用法】
本脚本按【自己所在的位置】去找 backend/app, 和你在哪个目录运行无关。
激活虚拟环境之后, 下面这些写法都可以:

    智能旅行助手-教学包>         python .\自检.py
    智能旅行助手-教学包\backend> python ..\自检.py

【注意】自检不需要任何密钥, 也不调用 LLM。
它【只检查装配】, 不代表 python run.py 一定能起来 ——
启动时还会校验 AMAP_API_KEY, 那一步在这里是被跳过的。

【通过之后】
再配 .env 跑 python run.py, 去 /docs 发真实请求。
"""

import os
import sys

# 允许从 backend/ 或其上级目录运行
这里 = os.path.dirname(os.path.abspath(__file__))
for 候选 in (这里, os.path.join(这里, "backend")):
    if os.path.isdir(os.path.join(候选, "app")):
        sys.path.insert(0, 候选)
        break

# 自检阶段不需要真实密钥, 给个占位免得 config 报错
os.environ.setdefault("AMAP_API_KEY", "selfcheck-placeholder")

import warnings
warnings.filterwarnings("ignore")

通过 = 0
失败 = 0


def 检查(说明, 函数):
    global 通过, 失败
    try:
        结果 = 函数()
        print(f"  ✅ {说明}" + (f"  ({结果})" if 结果 else ""))
        通过 += 1
    except Exception as e:
        print(f"  ❌ {说明}")
        print(f"     {type(e).__name__}: {e}")
        失败 += 1


print("=" * 60)
print("STEP4 自检 · 后端装配检查")
print("=" * 60)

# ---------- 1. 依赖 ----------
print("\n[1/4] 依赖检查")

def _fastapi():
    import fastapi
    return f"fastapi {fastapi.__version__}"

def _pydantic():
    import pydantic
    if not pydantic.VERSION.startswith("2"):
        raise RuntimeError(f"需要 Pydantic 2.x, 当前 {pydantic.VERSION}")
    return f"pydantic {pydantic.VERSION}"

def _hello_agents():
    import importlib.metadata as md
    from hello_agents import SimpleAgent, HelloAgentsLLM
    from hello_agents.tools import MCPTool
    return f"hello-agents {md.version('hello-agents')}"

def _uvicorn():
    import uvicorn
    return f"uvicorn {uvicorn.__version__}"

检查("fastapi", _fastapi)
检查("pydantic 2.x", _pydantic)
检查("hello-agents + MCPTool", _hello_agents)
检查("uvicorn", _uvicorn)

# ---------- 2. 模块导入 ----------
print("\n[2/4] 模块导入")

def _schemas():
    from app.models.schemas import TripRequest, TripPlan, TripPlanResponse
    return "schemas"

def _config():
    from app.config import get_settings
    return f"port={get_settings().port}"

def _agent():
    from app.agents.trip_planner_agent import MultiAgentTripPlanner, get_trip_planner_agent
    return "trip_planner_agent"

def _app():
    from app.api.main import app
    return "FastAPI app"

检查("app.models.schemas", _schemas)
检查("app.config", _config)
检查("app.agents.trip_planner_agent", _agent)
检查("app.api.main", _app)

# ---------- 3. 路由 ----------
print("\n[3/4] 路由注册")

def _核心路由():
    from app.api.main import app
    paths = app.openapi()["paths"]
    if "/api/trip/plan" not in paths:
        raise RuntimeError(f"缺少 /api/trip/plan, 现有: {sorted(paths)}")
    if "post" not in paths["/api/trip/plan"]:
        raise RuntimeError("/api/trip/plan 不支持 POST")
    return "POST /api/trip/plan"

def _全部路由():
    from app.api.main import app
    paths = app.openapi()["paths"]
    print("     已注册的端点:")
    for p in sorted(paths):
        ms = ",".join(sorted(m.upper() for m in paths[p]))
        print(f"       {ms.ljust(8)} {p}")
    return f"共 {len(paths)} 个"

检查("核心端点存在", _核心路由)
检查("端点清单", _全部路由)

# ---------- 4. 请求模型字段 ----------
print("\n[4/4] 请求模型字段（对照课本文档的差异）")

def _字段():
    from app.models.schemas import TripRequest
    实际 = set(TripRequest.model_fields)
    应有 = {"city", "start_date", "end_date", "travel_days",
            "transportation", "accommodation", "preferences", "free_text_input"}
    缺 = 应有 - 实际
    if 缺:
        raise RuntimeError(f"缺少字段: {缺}")
    return f"{len(实际)} 个字段"

def _文档差异():
    from app.models.schemas import TripRequest
    f = TripRequest.model_fields
    print("     文档写的        实际代码")
    print(f"       days      ->  travel_days     {'✅' if 'travel_days' in f else '❌'}")
    print(f"       budget    ->  (无此字段)       {'✅' if 'budget' not in f else '⚠️ 已被添加'}")
    print(f"       (未提)     ->  free_text_input {'✅' if 'free_text_input' in f else '❌'}")
    anno = str(f["preferences"].annotation) if "preferences" in f else ""
    print(f"       str       ->  List[str]       {'✅' if 'list' in anno.lower() else '❌'}")
    return None

检查("TripRequest 字段齐全", _字段)
检查("与文档的差异", _文档差异)

# ---------- 结果 ----------
print("\n" + "=" * 60)
if 失败 == 0:
    print(f"✅ 全部通过 ({通过}/{通过})")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 复制 .env.example 为 .env, 填入三个密钥")
    print("  2. python run.py")
    print("  3. 打开 http://localhost:8200/docs")
    print("  4. 找到 POST /api/trip/plan, 点 Try it out")
else:
    print(f"❌ {失败} 项失败 / {通过 + 失败} 项")
    print("=" * 60)
    print("\n常见原因:")
    print("  ModuleNotFoundError: hello_agents")
    print("      pip install -r requirements.txt")
    print("  ModuleNotFoundError: huggingface_hub")
    print("      pip install huggingface_hub")
    print("      (单独装 hello-agents 不会带上它, 但 import 时需要)")
    print("  找不到 app 包")
    print("      本脚本按自身位置定位 backend/app, 在哪个目录运行都行,")
    print("      但 自检.py 必须和 backend/ 保持同级(即放在教学包根目录)")
    sys.exit(1)
