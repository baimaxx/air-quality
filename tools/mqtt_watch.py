"""订阅巴法云 MQTT，看设备上报（凭据从 secrets.yaml 读，不打印）。"""
import re
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt

SECRETS = "/mnt/e/code/zb/esp32-air-monitor/esphome/secrets.yaml"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 90

key = None
for line in open(SECRETS, encoding="utf-8"):
    m = re.match(r"\s*bemfa_key\s*:\s*['\"]?([^'\"\s]+)", line)
    if m:
        key = m.group(1)
assert key, "secrets.yaml 里没找到 bemfa_key"

seen = []


def on_connect(c, u, flags, rc):
    print(f"# connected rc={rc}", flush=True)
    for t in ("esp32air004", "esp32bat", "esp32boot", "esp32reset", "airquality/#", "#"):
        c.subscribe(t)


def on_message(c, u, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    body = msg.payload.decode("utf-8", "replace")
    seen.append((ts, msg.topic, body))
    print(f"[{ts}] {msg.topic} retain={msg.retain} {body}", flush=True)


cli = mqtt.Client(client_id=key)
cli.username_pw_set(key, key)
cli.on_connect = on_connect
cli.on_message = on_message
cli.connect("mqtt.bemfa.com", 9501, 30)
cli.loop_start()
time.sleep(DURATION)
cli.loop_stop()
print(f"# 共 {len(seen)} 条", flush=True)
