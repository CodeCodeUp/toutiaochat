# 资源中心设计文档

> 创建时间：2024-12-24
> 状态：规划中

---

## 一、需求概述

### 1.1 背景

当前系统支持手动输入话题或从预设列表中选择，缺乏热点话题的自动获取能力。为提升内容生产效率和话题时效性，需要引入「资源中心」模块。

### 1.2 核心功能

| 模块 | 功能 | 用途 |
|:---|:---|:---|
| **话题池** | 聚合多平台热榜话题 | 供工作流选题、定时任务随机选题 |
| **素材文章** | 存储优质文章素材 | 二次创作参考、内容结构借鉴 |

### 1.3 设计原则

- **独立模块**：与现有工作流解耦，通过 API 集成
- **多源聚合**：支持多个数据源，降低单点依赖
- **灵活管理**：支持自动采集 + 手动导入

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       资源中心                               │
├─────────────────────┬───────────────────────────────────────┤
│      话题池         │           素材文章                     │
│   (TopicPool)       │      (SourceArticle)                  │
├─────────────────────┼───────────────────────────────────────┤
│ - 微博热搜          │ - 手动 URL 导入                        │
│ - 百度热点          │ - 正文自动提取                         │
│ - 知乎热榜          │ - 来源追溯                            │
│ - 头条热榜          │                                       │
│ - 抖音热点          │                                       │
│ - 手动添加          │                                       │
├─────────────────────┴───────────────────────────────────────┤
│                    采集调度器                                │
│              (基于现有 APScheduler)                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   现有工作流引擎        │
              │ - 话题选择时检索话题池  │
              │ - 生成时可参考素材库    │
              └────────────────────────┘
```

---

## 三、前端 UI 设计

### 3.1 导航结构

采用**单入口 + Tab 切换**方案，在侧边栏新增「资源中心」菜单项：

```
侧边栏:
├── 仪表盘
├── 文章管理
├── 资源中心      ← 新增
├── 提示词管理
├── 账号管理
├── 定时任务
├── 任务队列
├── 系统设置
```

### 3.2 页面布局

```
┌────────────────────────────────────────────────────────────────┐
│  资源中心                                          [采集配置]   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐ ┌──────────────┐                             │
│  │   话题池     │ │   素材文章   │          ← Tab 切换          │
│  └──────────────┘ └──────────────┘                             │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  [话题池 Tab]                                                   │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 筛选: [来源 ▾] [分类 ▾] [状态 ▾]    [手动添加] [立即采集]  ││
│  ├────────────────────────────────────────────────────────────┤│
│  │  □  热度   话题标题                    来源   采集时间  操作││
│  │  □  999K   #某某热点事件...            微博   10分钟前  ... ││
│  │  □  888K   #另一个话题...              百度   15分钟前  ... ││
│  │  □  777K   #第三个话题...              知乎   20分钟前  ... ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                │
│  [素材文章 Tab]                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 筛选: [来源 ▾] [分类 ▾]              [导入文章]            ││
│  ├────────────────────────────────────────────────────────────┤│
│  │  文章标题                      来源    字数   导入时间  操作││
│  │  某某科技文章标题...           头条    2.5K   昨天      ... ││
│  │  另一篇财经分析...             公众号  3.2K   2天前     ... ││
│  └────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### 3.3 交互设计

#### 话题池

| 功能 | 说明 |
|:---|:---|
| 筛选 | 来源（微博/百度/知乎/头条...）、状态（可用/已用/归档）、分类 |
| 手动添加 | 弹窗输入话题标题 |
| 立即采集 | 触发一次全量采集 |
| 行操作 | 复制话题、使用（跳转创建文章）、归档、删除 |
| 批量操作 | 批量归档、批量删除 |

#### 素材文章

| 功能 | 说明 |
|:---|:---|
| 导入文章 | 弹窗输入 URL，自动提取正文 |
| 行操作 | 查看详情（抽屉）、复制内容、删除 |
| 详情抽屉 | 显示全文、来源链接、使用记录 |

#### 采集配置（弹窗）

| 功能 | 说明 |
|:---|:---|
| 数据源开关 | 启用/禁用各平台采集 |
| 采集频率 | 设置定时采集间隔 |
| 自动过期 | 设置话题过期天数 |

---

## 四、数据模型

### 4.1 话题表 (Topic)

```python
class Topic(Base):
    __tablename__ = "topics"

    id: UUID
    title: str                    # 话题标题
    source: str                   # 来源: weibo | baidu | zhihu | toutiao | douyin | manual
    source_url: Optional[str]     # 原始链接
    hot_score: Optional[int]      # 热度值
    category: Optional[str]       # 分类
    tags: JSONB                   # 标签列表
    status: str                   # active | used | archived
    used_count: int = 0           # 被使用次数
    collected_at: datetime        # 采集时间
    expired_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

### 4.2 素材文章表 (SourceArticle)

```python
class SourceArticle(Base):
    __tablename__ = "source_articles"

    id: UUID
    title: str
    content: Text                 # 全文内容
    summary: Optional[str]        # 摘要

    # 来源信息（必须保留）
    source_platform: str          # toutiao | weixin | zhihu | other
    source_url: str               # 原文链接
    author: Optional[str]
    publish_time: Optional[datetime]

    # 元数据
    word_count: int
    tags: JSONB
    category: Optional[str]

    # 使用追踪
    status: str                   # pending | used | archived
    reference_count: int = 0
    referenced_by: JSONB          # 关联的生成文章 ID

    collected_at: datetime
    created_at: datetime
    updated_at: datetime
