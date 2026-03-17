# Agent 测试文档

## 一、测试概览

| 指标 | 数值 |
|------|------|
| 总测试用例 | 74 |
| 通过 | 65 |
| 跳过 | 9 |
| 总体覆盖率 | 58% |
| 运行时间 | ~66s |

---

## 二、测试文件结构

```
tests/
├── conftest.py                      # 测试配置和 fixtures
├── unit/
│   ├── test_router.py              # 路由决策测试 (23用例)
│   ├── test_workers.py             # Worker 功能测试 (16用例)
│   ├── test_order_worker.py        # Order Worker 测试 (11用例)
│   ├── test_product_worker.py      # Product Worker 测试 (11用例)
│   └── test_workflow.py           # LangGraph 工作流测试 (7用例)
└── performance/
    └── test_performance.py         # 性能测试 (6用例)
```

---

## 三、测试用例详解

### 3.1 路由决策测试 (`test_router.py`)

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 意图到Worker映射 | `test_intent_to_worker_mapping` | faq→faq_worker, order→order_worker 等7种映射 |
| FAQ意图识别 | `test_route_faq_intent` | "退货政策是什么？" → intent=faq |
| 订单意图识别 | `test_route_order_intent` | "我的订单到哪里了？" → intent=order |
| 商品意图识别 | `test_route_product_intent` | "这款手机有什么配置？" → intent=product |
| 投诉意图识别 | `test_route_complaint_intent` | "产品质量太差了，我要投诉" → intent=complaint |
| 愤怒情绪升级 | `test_angry_sentiment_escalation` | angry+complaint+high → human_worker, urgency=critical |
| 沮丧情绪升级 | `test_frustrated_critical_escalation` | frustrated+critical → human_worker |
| 低紧急度不升级 | `test_angry_not_escalate_when_low_urgency` | angry+low → complaint_worker (不转人工) |
| 无效情感默认值 | `test_invalid_sentiment_defaults_neutral` | sentiment=happy → neutral |
| 无效紧急度默认值 | `test_invalid_urgency_defaults_medium` | urgency=urgent → medium |
| JSON解析失败降级 | `test_json_parse_failure_fallback` | LLM返回无效JSON → 降级到简单分类 |
| LLM异常安全返回 | `test_llm_exception_safe_default` | API异常 → 返回安全默认值 |
| JSON提取 | `test_extract_json_from_response` | 从各种格式提取JSON |

**运行**: `pytest tests/unit/test_router.py -v`

---

### 3.2 Worker 功能测试 (`test_workers.py`)

#### FAQ Worker

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 返回回答 | `test_faq_handle_returns_response` | handle() 返回非空字符串 |
| 空RAG结果处理 | `test_faq_handles_empty_rag_results` | 无检索结果时LLM仍被调用 |
| RAG异常降级 | `test_faq_handles_rag_exception` | 检索异常 → 返回降级消息 |
| 包含检索上下文 | `test_faq_includes_context_in_response` | prompt包含RAG内容 |
| 包含历史记录 | `test_faq_includes_history` | prompt包含对话历史 |

#### Order Worker

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 订单查询处理 | `test_order_handle_query` | 处理订单查询返回结果 |
| 退款请求处理 | `test_order_handle_refund` | 处理退款请求 |

#### Product Worker

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 商品查询处理 | `test_product_handle_query` | 处理商品咨询返回结果 |

#### Complaint Worker

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 投诉处理 | `test_complaint_handles_negatively` | 负面情绪返回抱歉类回复 |
| 紧急投诉转人工 | `test_complaint_escalation_when_urgent` | critical紧急度标记转人工 |

#### Human Worker

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 总是标记转人工 | `test_human_worker_always_escalates` | 返回人工客服提示 |

**运行**: `pytest tests/unit/test_workers.py -v`

---

### 3.3 Order Worker 测试 (`test_order_worker.py`)

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 初始化 | `test_order_worker_initialization` | name="order_worker", description包含"订单" |
| 工具注册 | `test_order_worker_has_tools` | 包含query_order, query_user_orders, process_return |
| order_id上下文 | `test_handle_with_order_id_context` | 带订单号时正确处理 |
| 对话历史 | `test_handle_with_history` | 历史记录被传递 |
| 重试上下文 | `test_handle_with_retry_context` | 包含上次失败原因提示 |
| 空消息降级 | `test_handle_empty_messages_fallback` | 返回系统原因提示 |
| 工具存在性 | `test_query_order_tool_exists` | query_order工具存在 |
| 工具存在性 | `test_query_user_orders_tool_exists` | query_user_orders工具存在 |
| 工具存在性 | `test_process_return_tool_exists` | process_return工具存在 |
| MCP禁用模式 | `test_mcp_disabled_uses_basic_mode` | MCP关闭时使用基础模式 |

**运行**: `pytest tests/unit/test_order_worker.py -v`

---

