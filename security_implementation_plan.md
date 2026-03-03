# 分布式游戏服务器：非对称加密通讯与身份 ID 重构计划 (Security Implementation Plan)

## 1. 核心目标
- **增强安全性**: 使用非对称加密（Ed25519 或 RSA）替代简单的 UUID ID。
- **身份防伪造**: Agent 的 `node_id` 直接由公钥派生。
- **请求签名**: Center 通过签名验证 Agent 发出的心跳与注册请求。
- **防止重放**: 引入时间戳签名校验。

---

## 2. 实施路线图 (Implementation Roadmap)

### Phase 1: 基础设施与库定义
- [ ] **依赖配置**: 在 `requirements.txt` 中添加 `cryptography`。
- [ ] **工具类实现**: 创建 `edge_agent/crypto_utils.py`：
    - `generate_key_pair()`: 首次启动生成并保存密钥。
    - `get_node_id_from_pubkey()`: 从公钥生成唯一的 Base64 ID。
    - `sign_payload(payload, private_key)`: 对 JSON 负载进行 Ed25519 签名。
    - `verify_signature(payload, signature, public_key)`: Center 端验证签名。

### Phase 2: Agent 端逻辑重绘
- [ ] **密钥初始化**: 启动时自动检查 `/app/data/node.key` (私钥) 与 `node_pub.pem` (公钥)。
- [ ] **UUID 弃用**: 修改 `agent.py` 中的 `get_node_id()`，改从公钥生成 ID。
- [ ] **心跳签名**: 修改 `heartbeat_loop`，在心跳 POST 请求中附加 `X-Signature` 和 `X-Timestamp` 请求头。

### Phase 3: Center 端验证逻辑实现
- [ ] **数据库模型升级**:
    - `nodes` 表新增 `public_key` (TEXT/BLOB) 字段。
- [ ] **注册接口升级**: 
    - `/api/nodes/register` 接口要求上报完整的公钥。
    - 校验上报的公钥与派生的 `node_id` 是否匹配。
- [ ] **身份验证守卫 (Guard)**:
    - 实现 FastAPI 依赖性注入（Dependency），拦截所有 `/api/nodes/{node_id}/...` 请求。
    - 根据 `node_id` 查询数据库中的公钥，验证 `X-Signature`。

### Phase 4: UI 与 UX 适配
- [ ] **ID 显示优化**: 由于公钥派生的 ID 可能较长，前端 Dashboard 的节点表格增加 `ellipsis` 或支持点击复制。
- [ ] **状态页更新**: Agent 本地状态页显示「密钥指纹 (Fingerprint)」以供管理员手动核对。

---

## 3. 安全性分析 (Security Analysis)

| 威胁 | 方案 | 效果 |
| :--- | :--- | :--- |
| **伪造 Agent** | 身份绑定私钥签名 | **解决**: 只有持有私钥的人才能以特定 ID 发送心跳。 |
| **中间人修改指令** | 全量 payload 签名 | **解决**: 修改中间数据会导致 Center 端验证签名失败。 |
| **信道窃听** | (本方案) 仅验证身份 | **备注**: 建议配合 Center 启用 HTTPS 保护数据隐私。 |
| **重放攻击** | 签名中包含时间戳 | **解决**: Center 会丢弃超过 30s 的旧请求。 |

---

## 4. 后续扩展性
- **双向校验**: 后续可实现 Center 下发指令时使用 Center 私钥签名，Agent 验证公钥，确保指令来源可靠。
- **证书链**: 允许管理员手动下发「根证书」到所有 Agent，构建受信任的私有算力网络。