```

### 4.3 采集配置表 (CollectorConfig)

```python
class CollectorConfig(Base):
    __tablename__ = "collector_configs"

    id: UUID
    source_type: str              # topic | article
    source_name: str              # weibo | baidu | dailyhot
    enabled: bool = True
    schedule_interval: Optional[int]  # 采集间隔（分钟）
    config: JSONB                 # 源特定配置
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## 五、API 设计

```python
# 话题池
GET    /api/v1/topics                    # 列表
POST   /api/v1/topics                    # 手动添加
DELETE /api/v1/topics/{id}
PATCH  /api/v1/topics/{id}/archive       # 归档
POST   /api/v1/topics/collect            # 手动触发采集

# 素材文章
GET    /api/v1/source-articles           # 列表
GET    /api/v1/source-articles/{id}      # 详情
POST   /api/v1/source-articles/import    # URL 导入
DELETE /api/v1/source-articles/{id}

# 采集配置
GET    /api/v1/collectors                # 配置列表
PUT    /api/v1/collectors/{source}       # 更新配置
POST   /api/v1/collectors/{source}/run   # 手动执行
```

---

## 六、与现有系统集成

### 6.1 工作流集成

```python
POST /api/v1/workflows/sessions
{
    "mode": "auto",
    "content_type": "article",
    "topic": "话题文本",
    "topic_id": "uuid",              # 新增: 关联话题池
    "reference_article_ids": ["uuid"] # 新增: 参考文章
}
```

### 6.2 定时任务集成

```python
# ScheduledTask 扩展 topic_mode
topic_mode: random | fixed | list | pool  # 新增 pool 模式

topic_pool_config: {
    "sources": ["weibo", "baidu"],
    "categories": ["科技", "财经"],
    "min_hot_score": 1000
}
```

---

## 七、数据源技术选型

### 7.1 话题采集：DailyHotApi（推荐）

| 项目 | https://github.com/imsyy/DailyHotApi |
|:---|:---|
| 平台数 | 50+ |
| 输出格式 | JSON |
| 部署 | Docker 一键部署 |

**支持平台**：微博、百度、知乎、头条、抖音、B站、小红书、掘金、V2EX 等

**部署命令**：
```bash
docker run -d --name dailyhot-api --restart always -p 6688:6688 imsyy/dailyhot-api:latest
```

**API 示例**：
```bash
GET http://localhost:6688/weibo    # 微博热搜
GET http://localhost:6688/baidu    # 百度热搜
GET http://localhost:6688/zhihu    # 知乎热榜
```

**返回格式**：
```json
{
  "code": 200,
  "data": [
    { "title": "热搜标题", "hot": 1234567, "url": "https://..." }
  ]
}
```

### 7.2 备选：RSSHub

| 项目 | https://github.com/DIYgod/RSSHub |
|:---|:---|
| 定位 | 万物皆可 RSS |
| 输出格式 | XML |
| 注意 | 部分路由需 Cookie |

**公共实例**：
- `https://rsshub.rssforever.com`
- `https://rsshub.feeded.xyz`

### 7.3 文章提取：Trafilatura

```bash
pip install trafilatura
```

```python
from trafilatura import fetch_url, extract

downloaded = fetch_url(url)
result = extract(downloaded, output_format='json')
```

**备选**：Newspaper3k（内置 NLP 功能）

### 7.4 技术选型总结

| 用途 | 方案 | 理由 |
|:---|:---|:---|
| 话题采集 | DailyHotApi | JSON 格式、开箱即用、热度值 |
| 补充源 | RSSHub | 覆盖面广 |
| 文章提取 | Trafilatura | 准确率高、中文支持好 |

---

## 八、风险提示

### 素材文章使用风险

| 风险 | 说明 | 缓解 |
|:---|:---|:---|
| 平台查重 | 头条有原创检测 | 仅作参考，不直接改写 |
| 版权追溯 | 原作者可能投诉 | 保留来源信息 |
| 账号处罚 | 相似度过高 | AI 生成时强调原创 |

---

## 九、实施计划

| 阶段 | 内容 | 优先级 |
|:---|:---|:---|
| Phase 1 | 话题池后端 + DailyHotApi 集成 | P0 |
| Phase 2 | 资源中心 UI（话题池 Tab） | P0 |
| Phase 3 | 素材文章后端 + Trafilatura | P1 |
| Phase 4 | 资源中心 UI（素材文章 Tab） | P1 |
| Phase 5 | 定时任务 pool 模式集成 | P2 |

---

## 参考链接

- [DailyHotApi](https://github.com/imsyy/DailyHotApi)
- [RSSHub](https://github.com/DIYgod/RSSHub)
- [Trafilatura](https://github.com/adbar/trafilatura)
- [TrendRadar](https://github.com/sansan0/TrendRadar)（备选，带 AI 分析）
