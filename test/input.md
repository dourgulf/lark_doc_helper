# App 多语言工作流

本文档描述从开发、验收到发布的完整多语言（i18n）工作流程，涵盖 AI 自动生成、i18n 平台协作与热更、发版前全量同步等环节。

---

## 一、工作流总览

三个阶段形成闭环：**开发阶段** 产出初版多语言并推送到 i18n 平台；**验收阶段** 在平台上微调并依赖热更生效；**发布阶段** 全量同步平台数据作为发版多语言。

```mermaid
flowchart LR
    subgraph P1["1. 开发阶段"]
        A1[Figma 设计] --> A2[实现 UI]
        A2 --> A3[AI 生成多语言]
        A3 --> A4[写入本地文件]
        A4 --> A5[MCP 提交 i18n 平台]
    end

    subgraph P2["2. 验收阶段"]
        B1[验收使用 App] --> B2[发现问题文案]
        B2 --> B3[i18n 平台微调]
        B3 --> B4[热更加载]
    end

    subgraph P3["3. 发布阶段"]
        C1[发版前] --> C2[全量同步 i18n]
        C2 --> C3[最终发版多语言]
    end

    P1 --> P2
    P2 --> P3
```

---

## 二、阶段一：开发阶段

开发根据 Figma 实现 UI，由 AI 自动生成多语言并写入项目内多语言文件，再通过 MCP 将内容提交到 i18n 平台。

### 2.1 流程图

```mermaid
flowchart TB
    subgraph Input["输入"]
        Figma[Figma 设计图]
        Keys[文案 Key / 占位]
    end

    subgraph Dev["开发与 AI"]
        UI[开发实现 UI]
        AI[AI 协助]
        AI --> Gen[生成各语言文案]
        Gen --> Write[写入多语言文件]
    end

    subgraph Output["输出"]
        Local["本地多语言文件\n如 localizable_*_en.dart 等"]
        MCP[MCP 客户端]
        i18nPlatform[(i18n 平台)]
    end

    Figma --> UI
    Keys --> AI
    UI --> AI
    Write --> Local
    Local --> MCP
    MCP -->|"提交/同步"| i18nPlatform
```

### 2.2 角色与职责

| 角色       | 职责 |
|------------|------|
| 开发人员   | 按 Figma 实现 UI，维护文案 Key；触发 AI 生成并确认写入本地文件；通过 MCP 提交到 i18n 平台。 |
| AI 助手    | 根据设计稿与 Key 生成各语言初版文案，并写入对应多语言文件。 |
| i18n 平台  | 接收并存储多语言数据，供验收微调与热更、发版同步使用。 |

### 2.3 关键产出

- 项目内多语言源文件已更新（如 `lib/localizations/translations/*/localizable_*.dart`）。
- i18n 平台上存在与当前版本对应的多语言数据，作为后续微调与同步的基准。

---

## 三、阶段二：验收阶段

验收人员在真机/模拟器上使用 App，对 AI 生成的文案进行审阅；不合适处在 i18n 平台上微调，App 通过在线热更拉取最新文案并生效。

### 3.1 流程图

```mermaid
sequenceDiagram
    participant QA as 验收人员
    participant App as App
    participant i18n as i18n 平台
    participant HotReload as 热更服务

    QA->>App: 使用 App，发现不合适文案
    QA->>i18n: 在平台上定位并微调文案
    i18n->>i18n: 保存微调结果
    Note over App,HotReload: 热更触发（定时/手动/启动时）
    App->>HotReload: 请求最新多语言
    HotReload->>i18n: 拉取平台数据
    i18n-->>HotReload: 返回最新文案
    HotReload-->>App: 下发/合并多语言
    App->>App: 重新加载文案并刷新 UI
    QA->>App: 再次验证，确认无误
```

### 3.2 验收阶段流程（泳道图）

```mermaid
flowchart TB
    subgraph QA["验收人员"]
        Q1[使用 App]
        Q2[记录不合适文案]
        Q3[在 i18n 平台修改]
        Q4[再次验收]
    end

    subgraph Platform["i18n 平台"]
        P1[展示 Key / 文案]
        P2[保存微调]
        P3[提供热更 API]
    end

    subgraph AppSide["App 侧"]
        A1[展示当前文案]
        A2[请求热更]
        A3[应用新文案]
        A4[刷新界面]
    end

    Q1 --> A1
    Q2 --> Q3
    Q3 --> P1
    Q3 --> P2
    A2 --> P3
    P3 --> A3
    A3 --> A4
    A4 --> Q4
```

