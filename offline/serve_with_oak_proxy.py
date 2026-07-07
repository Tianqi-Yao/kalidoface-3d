#!/usr/bin/env python3
"""
kalidoface-3d 离线版静态文件服务器 + OAK-D MJPEG 同源反向代理。

用于把 IMU_GPS/06_Camera/camera_bridge.py 已经暴露的 MJPEG 流(默认
http://<cam-ip>:8080/、:8081/)同源转发到 /oak/cam1、/oak/cam2,这样浏览器里
的 <img>/<canvas> 不会因为跨域而把 canvas 标记为 tainted(canvas.captureStream()
会因此抛 SecurityError)。完全不修改、不依赖 IMU_GPS 仓库任何代码,只从旁路
访问它已经开放的端口。

默认 IP 是 localhost(方便和 camera_bridge.py 跑在同一台机器上本地联调);
部署到机器人网络、跨机器访问时用 --cam1-ip/--cam2-ip 覆盖成实际 IP
(参考 IMU_GPS/config.py 里的 CAM1_IP/CAM2_IP,机器人上默认是
10.95.76.11 / 10.95.76.10)。

用法(在 offline/ 目录下运行):
    python3 serve_with_oak_proxy.py --port 8899
    python3 serve_with_oak_proxy.py --port 8899 --cam1-ip 10.95.76.11 --no-cam2

不需要 OAK 相机时,index.html 里把 OAK_CONFIG.enabled 设为 false 即可,
这个脚本依然可以正常当纯静态文件服务器用(等价于 python3 -m http.server)。
"""
import argparse
import os
import socket
import socketserver
import urllib.request
from http.server import SimpleHTTPRequestHandler, HTTPServer

# 默认指向本机,方便和 camera_bridge.py 跑在同一台机器上本地联调;
# 端口默认对齐 IMU_GPS/config.py 里的 CAM1_STREAM_PORT / CAM2_STREAM_PORT。
# 部署到机器人网络时用 --cam1-ip/--cam2-ip 覆盖成实际 IP
# (机器人上默认是 CAM1_IP=10.95.76.11 / CAM2_IP=10.95.76.10)。
DEFAULT_CAM1_IP = "localhost"
DEFAULT_CAM1_PORT = 8080
DEFAULT_CAM2_IP = "localhost"
DEFAULT_CAM2_PORT = 8081


class OakProxyHandler(SimpleHTTPRequestHandler):
    # 运行时由 main() 注入,例如 {"/oak/cam1": "http://10.95.76.11:8080/"}
    OAK_ROUTES = {}

    def do_GET(self):
        path_only = self.path.split("?", 1)[0]
        target = self.OAK_ROUTES.get(path_only)
        if target:
            return self._proxy_stream(target)
        return super().do_GET()

    def _proxy_stream(self, target_url):
        try:
            upstream = urllib.request.urlopen(target_url, timeout=5)
        except Exception as e:
            self.send_error(502, "OAK upstream unreachable: %s" % e)
            return

        try:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                upstream.headers.get(
                    "Content-Type", "multipart/x-mixed-replace; boundary=frame"
                ),
            )
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # MJPEG 是无 Content-Length 的长连接,纯字节流转发,不做 multipart 解析
            while True:
                chunk = upstream.read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            # 客户端断开连接、或上游相机短暂卡顿超过 urlopen 的 5s timeout,
            # 都是正常/可恢复的情况,不需要当错误处理(否则会在 server 日志里
            # 打出一堆没意义的 traceback)
            pass
        finally:
            upstream.close()

    def log_message(self, fmt, *args):
        # 保留默认的访问日志行为(仅覆盖以便未来按需静音)
        super().log_message(fmt, *args)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    # 必须用 ThreadingMixIn——MJPEG 是无限长连接,单线程 server 会被第一个
    # 请求永久堵死,后续任何静态文件请求都拿不到响应
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8899, help="本地服务器端口")
    parser.add_argument("--cam1-ip", default=DEFAULT_CAM1_IP, help="OAK 相机 1 的 IP")
    parser.add_argument(
        "--cam1-port", type=int, default=DEFAULT_CAM1_PORT, help="OAK 相机 1 的 MJPEG 端口"
    )
    parser.add_argument("--cam2-ip", default=DEFAULT_CAM2_IP, help="OAK 相机 2 的 IP")
    parser.add_argument(
        "--cam2-port", type=int, default=DEFAULT_CAM2_PORT, help="OAK 相机 2 的 MJPEG 端口"
    )
    parser.add_argument(
        "--no-cam2", action="store_true", help="不代理 cam2(只暴露 /oak/cam1)"
    )
    args = parser.parse_args()

    routes = {"/oak/cam1": "http://%s:%d/" % (args.cam1_ip, args.cam1_port)}
    if not args.no_cam2:
        routes["/oak/cam2"] = "http://%s:%d/" % (args.cam2_ip, args.cam2_port)
    OakProxyHandler.OAK_ROUTES = routes

    # 确保静态文件根目录始终是本脚本所在的 offline/ 目录,不受调用时 cwd 影响
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    with ThreadingHTTPServer(("", args.port), OakProxyHandler) as httpd:
        print("Serving offline/ + OAK proxy on http://localhost:%d" % args.port)
        for route, target in routes.items():
            print("  %s  ->  %s" % (route, target))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