### 3.4 Product Worker 测试 (`test_product_worker.py`)

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 初始化 | `test_product_worker_initialization` | name="product_worker", description包含"产品" |
| 工具注册 | `test_product_worker_has_search_tool` | 包含search_products工具 |
| product_id上下文 | `test_handle_with_product_id_context` | 带商品ID时正确处理 |
| 对话历史 | `test_handle_with_history` | 历史记录被传递 |
| 重试上下文 | `test_handle_with_retry_context` | 包含上次失败原因提示 |
| 空消息降级 | `test_handle_empty_messages_fallback` | 返回系统原因提示 |
| 搜索工具存在 | `test_search_products_tool_exists` | search_products工具存在 |
| 搜索返回结果 | `test_search_products_returns_results` | 有结果时返回格式化的产品信息 |
| 无结果处理 | `test_search_products_no_results` | 无结果时返回"未查找到" |

**运行**: `pytest tests/unit/test_product_worker.py -v`

---

### 3.5 LangGraph 工作流测试 (`test_workflow.py`)

| 测试点 | 测试方法 | 验证内容 |
|--------|----------|----------|
| 工作流构建 | `test_build_workflow_returns_stategraph` | 返回StateGraph实例 |
| 节点完整性 | `test_workflow_has_all_nodes` | 包含所有Worker节点 |
| 工作流编译 | `test_compile_workflow` | 编译成功返回可执行对象 |
| FAQ执行路径 | `test_workflow_runs_faq_path` | FAQ请求正确路由 |
| 正确Worker路由 | `test_workflow_routes_to_correct_worker` | 返回包含worker信息 |
| 状态结构 | `test_agent_state_structure` | 状态包含所有必要字段 |
| 可选字段 | `test_agent_state_allows_optional_fields` | 可选字段可以为None |

**运行**: `pytest tests/unit/test_workflow.py -v`

---

### 3.6 性能测试 (`test_performance.py`)

| 测试点 | 测试方法 | 阈值 | 验证内容 |
|--------|----------|------|----------|
| FAQ响应时间 | `test_faq_response_time_under_threshold` | <3s | FAQ Worker响应时间 |
| 路由响应时间 | `test_router_response_time` | <1s | 路由决策响应时间 |
| 并发FAQ请求 | `test_concurrent_faq_requests` | 10并发 | 并发处理能力 |
| 并发路由 | `test_concurrent_routing` | 20并发 | 并发路由能力 |
| 批量分类 | `test_batch_intent_classification` | 4条 | 批量处理能力 |
| 编译性能 | `test_workflow_compilation_performance` | <1s平均 | 工作流编译时间 |
| 单例模式 | `test_workflow_singleton_pattern` | 同一实例 | 工作流单例 |
| 典型延迟 | `test_typical_request_latency` | P95<1s | 延迟分布 |
| LLM延迟影响 | `test_llm_latency_impact` | 线性关系 | LLM延迟影响整体响应 |

**运行**: `pytest tests/performance/ -v`

---

## 四、覆盖率统计

| 模块 | 覆盖率 | 测试文件 |
|------|--------|----------|
| `orchestrator/router.py` | 91% | test_router.py |
| `orchestrator/state.py` | 100% | test_router.py |
| `graph/workflow.py` | 100% | test_workflow.py |
| `workers/faq_worker.py` | 89% | test_workers.py |
| `workers/human_worker.py` | 85% | test_workers.py |
| `workers/base_worker.py` | 65% | test_workers.py |
| `workers/product_worker.py` | 58% | test_product_worker.py |
| `workers/order_worker.py` | 41% | test_order_worker.py |
| `tools/mcp_client.py` | 55% | test_order_worker.py |

---

## 五、运行测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行特定测试文件
```bash
# 路由测试
pytest tests/unit/test_router.py -v

# Worker测试
pytest tests/unit/test_workers.py -v

# Order Worker测试
pytest tests/unit/test_order_worker.py -v

# Product Worker测试
pytest tests/unit/test_product_worker.py -v

# 性能测试
pytest tests/performance/ -v
```

### 生成报告
```bash
# HTML报告
pytest tests/ --html=tests/report.html --self-contained-html

# 覆盖率报告
pytest tests/ --cov=src/agents --cov-report=html

# 同时生成
pytest tests/ -v --cov=src/agents --cov-report=term --html=tests/report.html --self-contained-html
```

### 查看报告
```bash
# 打开HTML测试报告
start tests/report.html

# 打开覆盖率报告
start htmlcov/index.html
```

---

## 六、测试环境要求

- Python 3.11+
- pytest 8.0+
- pytest-asyncio
- pytest-cov
- pytest-html

安装依赖:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-html
```

---

## 七、CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=src/agents --cov-report=xml
      - run: pytest tests/ --html=report.html --self-contained-html
```

---

## 八、测试数据

### Fixtures (conftest.py)

| Fixture | 用途 |
|---------|------|
| `event_loop` | 异步测试事件循环 |
| `mock_llm_response` | 创建指定响应的Mock LLM |
| `mock_llm_json_response` | 创建JSON响应的Mock LLM |
| `sample_agent_state` | 示例Agent状态 |
| `mock_rag_results` | Mock RAG检索结果 |

---

## 九、注意事项

1. **网络依赖**: 部分测试需要网络连接，被标记为 `@pytest.mark.skip`
2. **MCP测试**: MCP相关测试需要MCP服务器运行，否则跳过
3. **异步测试**: 使用 `pytest-asyncio`，配置 `asyncio_mode = auto`
4. **Mock策略**: 外部依赖(LLM, RAG, DB)使用mock，避免真实API调用
