# 前端 UI P0 基线文档

## 目标
P0 聚焦基础统一与可读性修复，不做大幅视觉重设计。

- 统一 token 来源，避免多套语义变量并存。
- 统一页面状态表达，确保 loading / empty / error / offline / retry 一致。
- 修复登录、搜索、后台监控页文案可读性问题。
- 建立动效基线和无障碍降级规则。

## Token 规范
单一语义来源：`src/theme/tokens.ts`。

- 色彩：统一使用 `semanticMap` 与 `--ds-*` 变量。
- 圆角：`--ds-radius-sm/md/lg/xl`。
- 阴影：`--ds-shadow-sm/md/lg`。
- 动效时长：`--ds-duration-fast/base/slow`。
- 动效曲线：`--ds-ease-standard`、`--ds-ease-emphasized`。

## 状态组件规范
统一组件：`src/components/common/UIState.vue`。

- 类型：`loading | empty | error | offline | retry`。
- 输入：`type`、`title`、`description`、`actionText`。
- 事件：`action`。
- 场景：搜索页、聊天记录加载、后台监控页。

## 文案规范
默认中文产品语境，术语统一。

- 会话、模型监控、中间件状态、检索质量、退出登录。
- 按钮优先动词：刷新、重试、删除选中。
- 错误信息清晰具体：说明问题 + 给出可执行动作。

## 动效规范
统一使用 design-system 动效变量。

- hover/active/列表入场/路由淡入淡出节奏一致。
- 避免局部页面自定义离散 easing。
- 启用 `prefers-reduced-motion` 降级。

## 验收标准
- 前端构建通过，类型检查无新增错误。
- 登录、聊天、搜索、后台页面均可正常加载。
- 状态组件在不同页面视觉和语义一致。
- 关键中文文案无乱码、无歧义。
- reduced motion 开启时动画自动降级。

## Do / Don't
Do:
- 新增状态反馈优先复用 `UIState`。
- 新增样式优先复用 `--ds-*` 变量。
- 新增动效优先复用 `--ds-duration-*` 与 `--ds-ease-*`。

Don't:
- 不新增第二套语义色板变量。
- 不在页面内硬编码重复状态卡样式。
- 不在基础按钮交互上使用不一致的过渡曲线。
