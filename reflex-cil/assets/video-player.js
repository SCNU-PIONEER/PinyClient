/**
 * video-player.js
 * MSE (Media Source Extensions) + WebSocket 视频播放器
 * 连接到 video_server.py 的 WebSocket (port 8765)，接收 frag MP4 (H.264) 数据流。
 */
(function () {
  if (window.__pvInit) return;
  window.__pvInit = true;

  var WS_PORT = 8765;
  var QUEUE_MAX = 30;      // 最大排队帧数
  var KEEP_SEC = 5;        // MSE 缓冲保留秒数
  var STALL_TIMEOUT_MS = 8000;
  var STALL_CHECK_INTERVAL_MS = 2000;
  var MIME_CANDIDATES = [
    'video/mp4; codecs="avc1.42C01F"',
    'video/mp4; codecs="avc1.42E01F"',
    'video/mp4; codecs="avc1.42E01E"'
  ];

  function selectMimeType() {
    for (var index = 0; index < MIME_CANDIDATES.length; index++) {
      if (MediaSource.isTypeSupported(MIME_CANDIDATES[index])) {
        return MIME_CANDIDATES[index];
      }
    }
    return MIME_CANDIDATES[0];
  }

  /** 轮询等待 DOM 元素就绪 */
  function waitForElement(id, cb) {
    var deadline = Date.now() + 12000;
    (function poll() {
      var el = document.getElementById(id);
      if (el) { cb(el); return; }
      if (Date.now() < deadline) { setTimeout(poll, 150); }
    })();
  }

  waitForElement('pioneer-video', function (video) {
    // React 对 muted 属性有已知 Bug，必须用 JS 直接设置
    video.muted = true;
    video.autoplay = true;
    console.log('[VideoPlayer] 找到 video 元素，开始初始化 MSE');

    var ms = null;
    var sb = null;
    var queue = [];
    var ws = null;
    var reconnectTimer = null;
    var stallTimer = null;
    var lastPacketAt = 0;
    var receivedFrameInSession = false;
    var retries = 0;
    var mimeType = selectMimeType();

    function trimQueue() {
      while (queue.length > QUEUE_MAX) queue.shift();
    }

    function appendNext() {
      if (!sb || sb.updating || queue.length === 0) return;
      var chunk = queue.shift();
      try {
        // 清理已播放的旧缓冲，防止 QuotaExceededError
        if (sb.buffered.length > 0 && video.currentTime > KEEP_SEC && !sb.updating) {
          var start = sb.buffered.start(0);
          var trim = video.currentTime - KEEP_SEC;
          if (trim > start) {
            sb.remove(start, trim);
            // remove 会触发 updateend，届时再 appendNext
            queue.unshift(chunk);
            return;
          }
        }
        sb.appendBuffer(chunk);
        if (video.paused) {
          video.play().catch(function () {});
        }
      } catch (e) {
        if (e.name === 'QuotaExceededError') {
          try {
            if (sb.buffered.length > 0 && !sb.updating) {
              sb.remove(sb.buffered.start(0), Math.max(0, video.currentTime - 1));
            }
          } catch (_) {}
        }
        // 若 appendBuffer 失败，将 chunk 放回队头等待下次尝试
        queue.unshift(chunk);
      }
    }

    function initMediaSource() {
      ms = new MediaSource();
      sb = null;
      queue = [];

      ms.addEventListener('sourceopen', function () {
        console.log('[VideoPlayer] MediaSource sourceopen');
        try {
          sb = ms.addSourceBuffer(mimeType);
          console.log('[VideoPlayer] SourceBuffer 创建成功, mime=' + mimeType);
          sb.addEventListener('updateend', appendNext);
          appendNext();
        } catch (e) {
          console.error('[VideoPlayer] MSE SourceBuffer 初始化失败:', e);
        }
      });

      video.src = URL.createObjectURL(ms);
    }

    function resetMediaSource() {
      try {
        if (sb && sb.updating) {
          sb.abort();
        }
      } catch (_) {}

      try {
        if (ms && ms.readyState === 'open') {
          ms.endOfStream();
        }
      } catch (_) {}

      initMediaSource();
    }

    function scheduleReconnect() {
      if (reconnectTimer) return;
      var delay = Math.min(500 * Math.pow(2, retries), 16000);
      retries++;
      reconnectTimer = setTimeout(function () {
        reconnectTimer = null;
        connect();
      }, delay);
      console.log('[VideoPlayer] WebSocket 断开，' + delay + 'ms 后重连');
    }

    initMediaSource();

    function connect() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return;
      }

      var wsUrl = 'ws://' + location.hostname + ':' + WS_PORT;
      ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = function () {
        retries = 0;
        lastPacketAt = 0;
        receivedFrameInSession = false;
        console.log('[VideoPlayer] WebSocket 已连接 ' + wsUrl + '  sb就绪=' + !!sb);
      };

      ws.onmessage = function (e) {
        if (!(e.data instanceof ArrayBuffer)) return;
        receivedFrameInSession = true;
        lastPacketAt = Date.now();
        if (!sb) {
          queue.push(e.data);
          trimQueue();
          return;
        }
        if (sb.updating || queue.length > 0) {
          queue.push(e.data);
          trimQueue();
        } else {
          try {
            sb.appendBuffer(e.data);
            if (video.paused) {
              video.play().catch(function () {});
            }
          } catch (err) {
            queue.push(e.data);
            trimQueue();
          }
        }
      };

      ws.onclose = function () {
        ws = null;
        scheduleReconnect();
      };

      ws.onerror = function () {
        try { ws.close(); } catch (_) {}
      };
    }

    stallTimer = setInterval(function () {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (!receivedFrameInSession) return;
      if (!lastPacketAt) return;

      if (Date.now() - lastPacketAt > STALL_TIMEOUT_MS) {
        console.warn('[VideoPlayer] 检测到视频流超时，执行自愈重连');
        resetMediaSource();
        try { ws.close(); } catch (_) {}
      }
    }, STALL_CHECK_INTERVAL_MS);

    connect();

    window.addEventListener('beforeunload', function () {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (stallTimer) clearInterval(stallTimer);
      if (ws) {
        try { ws.close(); } catch (_) {}
      }
    });
  });
})();
