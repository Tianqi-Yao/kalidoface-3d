# Kalidoface 3D 离线运行 Quickstart

本目录是 `docs/`(线上生产构建产物)的离线可用版本:所有原本从 `cdn.jsdelivr.net`
加载的 MediaPipe 脚本和模型文件(wasm/tflite/binarypb)都已经下载并 vendor 到
`vendor/mediapipe/` 下,`index.html` 和打包后的 JS 也已改为指向本地路径,断网也能跑。

## 前置要求

- 已安装 Python 3(`python3 --version` 能跑通即可,macOS/大多数 Linux 自带)
- 一个现代浏览器(Chrome/Edge/Firefox 均可)+ 摄像头

## 启动

```bash
cd offline
python3 -m http.server 8899
```

浏览器打开:

```
http://localhost:8899
```

授权摄像头权限,拖入 `.vrm` 模型文件即可开始动作捕捉。

> 端口 8899 可以换成任意空闲端口,例如 `python3 -m http.server 8000`。

## 验证是否真的能离线用

1. Chrome DevTools → Network 面板 → 勾选 **Offline**
2. 刷新页面,确认摄像头追踪、模型加载均正常

## 停止服务器

终端里按 `Ctrl+C`。

## 已知的无害外链(断网时会静默 404,不影响功能)

- Google Tag Manager 分析脚本
- favicon / apple-touch-icon(指向 yeemachine.github.io)

## 目录说明

```
offline/
├── index.html              # 已改为引用本地 vendor 脚本
├── assets/                 # 打包后的 app 主体(已 patch 掉 CDN 路径)
├── global.css / manifest.json / sw.js
└── vendor/mediapipe/
    ├── holistic/            # holistic.js + wasm + tflite 模型
    ├── face_mesh/           # face_mesh.js + wasm + tflite 模型
    └── drawing_utils/       # drawing_utils.js
```

## 背景说明

这个仓库(包括 GitHub 上的官方仓库)从未提交过 Svelte 源码(`src/` 被
`.gitignore` 排除,历史提交里也找不到),所以 `npm run dev` 走不通。本目录是
基于唯一可用的产物——生产构建包(`docs/`)——改造出的离线版本,而非重新构建。
