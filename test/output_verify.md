# App 多语言工作流

![Image](https://internal-api-drive-stream-sg.larksuite.com/space/api/box/stream/download/authcode/?code=Y2RlNjhmMDQwNDQyNjhhMjQ5NWNiYWI3ZTNhNGJkY2RfNGEyZDE3MDBiZDhiMTA4MGFiNzZiOWYzN2MxODVlMDNfSUQ6NzYxNjc2MDQzMzkwNDA5NDk0Nl8xNzczNDE1MjY4OjE3NzM1MDE2NjhfVjM)

本文档描述从开发、验收到发布的完整多语言（i18n）工作流程，涵盖 AI 自动生成、i18n 平台协作与热更、发版前全量同步等环节。

---

### 2.2 角色与职责

| 角色 | 职责 |
| --- | --- |
| 如果还有些文字在前面呢？ <br>![Image](https://internal-api-drive-stream-sg.larksuite.com/space/api/box/stream/download/authcode/?code=MmFkMmQ2Zjk3OTM0YzQxZDVjYjI0MGQ3NTdlMmZiYmRfNDY2NDE4YTBkMWIwNzkwZDYxMWY1YTkzYzU3YmIzYmRfSUQ6NzYxNjc2MDQ2NTA0NTE4MDEzMF8xNzczNDE1MjY4OjE3NzM1MDE2NjhfVjM) | 按 Figma 实现 UI，维护文案 Key；触发 AI 生成并确认写入本地文件；通过 MCP 提交到 i18n 平台。 |
| AI 助手 | 根据设计稿与 Key 生成各语言初版文案，并写入对应多语言文件。 |
| i18n 平台 | 接收并存储多语言数据，供验收微调与热更、发版同步使用。 |