### 3.3 角色与职责

| 角色       | 职责 |
|------------|------|
| 验收人员   | 在实际使用场景下检查文案；在 i18n 平台上对问题 Key 进行微调，不直接改代码。 |
| i18n 平台  | 提供 Key/文案的查询与编辑；对外提供热更接口（或供热更服务拉取）。 |
| App        | 在适当时机（如启动、定时、手动）拉取平台最新多语言并热更，刷新界面。 |

### 3.4 热更说明

- **时机**：应用启动时、定时轮询、或用户/验收触发「检查更新」。
- **范围**：仅多语言文案，不涉及代码或资源包的大版本更新。
- **策略**：可先拉取增量或全量差异，再合并到当前运行时文案并触发 UI 刷新。

---

## 四、阶段三：发布阶段

在版本发布前，开发将 i18n 平台上的「验收后」数据全量同步回工程，作为该版本的最终发版多语言，随包发布。

### 4.1 流程图

```mermaid
flowchart LR
    subgraph PreRelease["发版前"]
        T1[确定发版版本/分支]
        T2[触发全量同步]
    end

    subgraph Sync["同步"]
        i18n[(i18n 平台)]
        Script[同步脚本 / MCP]
        Local[本地多语言文件]
    end

    subgraph Release["发版"]
        Build[构建 App 包]
        Ship[应用商店 / 分发]
    end

    T1 --> T2
    T2 --> Script
    i18n -->|"全量拉取"| Script
    Script -->|"覆盖/合并"| Local
    Local --> Build
    Build --> Ship
```

### 4.2 发布阶段时序

```mermaid
sequenceDiagram
    participant Dev as 开发人员
    participant Script as 同步脚本/MCP
    participant i18n as i18n 平台
    participant Repo as 代码库

    Dev->>Dev: 发版前确认版本
    Dev->>Script: 执行全量同步
    Script->>i18n: 拉取全量多语言数据
    i18n-->>Script: 返回数据
    Script->>Script: 生成/更新本地文件
    Script->>Repo: 写入多语言文件并提交
    Dev->>Repo: 打 Tag / 分支，构建发版
```

### 4.3 角色与职责

| 角色       | 职责 |
|------------|------|
| 开发人员   | 在发版前执行一次「i18n 平台 → 本地」的全量同步，确认多语言文件已提交并参与构建。 |
| 同步工具   | MCP 或脚本从 i18n 平台拉取全量数据，按项目约定写入对应多语言文件。 |

### 4.4 注意事项

- 全量同步应以 **i18n 平台上验收后的数据** 为准，避免覆盖为未验收内容。
- 同步结果需纳入版本控制（如 Git），便于追溯和回滚。
- 若有「仅线上、不发版」的 Key，需在同步规则或平台上做区分，避免误写回工程。

---

## 五、三阶段串联视图

下图为三个阶段在同一视图中的串联关系，便于整体理解。

```mermaid
flowchart TB
    subgraph Phase1["阶段一：开发"]
        direction TB
        F1[Figma] --> F2[实现 UI + AI 生成]
        F2 --> F3[写入本地文件]
        F3 --> F4[MCP → i18n 平台]
    end

    subgraph Phase2["阶段二：验收"]
        direction TB
        S1[验收用 App] --> S2[平台微调]
        S2 --> S3[热更加载]
        S3 --> S4[验收通过]
    end

    subgraph Phase3["阶段三：发布"]
        direction TB
        T1[发版前] --> T2[全量同步 i18n]
        T2 --> T3[多语言随包发版]
    end

    Phase1 --> Phase2
    Phase2 --> Phase3

    style Phase1 fill:#e8f4f8
    style Phase2 fill:#fff4e8
    style Phase3 fill:#e8f8e8
```

---

## 六、检查清单（简要）

- **开发阶段**：Figma 已实现 → AI 已生成并写入本地文件 → MCP 已提交 i18n 平台。
- **验收阶段**：验收已在平台上完成微调 → App 热更已验证能加载平台最新文案。
- **发布阶段**：已执行全量同步 → 多语言文件已提交代码库 → 构建包内文案与平台一致。

---

## 七、文档维护

- **文档路径**：`docs/i18n_workflow.md`
- **变更说明**：流程或角色调整时请同步更新本文档及图中的泳道/节点。

若 i18n 平台、MCP 接口或热更策略有具体规范，可在此文档中增加「平台与接口说明」章节，或链接到对应技术文档。
