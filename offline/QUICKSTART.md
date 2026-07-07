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
> 如果要用 OAK-D 相机作为输入源,启动方式不一样,见下面专门一节。

## 验证是否真的能离线用

1. Chrome DevTools → Network 面板 → 勾选 **Offline**
2. 刷新页面,确认摄像头追踪、模型加载均正常

## 停止服务器

终端里按 `Ctrl+C`。

## 让背景显示真实摄像头画面

已经在 `index.html` 里加了一段脚本,新建一个独立的 `#kf3d-camera-bg` 视频元素,
持续同步应用内真实摄像头(`#user-cam`)的画面流,撑满全屏、放到 3D 场景下面。
启用方法:

1. 打开应用后,点开 **Backgrounds(背景)** 面板
2. 选中里面的 **Transparent(透明)** 预设色块 —— 这是应用自带的选项,选中后
   3D 场景背景会变透明,底下露出的就是你摄像头的真实画面

如果画面镜像方向看着不对(左右反了),把 `index.html` 里 `#kf3d-camera-bg` 那段
样式中的 `transform: scaleX(-1);` 删掉或改成 `scaleX(1)` 即可。

## 使用 OAK-D 相机作为输入源

这是一个可选功能:把摄像头输入换成 IMU_GPS 项目里 `06_Camera/camera_bridge.py`
驱动的 OAK-D 深度相机画面,而不是普通 USB 摄像头。**完全不修改 IMU_GPS 仓库任何
代码**,只是从 kalidoface-3d 这一侧,通过网络访问它已经暴露出来的 MJPEG 流。

### 前置条件

- `IMU_GPS/06_Camera/camera_bridge.py` 已经在运行,MJPEG 服务已监听(这一步在
  IMU_GPS 那一侧完成,不属于这个改造范围)
- 默认假设 `camera_bridge.py` 和 kalidoface-3d 跑在**同一台机器**上(cam1 =
  `localhost:8080`,cam2 = `localhost:8081`),方便本地联调。部署到机器人网络、
  跨机器访问时用下面的命令行参数改成实际 IP(机器人上默认是
  `IMU_GPS/config.py` 里的 `CAM1_IP=10.95.76.11` / `CAM2_IP=10.95.76.10`)

### 启动方式

不再用 `python3 -m http.server`,改用新增的反向代理脚本:

```bash
cd offline
python3 serve_with_oak_proxy.py --port 8899
```

跨机器访问机器人上的真实相机,或只有一台相机时:

```bash
python3 serve_with_oak_proxy.py --port 8899 --cam1-ip 10.95.76.11 --no-cam2
```

可用参数:`--port`、`--cam1-ip`、`--cam1-port`、`--cam2-ip`、`--cam2-port`、
`--no-cam2`(默认值:`cam1-ip`/`cam2-ip` 都是 `localhost`,`cam1-port` 是
`8080`,`cam2-port` 是 `8081`)。

### 为什么需要一个反向代理

浏览器如果直接跨域访问 `http://<cam-ip>:8080/` 再 `canvas.captureStream()`,
会因为 canvas 被判定为"跨域污染"(tainted)而抛 `SecurityError`(OAK 那边的
MJPEG 服务器没有设置 CORS 头,而且我们不想为此改 IMU_GPS 的代码)。
`serve_with_oak_proxy.py` 把 `/oak/cam1`、`/oak/cam2` 反代成同源路径,彻底绕开
这个问题。

### 开关 / 切换相机 / 调参数

打开 `index.html`,找到 `OAK_CONFIG` 这个对象(在新增的 `getUserMedia` 补丁脚本
里,`vendor/mediapipe` 那几个 `<script>` 标签之前):

- `enabled`:`false` 时完全不 patch,等同普通摄像头
- `proxyPath`:`"/oak/cam1"` 换成 `"/oak/cam2"` 即可切另一台相机
- `fps`:对齐 OAK 默认帧率,一般不用改
- `firstFrameTimeoutMs`:首帧超时(毫秒),超时会自动回退成调用真实的
  `getUserMedia`(避免 OAK 不可用时整个应用卡死/黑屏)
- `debug`:是否在浏览器 console 打印 `[OAK-bridge]` 前缀日志

改完直接刷新页面即可生效,不需要重启代理脚本。

### 单独验证代理本身

浏览器直接打开 `http://localhost:8899/oak/cam1`,应该能看到持续刷新的画面
(和直接打开 `http://<cam-ip>:8080/` 效果一致,只是经过了本机代理)。如果看到
502,说明代理连不上 OAK 相机(检查 IP/端口、网络连通性、`camera_bridge.py`
是不是真的在跑)。

### 排错

打开浏览器 DevTools 控制台,看 `[OAK-bridge]` 前缀的日志:

- `video request intercepted` → `OAK stream ready: WxH`:正常走 OAK 分支
- `OAK bridge failed, falling back to real camera: ...`:说明超时或加载失败,
  已自动回退到真实摄像头,先按上面"单独验证代理本身"排查
- `audio-only request, passthrough to real getUserMedia`:通话功能的麦克风
  请求正常放行,和 OAK 无关

## 已知的无害外链(断网时会静默 404,不影响功能)

- Google Tag Manager 分析脚本
- favicon / apple-touch-icon(指向 yeemachine.github.io)

## 目录说明

```
offline/
├── index.html              # 已改为引用本地 vendor 脚本 + getUserMedia OAK 补丁
├── serve_with_oak_proxy.py # 静态文件服务器 + OAK MJPEG 同源反向代理(可选)
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
