# 資料庫 Schema 查詢

## 基礎連線指令

```bash
podman exec mariadb mariadb -h localhost -u root -p'1qaz@WSX'
```

## Input

```
$ARGUMENTS = [database] [table] [--sql 'raw query']
```

所有參數皆為選填，依引數數量自動判斷行為。

---

## Execution Flow

### Step 1: 解析引數

| 引數                 | 行為                      |
| -------------------- | ------------------------- |
| 無引數               | 列出所有資料庫            |
| `<database>`         | 列出該 DB 所有表          |
| `<database> <table>` | 顯示表結構（欄位 + 索引） |
| `--sql '<query>'`    | 執行唯讀 SQL              |

- 從 `$ARGUMENTS` 中先提取 `--sql '...'` 旗標（若存在）
- 剩餘引數依序為 database、table

### Step 2: 安全檢查（僅 `--sql` 模式）

將 SQL 轉為大寫後檢查，若包含以下關鍵字則**拒絕執行並警告**：

```
INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, RENAME, REPLACE, GRANT, REVOKE
```

僅允許：`SELECT`、`SHOW`、`DESCRIBE`、`EXPLAIN`、`WITH`

### Step 3: 執行查詢

根據模式組合指令：

**列出所有資料庫：**

```bash
podman exec mariadb mariadb -h localhost -u root -p'1qaz@WSX' -e "SHOW DATABASES"
```

**列出指定 DB 的表：**

```bash
podman exec mariadb mariadb -h localhost -u root -p'1qaz@WSX' <database> -e "SHOW TABLES"
```

**查看表結構：**

```bash
podman exec mariadb mariadb -h localhost -u root -p'1qaz@WSX' <database> -e "DESCRIBE <table>; SHOW INDEX FROM <table>"
```

**執行唯讀 SQL：**

```bash
podman exec mariadb mariadb -h localhost -u root -p'1qaz@WSX' --safe-updates -e "<sql>"
```

### Step 4: 格式化輸出

- 將查詢結果以 **Markdown 表格**呈現
- 表結構查詢時，分兩區塊顯示：
  1. **欄位定義**：Field、Type、Null、Key、Default、Extra
  2. **索引資訊**：Key_name、Column_name、Non_unique、Index_type

---

## 安全規則

- **唯讀**：絕不執行任何寫入或結構修改操作
- **--safe-updates**：raw SQL 模式強制加此旗標
- **關鍵字過濾**：攔截所有 DML/DDL 語句
- **開發環境限定**：此 skill 僅用於 Podman 本地開發環境

---

## Error Handling

| 錯誤情境          | 處理方式                     |
| ----------------- | ---------------------------- |
| Podman 容器未啟動 | 提示：`podman-compose up -d` |
| 資料庫不存在      | 列出可用資料庫               |
| 表不存在          | 列出該 DB 的可用表           |
| SQL 語法錯誤      | 顯示 MariaDB 錯誤訊息        |
| 含寫入操作的 SQL  | 拒絕執行，顯示警告           |
