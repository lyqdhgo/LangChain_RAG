# -*- coding: utf-8 -*-
"""后端冒烟测试：不需要 MySQL、Ollama、Chroma 任何一个服务就能跑。

在 server 目录下运行：

    python -m unittest discover -s tests -t . -v

这个测试不验证 RAG 效果，只验证一件更容易被改坏、而且一坏就整个服务不可用的
事情：**应用还能不能起来**。代码会碰的东西有三样，这里刻意一样都不连：

  1. 导入 app 就等于建好了应用（app.py 的模块级 `app = create_app()`），
     而 create_app() 只做注册，不连数据库；
  2. 健康检查里的 MySQL 查询、Ollama 探测都包在 try/except 里，失败被写进
     返回体而不是抛出去；
  3. 受保护接口在没有 token 时直接返回未登录，根本不碰数据库。

所以下面这两个环境变量必须在 `import app` **之前**设好：Config 是在类体里读
环境变量的（config.py），导入 app 的那一刻就已经读完了。指向“必定拒绝连接”
的地址，是为了让健康检查立刻返回，而不是干等 Ollama 那 3 秒超时。
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# 兜底：即使执行时的工作目录不是 server/，也能 import app
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# 必须在 import app 之前。setdefault 而非赋值：CI 里已经导出过同名变量时，
# 以 CI 的为准，两边互不覆盖。
os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:1")  # 端口 1：立即 ECONNREFUSED
os.environ.setdefault("MYSQL_PORT", "3399")                     # 无人监听：立即拒绝

import app as app_module  # noqa: E402


class BackendSmokeTest(unittest.TestCase):
    """进程起得来、路由注册得全、依赖不可用时降级得掉。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = app_module.app.test_client()
        cls.rules = {rule.rule for rule in app_module.app.url_map.iter_rules()}

    def test_health_endpoint_degrades_instead_of_failing(self) -> None:
        """依赖全挂时，健康检查仍然要回 200 和一句能读懂的说明。

        这里断言的是失败的表现形式：mysql 必须是一段字符串状态，而不是异常、
        不是 500。健康检查在依赖挂掉时跟着挂掉，就没有任何东西能报告“为什么
        挂”，这正是它最该起作用的时刻。
        """
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(payload["code"], 200)

        data = payload["data"]
        self.assertEqual(data["server"], "ok")
        self.assertIsInstance(data["mysql"], str)
        self.assertIsInstance(data["ollama"], str)

    def test_core_routes_are_registered(self) -> None:
        """按蓝图分组的每一条主干路径都还在。

        只挑每个蓝图的一条代表，不锁死总数：多出一条路由不该让测试变红，
        少掉一条最核心的才该。
        """
        expected = {
            "/api/health",
            "/api/auth/login",
            "/api/kb/list",
            "/api/chat/stream",
            "/api/stats/overview",
            "/api/user/list",
        }
        missing = expected - self.rules
        self.assertFalse(missing, f"缺少路由：{sorted(missing)}")

    def test_protected_route_rejects_anonymous_without_touching_the_db(self) -> None:
        """没带 token 时走的是“未登录”，不是 500，也不是数据库异常。

        HTTP 状态码是 200、业务码是 401 —— 这是本项目统一的约定（见
        utils/response.py 的说明），前端拦截器按 code 判断。
        """
        response = self.client.get("/api/kb/list")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["code"], 401)


if __name__ == "__main__":
    unittest.main()
