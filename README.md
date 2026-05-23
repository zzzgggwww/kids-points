# 🏝️ Kids Points — 小朋友积分系统

动森风格的小朋友积分管理系统。每次完成任务（如吃菜），大人输入 PIN 后直接加星。

## 快速启动

```bash
cd kids-points
pip install fastapi uvicorn
python app.py
# → http://0.0.0.0:2020
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KIDS_PORT` | `2020` | 服务端口 |
| `KID_NAME` | `小宝` | 小朋友名字 |
| `KIDS_PIN` | `159357` | 大人验证 PIN（6位） |

## 使用方法

1. 手机浏览器访问服务地址
2. 小朋友可以看到今日任务和总积分
3. 大人点击「完成任务」→ 输入 PIN → 直接加星
4. 每个任务可配置不同的星数

## 数据备份

复制 `data/points.db` 文件即可。

## 技术栈

- **后端**: Python + FastAPI + SQLite
- **前端**: 纯 HTML/CSS/JS（零依赖）
- **数据库**: SQLite（单文件 `data/points.db`）
- **风格**: 动物森友会（Nook Phone 风格）
