"""
Monitor key checkpoints in the video pipeline every second.

Key checkpoints:
1) UDP packet ingress on port 3334
2) UDP frame reassembly completeness (based on 8-byte header)
3) WebSocket connection state on port 8765
4) WebSocket binary payload ingress

Usage:
  python debug_video_pipeline_watch.py
  python debug_video_pipeline_watch.py --udp-host 0.0.0.0 --udp-port 3334 --ws-url ws://127.0.0.1:8765 --interval 1
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FrameState:
    total_bytes: int
    received_bytes: int = 0
    slices: set[int] = field(default_factory=set)
    updated_at: float = field(default_factory=time.monotonic)


@dataclass
class Stats:
    udp_packets_total: int = 0
    udp_bytes_total: int = 0
    udp_frames_completed_total: int = 0
    udp_frames_dropped_total: int = 0
    udp_last_packet_at: float = 0.0
    udp_last_frame_at: float = 0.0

    ws_connected: bool = False
    ws_messages_total: int = 0
    ws_binary_messages_total: int = 0
    ws_bytes_total: int = 0
    ws_last_message_at: float = 0.0
    ws_last_error: str = ""

    # interval snapshots
    prev_udp_packets_total: int = 0
    prev_udp_frames_completed_total: int = 0
    prev_ws_binary_messages_total: int = 0
    prev_ws_bytes_total: int = 0


class VideoPipelineWatcher:
    def __init__(
        self,
        udp_host: str,
        udp_port: int,
        ws_url: str,
        interval: float,
        frame_timeout_s: float,
        healthy_timeout_s: float,
    ) -> None:
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.ws_url = ws_url
        self.interval = interval
        self.frame_timeout_s = frame_timeout_s
        self.healthy_timeout_s = healthy_timeout_s

        self._stats = Stats()
        self._frames: Dict[int, FrameState] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def start(self) -> None:
        udp_thread = threading.Thread(target=self._udp_loop, daemon=True)
        ws_thread = threading.Thread(target=self._ws_loop_thread, daemon=True)
        udp_thread.start()
        ws_thread.start()

        print("=" * 72)
        print("视频链路关键位监视器已启动")
        print(f"UDP: {self.udp_host}:{self.udp_port} | WS: {self.ws_url} | 间隔: {self.interval}s")
        print("状态含义: OK=到位  MISS=未到位")
        print("=" * 72)

        try:
            while not self._stop_event.is_set():
                time.sleep(self.interval)
                self._cleanup_stale_frames()
                self._print_tick_report(self._build_tick_report())
        except KeyboardInterrupt:
            self._stop_event.set()
            print("\n监视器已停止（keyboard interrupt）")

    def _udp_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind((self.udp_host, self.udp_port))
        except OSError as exc:
            with self._lock:
                self._stats.ws_last_error = f"udp_bind_failed: {exc}"
            return

        while not self._stop_event.is_set():
            try:
                data, _ = sock.recvfrom(65535)
            except OSError:
                continue

            now = time.monotonic()
            with self._lock:
                self._stats.udp_packets_total += 1
                self._stats.udp_bytes_total += len(data)
                self._stats.udp_last_packet_at = now

            self._ingest_udp_packet(data, now)

    def _ingest_udp_packet(self, packet: bytes, now: float) -> None:
        if len(packet) < 9:
            return

        frame_id = struct.unpack_from(">H", packet, 0)[0]
        slice_id = struct.unpack_from(">H", packet, 2)[0]
        total_bytes = struct.unpack_from(">I", packet, 4)[0]
        payload = packet[8:]

        if total_bytes <= 0 or not payload:
            return

        with self._lock:
            frame = self._frames.get(frame_id)
            if frame is None:
                frame = FrameState(total_bytes=total_bytes)
                self._frames[frame_id] = frame

            if frame.total_bytes != total_bytes:
                self._frames.pop(frame_id, None)
                self._stats.udp_frames_dropped_total += 1
                return

            frame.updated_at = now
            if slice_id not in frame.slices:
                frame.slices.add(slice_id)
                frame.received_bytes += len(payload)

            if frame.received_bytes == frame.total_bytes:
                self._frames.pop(frame_id, None)
                self._stats.udp_frames_completed_total += 1
                self._stats.udp_last_frame_at = now
            elif frame.received_bytes > frame.total_bytes:
                self._frames.pop(frame_id, None)
                self._stats.udp_frames_dropped_total += 1

    def _cleanup_stale_frames(self) -> None:
        now = time.monotonic()
        with self._lock:
            stale_ids = [
                frame_id
                for frame_id, state in self._frames.items()
                if now - state.updated_at > self.frame_timeout_s
            ]
            for frame_id in stale_ids:
                self._frames.pop(frame_id, None)
                self._stats.udp_frames_dropped_total += 1

    def _ws_loop_thread(self) -> None:
        asyncio.run(self._ws_loop())

    async def _ws_loop(self) -> None:
        try:
            import websockets
        except ImportError:
            with self._lock:
                self._stats.ws_last_error = "websockets_not_installed"
            return

        retry = 0
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url, open_timeout=3, close_timeout=1) as ws:
                    with self._lock:
                        self._stats.ws_connected = True
                        self._stats.ws_last_error = ""
                    retry = 0

                    async for msg in ws:
                        now = time.monotonic()
                        with self._lock:
                            self._stats.ws_messages_total += 1
                            self._stats.ws_last_message_at = now
                            if isinstance(msg, (bytes, bytearray)):
                                self._stats.ws_binary_messages_total += 1
                                self._stats.ws_bytes_total += len(msg)
            except Exception as exc:
                with self._lock:
                    self._stats.ws_connected = False
                    self._stats.ws_last_error = f"{type(exc).__name__}: {exc}"

                retry += 1
                delay = min(0.5 * (2 ** retry), 8.0)
                await asyncio.sleep(delay)

    def _build_tick_report(self) -> Dict[str, Any]:
        now = time.monotonic()
        wall_clock = time.strftime("%H:%M:%S", time.localtime())

        with self._lock:
            s = self._stats
            udp_pps = s.udp_packets_total - s.prev_udp_packets_total
            frames_ps = s.udp_frames_completed_total - s.prev_udp_frames_completed_total
            ws_mps = s.ws_binary_messages_total - s.prev_ws_binary_messages_total
            ws_bps = s.ws_bytes_total - s.prev_ws_bytes_total

            s.prev_udp_packets_total = s.udp_packets_total
            s.prev_udp_frames_completed_total = s.udp_frames_completed_total
            s.prev_ws_binary_messages_total = s.ws_binary_messages_total
            s.prev_ws_bytes_total = s.ws_bytes_total

            udp_packet_ok = bool(s.udp_last_packet_at and (now - s.udp_last_packet_at) <= self.healthy_timeout_s)
            udp_frame_ok = bool(s.udp_last_frame_at and (now - s.udp_last_frame_at) <= self.healthy_timeout_s)
            ws_msg_ok = bool(s.ws_last_message_at and (now - s.ws_last_message_at) <= self.healthy_timeout_s)

            udp_last_packet_age_s = (now - s.udp_last_packet_at) if s.udp_last_packet_at else None
            udp_last_frame_age_s = (now - s.udp_last_frame_at) if s.udp_last_frame_at else None
            ws_last_message_age_s = (now - s.ws_last_message_at) if s.ws_last_message_at else None

            diagnosis = "链路正常"
            if not udp_packet_ok:
                diagnosis = "UDP输入缺失：请检查推流端是否在发送到 3334"
            elif not udp_frame_ok:
                diagnosis = "UDP重组异常：分片可能丢失/乱序严重"
            elif not s.ws_connected:
                diagnosis = "WS未连接：请检查 video_server 的 8765 监听"
            elif not ws_msg_ok:
                diagnosis = "疑似转码/推送段阻塞：UDP有帧但WS无新消息"

            return {
                "type": "tick",
                "time": wall_clock,
                "health": {
                    "udp_packet_ok": udp_packet_ok,
                    "udp_frame_ok": udp_frame_ok,
                    "ws_connected": s.ws_connected,
                    "ws_message_ok": ws_msg_ok,
                },
                "rate": {
                    "udp_packets_per_sec": udp_pps,
                    "udp_frames_per_sec": frames_ps,
                    "ws_binary_msgs_per_sec": ws_mps,
                    "ws_bytes_per_sec": ws_bps,
                },
                "total": {
                    "udp_packets": s.udp_packets_total,
                    "udp_frames_completed": s.udp_frames_completed_total,
                    "udp_frames_dropped": s.udp_frames_dropped_total,
                    "ws_binary_messages": s.ws_binary_messages_total,
                    "ws_bytes": s.ws_bytes_total,
                },
                "state": {
                    "pending_frame_slots": len(self._frames),
                    "udp_last_packet_age_s": udp_last_packet_age_s,
                    "udp_last_frame_age_s": udp_last_frame_age_s,
                    "ws_last_message_age_s": ws_last_message_age_s,
                    "ws_last_error": s.ws_last_error,
                },
                "diagnosis": diagnosis,
            }

    @staticmethod
    def _ok_mark(ok: bool) -> str:
        return "OK" if ok else "MISS"

    def _print_tick_report(self, report: Dict[str, Any]) -> None:
        health = report["health"]
        rate = report["rate"]
        total = report["total"]
        state = report["state"]

        header = (
            f"[{report['time']}] "
            f"UDP包:{self._ok_mark(health['udp_packet_ok'])} "
            f"UDP帧:{self._ok_mark(health['udp_frame_ok'])} "
            f"WS连通:{self._ok_mark(health['ws_connected'])} "
            f"WS消息:{self._ok_mark(health['ws_message_ok'])}"
        )
        print(header)
        print(
            "  速率  "
            f"udp={rate['udp_packets_per_sec']} pkt/s, "
            f"frame={rate['udp_frames_per_sec']} frame/s, "
            f"ws_msg_rate={rate['ws_binary_msgs_per_sec']} msg/s, "
            f"ws={rate['ws_bytes_per_sec']} B/s"
        )
        print(
            "  累计  "
            f"udp_pkt={total['udp_packets']}, "
            f"udp_frame_ok={total['udp_frames_completed']}, "
            f"udp_frame_drop={total['udp_frames_dropped']}, "
            f"ws_msg_total={total['ws_binary_messages']}, "
            f"ws_bytes={total['ws_bytes']}"
        )

        age_udp_pkt = "N/A" if state["udp_last_packet_age_s"] is None else f"{state['udp_last_packet_age_s']:.1f}s"
        age_udp_frame = "N/A" if state["udp_last_frame_age_s"] is None else f"{state['udp_last_frame_age_s']:.1f}s"
        age_ws_msg = "N/A" if state["ws_last_message_age_s"] is None else f"{state['ws_last_message_age_s']:.1f}s"

        extra = (
            f"  状态  pending_frames={state['pending_frame_slots']}, "
            f"udp_pkt_age={age_udp_pkt}, "
            f"udp_frame_age={age_udp_frame}, "
            f"ws_msg_age={age_ws_msg}"
        )
        if state["ws_last_error"]:
            extra += f" | ws_error={state['ws_last_error']}"
        print(extra)
        print(f"  结论  {report['diagnosis']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch key video pipeline checkpoints every second")
    parser.add_argument("--udp-host", default="0.0.0.0", help="UDP bind host")
    parser.add_argument("--udp-port", type=int, default=3334, help="UDP bind port")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8765", help="WebSocket URL")
    parser.add_argument("--interval", type=float, default=1.0, help="Tick interval in seconds")
    parser.add_argument("--frame-timeout", type=float, default=2.0, help="Reassembly frame timeout in seconds")
    parser.add_argument("--healthy-timeout", type=float, default=2.5, help="Health timeout in seconds")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    watcher = VideoPipelineWatcher(
        udp_host=args.udp_host,
        udp_port=args.udp_port,
        ws_url=args.ws_url,
        interval=max(0.2, args.interval),
        frame_timeout_s=max(0.2, args.frame_timeout),
        healthy_timeout_s=max(0.2, args.healthy_timeout),
    )
    watcher.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
