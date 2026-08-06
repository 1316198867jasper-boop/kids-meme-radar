# 🔥 小学生热梗雷达

> AI 每日自动追踪全网小学生流行梗 — 帮家长听懂孩子在说什么

## 在线查看

👉 **[点击查看热梗雷达](https://你的用户名.github.io/小学生热梗/)**

## 数据更新

- ⏰ 每天早上 9:00 自动抓取全网数据
- 📊 自动生成日报 + 更新总榜
- 🤖 由 ZCode CronJob 驱动

## 数据来源

- B站 API（热搜、视频搜索、热门视频）
- 今日头条搜索（家长/教师视角）
- 今日热榜（多平台聚合）
- 全网搜索补充

## 文件结构

```
├── index.html          ← 前端页面（GitHub Pages 入口）
├── data.json           ← 结构化数据（每日自动更新）
├── 小学生热梗总览.md    ← 总榜 Markdown 原始数据
├── daily/              ← 每日详细报告
│   ├── 2026-08-06.md
│   └── ...
└── README.md           ← 本文件
```

## 本地预览

```bash
cd 小学生热梗
python3 -m http.server 8765
# 浏览器打开 http://localhost:8765
```

## 部署到 GitHub Pages

1. 创建 GitHub 仓库
2. 推送代码到 main 分支
3. Settings → Pages → Source: main branch, root (/)
4. 等待部署完成，访问 `https://你的用户名.github.io/仓库名/`
