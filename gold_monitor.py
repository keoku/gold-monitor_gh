#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
  黄金价格智能监控系统 (中国版) — GitHub Actions 云端版
"""

import os
import json
import time
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote

# ═══════════════════════ 配置 ═══════════════════════
GOLD_GRAMS = 69
INVESTED_AMOUNT = 72000
EMAIL_CONFIG = {
    "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
    "sender_name": "黄金智能监控",
    "from_email": "onboarding@resend.dev",
}
DAILY_ALERT_PCT = 1.5
WEEKLY_ALERT_PCT = 3.0


def load_recipients():
    try:
        with open("recipients.json", "r", encoding="utf-8") as f:
            recipients = json.load(f)
            if recipients:
                return recipients
    except Exception:
        pass
    return ["1137206138@qq.com"]


# ═══════════════════ 数据获取 ═══════════════════
def http_get(url, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 GoldMonitor/1.0"}
    for attempt in range(3):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1)


def get_current_gold_price():
    result = {
        "price_cny_gram": None, "price_usd_oz": None,
        "usd_cny_rate": None, "source": "", "success": False,
    }
    for name, url, parse_fn in [
        ("metals.live", "https://api.metals.live/v1/spot/gold",
         lambda d: float(json.loads(d)[0]["price"])),
        ("goldprice.org", "https://data-asg.goldprice.org/dbXRates/USD",
         lambda d: float(json.loads(d)["items"][0]["xauPrice"])),
        ("Yahoo Finance", "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
         lambda d: json.loads(d)["chart"]["result"][0]["meta"]["regularMarketPrice"]),
    ]:
        try:
            result["price_usd_oz"] = parse_fn(http_get(url, {"User-Agent": "Mozilla/5.0"}))
            result["source"] = name
            break
        except Exception as e:
            print(f"[数据源] {name} 失败: {e}")

    if not result["price_usd_oz"]:
        return result

    try:
        obj = json.loads(http_get("https://api.frankfurter.app/latest?from=USD&to=CNY"))
        result["usd_cny_rate"] = obj["rates"]["CNY"]
    except Exception:
        result["usd_cny_rate"] = 7.25

    result["price_cny_gram"] = round(result["price_usd_oz"] * result["usd_cny_rate"] / 31.1035, 2)
    result["success"] = True
    return result


def get_historical_close(target_date_str):
    try:
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        start = int((target_dt - timedelta(days=3)).timestamp())
        end = int((target_dt + timedelta(days=1)).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?period1={start}&period2={end}&interval=1d"
        data = http_get(url, {"User-Agent": "Mozilla/5.0"})
        obj = json.loads(data)
        r = obj["chart"]["result"][0]
        ts = r.get("timestamp", [])
        closes = r["indicators"]["quote"][0].get("close", [])
        if not ts or not closes:
            return None
        target_ts = int(target_dt.timestamp())
        best, best_diff = None, float("inf")
        for t, c in zip(ts, closes):
            if c is None:
                continue
            diff = abs(t - target_ts)
            if diff < best_diff and diff < 86400 * 3:
                best_diff, best = diff, c
        return best
    except Exception as e:
        print(f"历史数据获取失败: {e}")
        return None


def get_previous_trading_day(dt, days_back=1):
    count = 0
    while count < days_back:
        dt = dt - timedelta(days=1)
        if dt.weekday() < 5:
            count += 1
    return dt


def get_last_friday(dt):
    while dt.weekday() != 4:
        dt = dt - timedelta(days=1)
    return dt


# ═══════════════════ 新闻与事件 ═══════════════════
def get_gold_news():
    news_items = []
    try:
        q = quote("黄金 金价")
        xml_data = http_get(f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
        root = ET.fromstring(xml_data)
        for item in root.iter("item"):
            title = item.find("title")
            if title is not None and title.text:
                news_items.append({
                    "title": title.text,
                    "link": item.find("link").text if item.find("link") is not None else "",
                    "source": item.find("source").text if item.find("source") is not None else "",
                    "pub_date": item.find("pubDate").text if item.find("pubDate") is not None else "",
                })
            if len(news_items) >= 6:
                break
    except Exception as e:
        print(f"新闻获取失败: {e}")
    return news_items


def analyze_price_drivers(current_price, prev_close):
    if prev_close is None:
        return ["初始数据积累中，暂无对比分析"]
    change = (current_price - prev_close) / prev_close * 100
    direction = "上涨" if change >= 0 else "下跌"
    drivers = [f"📊 价格变动: {direction} {abs(change):.2f}%"]
    if change >= 0:
        drivers += [
            "🔍 可能推动金价上涨的因素：",
            "  • 美元走弱 / 美联储降息预期升温",
            "  • 地缘政治紧张局势升级",
            "  • 全球央行持续增持黄金储备",
            "  • 避险需求增加",
        ]
    else:
        drivers += [
            "🔍 可能推动金价下跌的因素：",
            "  • 美元走强 / 美联储鹰派表态",
            "  • 风险偏好回升，资金流向股市",
            "  • 美国国债收益率上升",
            "  • 地缘局势缓和，避险需求下降",
        ]
    return drivers


def get_event_calendar():
    return [
        {"date": "2026-07-01", "event": "美国ISM制造业PMI", "impact": "中", "gold_direction": "PMI弱于预期 → 金价↑", "probability": "40%"},
        {"date": "2026-07-02", "event": "美国6月非农就业报告", "impact": "🔴高", "gold_direction": "数据弱于预期 → 金价↑", "probability": "45%↑"},
        {"date": "2026-07-10", "event": "美国6月CPI通胀数据", "impact": "🔴高", "gold_direction": "通胀回落可能短期打压金价", "probability": "55%↑"},
        {"date": "2026-07-15", "event": "美联储褐皮书发布", "impact": "中", "gold_direction": "经济放缓 → 金价↑", "probability": "50%"},
        {"date": "2026-07-17", "event": "美国6月零售销售", "impact": "中", "gold_direction": "消费疲软 → 金价↑", "probability": "45%"},
        {"date": "2026-07-29", "event": "美联储FOMC利率决议", "impact": "🔴高", "gold_direction": "降息暗示 → 金价大涨", "probability": "60%↑"},
        {"date": "2026-07-30", "event": "美国Q2 GDP初值", "impact": "高", "gold_direction": "GDP低于预期 → 金价↑", "probability": "50%"},
        {"date": "2026-08-01", "event": "美国7月非农就业", "impact": "🔴高", "gold_direction": "数据弱于预期 → 金价↑", "probability": "45%↑"},
        {"date": "2026-08-12", "event": "美国7月CPI通胀", "impact": "🔴高", "gold_direction": "通胀数据影响降息节奏", "probability": "55%"},
        {"date": "2026-08-21", "event": "Jackson Hole全球央行年会", "impact": "🔴高", "gold_direction": "鲍威尔讲话 → 大幅波动", "probability": "60%"},
    ]


def get_upcoming_events():
    today = datetime.now()
    events = []
    for evt in get_event_calendar():
        d = datetime.strptime(evt["date"], "%Y-%m-%d")
        days = (d - today).days
        if 0 <= days <= 30:
            evt["days_away"] = days
            events.append(evt)
    return events


# ═══════════════════ 邮件构建 ═══════════════════
def build_email_html(prices, prev_close, last_friday_close, news_items, drivers, upcoming_events):
    now = datetime.now(timezone(timedelta(hours=8)))
    time_str = now.strftime("%Y-%m-%d %H:%M")

    day_change = (prices["price_cny_gram"] - prev_close) / prev_close * 100 if prev_close else None
    week_change = (prices["price_cny_gram"] - last_friday_close) / last_friday_close * 100 if last_friday_close else None

    def cc(v):
        if v is None: return "#888"
        return "#e74c3c" if v >= 0 else "#27ae60"

    def ci(v):
        if v is None: return "➖"
        return "📈" if v >= 0 else "📉"

    current_value = prices["price_cny_gram"] * GOLD_GRAMS
    profit = current_value - INVESTED_AMOUNT if INVESTED_AMOUNT > 0 else None

    # ---- 精简 HTML 构建 ----
    lines = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">',
        '<style>',
        'body{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f5f5f5;margin:0;padding:20px}',
        '.c{max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}',
        '.h{background:linear-gradient(135deg,#1a1a2e,#0f3460);color:#ffd700;padding:28px 24px;text-align:center}',
        '.h h1{margin:0;font-size:22px}',
        '.h .t{font-size:12px;color:#aaa;margin-top:8px}',
        '.ps{padding:24px;text-align:center;background:#fafafa;border-bottom:1px solid #eee}',
        '.cp{font-size:48px;font-weight:700;color:#1a1a2e;margin:0}',
        '.cp .u{font-size:16px;color:#888;font-weight:400}',
        '.si{font-size:12px;color:#999;margin-top:4px}',
        '.cmp{display:flex;justify-content:center;gap:40px;padding:20px 0 0}',
        '.ci{text-align:center}',
        '.cl{font-size:12px;color:#999;margin-bottom:4px}',
        '.cpr{font-size:18px;font-weight:600;color:#333}',
        '.ccg{font-size:13px;font-weight:600;margin-top:2px}',
        '.s{padding:20px 24px;border-bottom:1px solid #f0f0f0}',
        '.s:last-child{border-bottom:none}',
        '.st{font-size:15px;font-weight:700;color:#1a1a2e;margin:0 0 12px;padding-left:8px;border-left:3px solid #ffd700}',
        '.dl{list-style:none;padding:0;margin:0}',
        '.dl li{padding:4px 0;font-size:13px;color:#555;line-height:1.6}',
        '.ni{padding:10px 0;border-bottom:1px dashed #f0f0f0}',
        '.ni:last-child{border-bottom:none}',
        '.nt{font-size:13px;color:#333;line-height:1.5}',
        '.nt a{color:#1a5276;text-decoration:none}',
        '.ns{font-size:11px;color:#aaa;margin-top:2px}',
        '.et{width:100%;border-collapse:collapse;font-size:12px}',
        '.et th{background:#f8f8f8;padding:8px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #eee}',
        '.et td{padding:8px;border-bottom:1px solid #f5f5f5;color:#555;line-height:1.5}',
        '.hi{color:#e74c3c;font-weight:600}',
        '.pr{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}',
        '.pu{background:#fdecea;color:#e74c3c}',
        '.pd{background:#e8f8f0;color:#27ae60}',
        '.pn{background:#f5f5f5;color:#888}',
        '.ft{padding:16px 24px;background:#fafafa;text-align:center;font-size:11px;color:#bbb}',
        '.sb{background:linear-gradient(135deg,#fff9e6,#fff3cd);border:1px solid #ffe082;border-radius:8px;padding:14px 16px;margin-top:12px;font-size:13px;color:#856404;line-height:1.6}',
        '.hd{display:flex;justify-content:center;gap:30px;padding:8px 0 16px}',
        '.hv{font-size:16px;font-weight:600;color:#1a1a2e}',
        '.hl{font-size:11px;color:#999}',
        '</style></head><body><div class="c">',
        f'<div class="h"><h1>🥇 黄金价格智能监控报告</h1><div class="t">⏰ {time_str} (北京时间)</div></div>',
        f'<div class="ps"><p class="cp">¥{prices["price_cny_gram"]:.2f}<span class="u"> /克</span></p>',
        f'<p class="si">📡 {prices["source"]} | ${prices["price_usd_oz"]:.2f}/oz | 汇率: ¥{prices["usd_cny_rate"]:.2f}</p>',
    ]

    if GOLD_GRAMS > 0:
        lines.append(f'<div class="hd"><div class="ci"><div class="hv">{GOLD_GRAMS}g</div><div class="hl">持仓重量</div></div>')
        lines.append(f'<div class="ci"><div class="hv">¥{current_value:,.0f}</div><div class="hl">当前市值</div></div>')
        if profit is not None:
            pc = "#e74c3c" if profit >= 0 else "#27ae60"
            pi = "📈" if profit >= 0 else "📉"
            lines.append(f'<div class="ci"><div class="hv" style="color:{pc}">{pi} ¥{profit:,.0f}</div><div class="hl">浮动盈亏</div></div>')
        lines.append('</div>')

    if prev_close or last_friday_close:
        lines.append('<div class="cmp">')
        if prev_close:
            lines.append(f'<div class="ci"><div class="cl">📅 前日收盘</div><div class="cpr">¥{prev_close:.2f}</div><div class="ccg" style="color:{cc(day_change)}">{ci(day_change)} {day_change:+.2f}%</div></div>')
        if last_friday_close:
            lines.append(f'<div class="ci"><div class="cl">📅 上周五收盘</div><div class="cpr">¥{last_friday_close:.2f}</div><div class="ccg" style="color:{cc(week_change)}">{ci(week_change)} {week_change:+.2f}%</div></div>')
        lines.append('</div>')
    lines.append('</div>')

    # 涨跌因素
    lines.append('<div class="s"><p class="st">📊 涨跌主要影响因素</p><ul class="dl">')
    for d in drivers:
        lines.append(f'<li>{d}</li>')
    lines.append('</ul></div>')

    # 新闻
    if news_items and news_items[0].get("link"):
        lines.append('<div class="s"><p class="st">📰 最新相关资讯</p>')
        for n in news_items[:5]:
            src = f'{n["source"]} · {n["pub_date"]}' if n.get("source") else ""
            lines.append(f'<div class="ni"><div class="nt"><a href="{n["link"]}" target="_blank">{n["title"]}</a></div>')
            if src:
                lines.append(f'<div class="ns">{src}</div>')
            lines.append('</div>')
        lines.append('</div>')

    # 事件
    if upcoming_events:
        lines.append('<div class="s"><p class="st">🔮 未来重大事件</p>')
        lines.append('<table class="et"><tr><th>日期</th><th>事件</th><th>影响</th><th>金价走向</th><th>概率</th></tr>')
        for e in upcoming_events[:8]:
            pc = "pu" if "↑" in e["probability"] else ("pd" if "↓" in e["probability"] else "pn")
            ic = "hi" if "高" in e["impact"] else ""
            lines.append(f'<tr><td>{e["date"]} ({e["days_away"]}天后)</td><td>{e["event"]}</td><td class="{ic}">{e["impact"]}</td><td style="font-size:12px">{e["gold_direction"]}</td><td><span class="pr {pc}">{e["probability"]}</span></td></tr>')
        lines.append('</table>')
        lines.append('<div class="sb"><strong>📋 综合研判：</strong>重点关注 <strong>非农就业、CPI通胀、FOMC利率决议</strong> 三大核心数据。<br><br>⚠️ <em>以上分析仅供参考，不构成投资建议。</em></div>')
        lines.append('</div>')

    lines.append(f'<div class="ft">⚡ GitHub Actions 云端运行 | 每15分钟自动检测 | 完全免费<br>📧 黄金智能监控系统自动生成 · {time_str}</div>')
    lines.append('</div></body></html>')
    return "\n".join(lines)


# ═══════════════════ ★ 邮件发送 (curl) ★ ═══════════════════
def send_email(subject, html_body, recipients):
    api_key = EMAIL_CONFIG["resend_api_key"]
    if not api_key:
        print("❌ 未设置 RESEND_API_KEY")
        return False

    for to_email in recipients:
        payload = {
            "from": f'{EMAIL_CONFIG["sender_name"]} <{EMAIL_CONFIG["from_email"]}>',
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        fd, tmp_path = tempfile.mkstemp(suffix=".json", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False))

            result = subprocess.run([
                "curl", "-s", "-w", "\n%{http_code}",
                "-X", "POST", "https://api.resend.com/emails",
                "-H", f"Authorization: Bearer {api_key}",
                "-H", "Content-Type: application/json; charset=utf-8",
                "-d", f"@{tmp_path}",
                "--connect-timeout", "30", "--max-time", "60",
            ], capture_output=True, text=True, timeout=65)

            output = result.stdout.strip()
            parts = output.rsplit("\n", 1)
            http_code = parts[1].strip() if len(parts) == 2 else "0"
            resp_body = parts[0].strip() if len(parts) == 2 else output

            if http_code == "200":
                try:
                    rid = json.loads(resp_body).get("id", "N/A")
                    print(f"✅ 邮件已发送: {to_email} (ID: {rid})")
                except:
                    print(f"✅ 邮件已发送: {to_email}")
            else:
                print(f"❌ 发送失败 [{to_email}]: HTTP {http_code}")
                if result.stderr:
                    print(f"   stderr: {result.stderr.strip()}")
                if resp_body:
                    print(f"   body: {resp_body[:300]}")
        except subprocess.TimeoutExpired:
            print(f"❌ 超时 [{to_email}]")
        except Exception as e:
            print(f"❌ 发送异常 [{to_email}]: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    return True


# ═══════════════════ 主逻辑 ═══════════════════
def main():
    tz_cn = timezone(timedelta(hours=8))
    now = datetime.now(tz_cn)
    print(f"════════ 检测开始 {now.strftime('%Y-%m-%d %H:%M')} ════════")

    prices = get_current_gold_price()
    if not prices["success"]:
        print("❌ 无法获取金价")
        return

    print(f"💰 国际金价: ${prices['price_usd_oz']:.2f}/oz")
    print(f"💱 汇率: {prices['usd_cny_rate']:.4f}")
    print(f"🥇 人民币: ¥{prices['price_cny_gram']:.2f}/g")

    prev_day = get_previous_trading_day(now)
    lf = get_last_friday(now)

    prev_close_usd = get_historical_close(prev_day.strftime("%Y-%m-%d"))
    lf_close_usd = get_historical_close(lf.strftime("%Y-%m-%d"))

    rate = prices["usd_cny_rate"]
    prev_close = round(prev_close_usd * rate / 31.1035, 2) if prev_close_usd else None
    lf_close = round(lf_close_usd * rate / 31.1035, 2) if lf_close_usd else None

    if prev_close:
        print(f"📅 前日收盘({prev_day.strftime('%m-%d')}): ¥{prev_close}/g")
    if lf_close:
        print(f"📅 上周五收盘({lf.strftime('%m-%d')}): ¥{lf_close}/g")

    should_send = False
    reason = ""

    if now.hour == 18 and now.minute < 15:
        should_send = True
        reason = "⏰ 每日18:00定时报告"

    dca = abs((prices["price_cny_gram"] - prev_close) / prev_close * 100) if prev_close else 0
    wca = abs((prices["price_cny_gram"] - lf_close) / lf_close * 100) if lf_close else 0

    if dca >= DAILY_ALERT_PCT:
        should_send = True
        d = "📈急涨" if prev_close and prices["price_cny_gram"] >= prev_close else "📉急跌"
        reason += (", " if reason else "") + f"{d} 日波动{dca:.2f}% (>{DAILY_ALERT_PCT}%)"
    if wca >= WEEKLY_ALERT_PCT:
        should_send = True
        reason += (", " if reason else "") + f"周波动{wca:.2f}% (>{WEEKLY_ALERT_PCT}%)"
    if os.environ.get("FORCE_SEND", "").lower() == "true":
        should_send = True
        reason = reason or "🔧 手动触发"

    if should_send:
        print(f"📤 触发原因: {reason}")
        news = get_gold_news()
        drivers = analyze_price_drivers(prices["price_cny_gram"], prev_close)
        events = get_upcoming_events()
        html = build_email_html(prices, prev_close, lf_close, news, drivers, events)
        subj = f"🥇 黄金监控 {now.strftime('%Y-%m-%d')} — ¥{prices['price_cny_gram']:.2f}/g"
        if reason and reason != "🔧 手动触发":
            subj += f" | {reason}"
        send_email(subj, html, load_recipients())
    else:
        print(f"⏭️ 未触发 ({now.strftime('%H:%M')})")

    print("════════ 检测完成 ════════")


if __name__ == "__main__":
    main()
