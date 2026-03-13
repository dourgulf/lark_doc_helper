# App 多语言工作流

![Image](https://internal-api-drive-stream-sg.larksuite.com/space/api/box/stream/download/authcode/?code=MTM3N2YwNGY1YmNiMjUwYzEyODY3Mjc4YWQ3Mjk5M2RfNzI5ZTQyNTNlMThmNmZlZDgzMzRiNjdhYmRjNjJkZGJfSUQ6NzYxNjc1NTQwNTY1NzU5MTUxOF8xNzczNDE0MTA2OjE3NzM1MDA1MDZfVjM)

本文档描述从开发、验收到发布的完整多语言（i18n）工作流程，涵盖 AI 自动生成、i18n 平台协作与热更、发版前全量同步等环节。

---

### 2.2 角色与职责

| 角色 | 职责 |
| --- | --- |
| ![Image](https://internal-api-drive-stream-sg.larksuite.com/space/api/box/stream/download/authcode/?code=MTY0YjRlNjk3YjNmMDczZWM1ZTc5ZjgwNjExYjY4ZDJfMDIwYzU0MWU5MTY0MWVjZmRlZmJiYmIxZTM4Mzg2MGJfSUQ6NzYxNjc1NTQ1MzAyODA5MzY2Nl8xNzczNDE0MTA2OjE3NzM1MDA1MDZfVjM) | 按 Figma 实现 UI，维护文案 Key；触发 AI 生成并确认写入本地文件；通过 MCP 提交到 i18n 平台。 |
| AI 助手 | 根据设计稿与 Key 生成各语言初版文案，并写入对应多语言文件。 |
| i18n 平台 | 接收并存储多语言数据，供验收微调与热更、发版同步使用。 |