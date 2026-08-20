# 医疗疾病智能问答与数据可视化系统

## 项目简介

本项目是一个基于 Flask 的医疗疾病信息查询、智能问答与数据可视化 Web 应用。系统以疾病 CSV 数据为基础，通过 Pandas 完成数据加载与统计分析，使用 Jieba 对疾病简介进行中文分词，并通过 Flask API 为前端 ECharts 大屏提供统计、词云、科室分布、散点分析和关联规则等数据。

项目面向医疗数据展示和辅助查询场景，提供疾病百科、科室分类、药品信息、症状/疾病关键词检索、历史对话以及药房定位等功能。系统输出仅用于信息展示和辅助参考，不替代专业医疗诊断。

## 简历项目描述

**医疗疾病智能问答与数据可视化系统｜Flask + Pandas + Jieba + ECharts**

- 负责基于 Flask 搭建后端 Web 服务和 REST API，完成疾病、科室、药品、历史对话及智能查询等业务接口，并使用 Jinja2 渲染多页面前端。
- 使用 Pandas 读取 GBK 编码医疗疾病 CSV 数据，完成缺失数据处理、疾病科室规则标注、疾病/药品数量统计和分类数据聚合。
- 使用 Jieba 对疾病简介进行中文分词，结合停用词过滤和词频统计生成医疗领域词云数据；基于关键词共现计算关联规则，为疾病信息探索提供辅助分析。
- 使用 ECharts 实现科室分布环形图、疾病简介词云图和科室散点图，并通过 Fetch API 异步加载后端数据，实现图表与查询结果联动。
- 设计疾病名称精确匹配、疾病简介关键词匹配和症状规则兜底三阶段查询流程，并返回推荐科室、相关疾病、排队信息等结构化结果。
- 集成高德地图定位接口和药房查询页面，使用环境变量管理 API Key；通过 `.gitignore` 排除虚拟环境、密钥和运行缓存等非业务文件。

## 技术栈

- **后端**：Python、Flask、Jinja2、REST API
- **数据处理**：Pandas、CSV、中文分词、停用词过滤、词频统计、关键词共现分析
- **前端**：HTML、CSS、JavaScript、Fetch API
- **数据可视化**：ECharts、ECharts WordCloud
- **配置管理**：python-dotenv、环境变量
- **数据存储**：CSV 文件；对话历史同时支持浏览器 localStorage 和服务端内存记录

> 当前代码实际使用 Flask、Pandas、Jieba 和 ECharts。项目名称中的 PySpark 可作为后续大规模数据清洗或离线计算的扩展方向，当前版本未在 `app.py` 中直接使用 PySpark。

## 功能模块

### 1. 数据加载与分类

应用启动时读取 `data/disease_data.csv`，根据疾病简介中的医疗关键词进行科室规则标注，形成呼吸内科、心血管内科、消化内科、感染科等分类数据。

### 2. 可视化数据大屏

首页通过异步 API 获取数据并渲染：

- 疾病总数、科室数量、对话次数和药品数量统计卡片
- 科室疾病数量环形图
- 疾病简介关键词词云图
- 不同科室疾病分布散点图
- 医疗关键词关联规则
- 热门疾病和疾病百科入口

### 3. 智能查询与问答

后端根据输入内容依次执行疾病名称精确匹配、疾病名称/简介关键词匹配和症状规则匹配，并返回相关疾病、推荐科室、治疗手段、常用药品及注意事项等信息。

### 4. 疾病与药品信息

提供疾病详情、科室详情、药品搜索、药品详情和药房页面，支持从疾病、科室和药品之间进行跳转查询。

## 主要接口

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/stats` | GET | 获取疾病、科室和对话统计 |
| `/api/cluster_stats` | GET | 获取科室分布数据 |
| `/api/wordcloud` | GET | 获取词云数据 |
| `/api/scatter` | GET | 获取疾病散点图数据 |
| `/api/rules` | GET | 获取关键词关联规则 |
| `/api/predict` | POST | 根据疾病或症状返回查询结果 |
| `/api/search_drug` | POST | 查询药品相关疾病和注意事项 |
| `/api/add_history` | POST | 保存对话记录 |

## 项目结构

```text
disease_chat_system/
├── app.py                    # Flask 应用入口、路由和业务逻辑
├── data/
│   └── disease_data.csv      # 疾病数据集
├── templates/                # Jinja2 页面模板
├── requirements.txt          # Python 依赖
├── .gitignore                # Git 忽略规则
├── .env                      # 本地环境变量，不提交到 Git
└── README.md
```

## 安装与运行

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

如需使用高德地图定位功能，请在 `.env` 中配置：

```text
GAODE_API_KEY=your_api_key
```

## 运行说明

- 数据文件默认位置为 `data/disease_data.csv`，编码为 `GBK`。
- `app.py` 当前默认监听 `0.0.0.0:5000`。
- 词云和关联规则接口会在请求时基于疾病简介计算结果，数据量较大时可进一步改为离线预处理或缓存。
- 医疗内容仅供信息检索和可视化展示，不能替代医生诊断和处方建议。