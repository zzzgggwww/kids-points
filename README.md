# 🏝️ Kids Points — 小朋友积分系统

给小朋友设计的积分打卡系统，动森风格界面。完成任务（吃菜、拉屎等），大人输入 PIN 确认后直接加星。

## 功能

- ✅ 每日任务打卡，完成即加星
- ✅ PIN 验证（防止小朋友自己加分）
- ✅ 每个任务每天只能完成一次
- ✅ 积分进度条，可视化升级进度
- ✅ 手机浏览器直接访问，无需安装 App

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
2. 小朋友看到今日任务和总积分
3. 点击任务 → 大人输入 PIN → 直接加星
4. 每个任务可配置不同星数

## 数据备份

复制 `data/points.db` 文件即可备份所有数据。

## 技术栈

- **后端**: Python + FastAPI + SQLite（零外部依赖）
- **前端**: 纯 HTML/CSS/JS（单文件，零依赖）
- **数据库**: SQLite（单文件 `data/points.db`）
- **部署**: 容器内运行 + 守护进程自启

## 项目结构

```
kids-points/
├── app.py              # 后端：API 路由 + SQLite 操作
├── run.sh              # 守护进程：崩溃自动重启
├── static/
│   └── index.html      # 前端：单页应用（HTML+CSS+JS）
├── data/
│   └── points.db       # SQLite 数据库（运行时自动生成）
└── README.md
```

## License

MIT
