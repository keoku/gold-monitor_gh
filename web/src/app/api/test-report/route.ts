import { NextRequest, NextResponse } from 'next/server'

// 内存速率限制：每个邮箱每小时最多 5 次，全局每分钟最多 10 次
const emailRateMap = new Map<string, number[]>()
const globalRequests: number[] = []
const PER_EMAIL_LIMIT = 5
const PER_EMAIL_WINDOW_MS = 60 * 60 * 1000  // 1 小时
const GLOBAL_LIMIT = 10
const GLOBAL_WINDOW_MS = 60 * 1000           // 1 分钟

function checkRateLimit(email: string): string | null {
  const now = Date.now()

  // 全局限流
  while (globalRequests.length > 0 && now - globalRequests[0] > GLOBAL_WINDOW_MS) {
    globalRequests.shift()
  }
  if (globalRequests.length >= GLOBAL_LIMIT) {
    return '请求过于频繁，请 1 分钟后再试'
  }

  // 单邮箱限流
  const key = email.toLowerCase().trim()
  const timestamps = emailRateMap.get(key) ?? []
  const filtered = timestamps.filter(t => now - t < PER_EMAIL_WINDOW_MS)
  if (filtered.length >= PER_EMAIL_LIMIT) {
    return '该邮箱 1 小时内最多发送 5 次测试报告，请稍后再试'
  }

  filtered.push(now)
  emailRateMap.set(key, filtered)
  globalRequests.push(now)
  return null
}

interface GoldPrices {
  price_cny_gram: number
  price_usd_oz: number
  usd_cny_rate: number
  source: string
}

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 GoldMonitor/1.0' },
    signal: AbortSignal.timeout(15000),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function getGoldPrice(): Promise<GoldPrices | null> {
  let priceUsdOz: number | null = null
  let source = ''

  // Swissquote (国内可直接访问)
  try {
    const data = (await fetchJson(
      'https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD'
    )) as Array<{
      spreadProfilePrices: Array<{ bid: number; ask: number }>
    }>
    if (data?.[0]?.spreadProfilePrices?.[0]) {
      const { bid, ask } = data[0].spreadProfilePrices[0]
      priceUsdOz = (bid + ask) / 2
      source = 'Swissquote'
    }
  } catch { /* fallback */ }

  // metals.live
  if (!priceUsdOz) {
    try {
      const data = (await fetchJson('https://api.metals.live/v1/spot/gold')) as Array<{ price: string }>
      if (data.length > 0) {
        priceUsdOz = parseFloat(data[0].price)
        source = 'metals.live'
      }
    } catch { /* fallback */ }
  }

  // goldprice.org
  if (!priceUsdOz) {
    try {
      const data = (await fetchJson('https://data-asg.goldprice.org/dbXRates/USD')) as {
        items?: Array<{ xauPrice?: number }>
      }
      if (data.items?.[0]?.xauPrice) {
        priceUsdOz = data.items[0].xauPrice
        source = 'goldprice.org'
      }
    } catch { /* fallback */ }
  }

  if (!priceUsdOz) return null

  // USD → CNY (多数据源)
  let usdCnyRate = 7.25
  try {
    const data = (await fetchJson('https://api.exchangerate-api.com/v4/latest/USD')) as {
      rates: { CNY: number }
    }
    usdCnyRate = data.rates.CNY
  } catch {
    try {
      const data = (await fetchJson('https://api.frankfurter.app/latest?from=USD&to=CNY')) as {
        rates: { CNY: number }
      }
      usdCnyRate = data.rates.CNY
    } catch { /* use fallback */ }
  }

  return {
    price_cny_gram: Math.round((priceUsdOz * usdCnyRate) / 31.1035 * 100) / 100,
    price_usd_oz: Math.round(priceUsdOz * 100) / 100,
    usd_cny_rate: Math.round(usdCnyRate * 10000) / 10000,
    source,
  }
}

function buildTestEmailHtml(prices: GoldPrices): string {
  const now = new Date()
  const timeStr = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f5f5; margin:0; padding:20px; }
  .container { max-width:640px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,.08); }
  .header { background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460); color:#ffd700; padding:28px 24px; text-align:center; }
  .header h1 { margin:0; font-size:22px; letter-spacing:2px; }
  .header .time { font-size:12px; color:#aaa; margin-top:8px; }
  .price-section { padding:24px; text-align:center; background:#fafafa; border-bottom:1px solid #eee; }
  .current-price { font-size:48px; font-weight:700; color:#1a1a2e; margin:0; }
  .current-price .unit { font-size:16px; color:#888; font-weight:400; }
  .sub-info { font-size:12px; color:#999; margin-top:4px; }
  .section { padding:20px 24px; border-bottom:1px solid #f0f0f0; }
  .section-title { font-size:15px; font-weight:700; color:#1a1a2e; margin:0 0 12px; padding-left:8px; border-left:3px solid #ffd700; }
  .test-note { background:linear-gradient(135deg,#e8f8f0,#d4edda); border:1px solid #c3e6cb; border-radius:8px; padding:14px 16px; margin-top:12px; font-size:13px; color:#155724; line-height:1.6; text-align:center; }
  .footer { padding:16px 24px; background:#fafafa; text-align:center; font-size:11px; color:#bbb; }
</style></head><body>
<div class="container">
<div class="header">
  <h1>🥇 黄金价格智能监控报告</h1>
  <div class="time">⏰ ${timeStr} (北京时间)</div>
</div>

<div class="price-section">
  <p class="current-price">¥${prices.price_cny_gram.toFixed(2)}<span class="unit"> /克</span></p>
  <p class="sub-info">📡 ${prices.source} | 国际: $${prices.price_usd_oz.toFixed(2)}/oz | 汇率: ¥${prices.usd_cny_rate.toFixed(2)}</p>
</div>

<div class="section">
  <p class="section-title">📊 实时金价概览</p>
  <table style="width:100%;font-size:13px;color:#555;">
    <tr><td style="padding:6px 0;">🌍 国际金价 (USD/oz)</td><td style="text-align:right;font-weight:600;">$${prices.price_usd_oz.toFixed(2)}</td></tr>
    <tr><td style="padding:6px 0;">💱 美元兑人民币汇率</td><td style="text-align:right;font-weight:600;">¥${prices.usd_cny_rate.toFixed(4)}</td></tr>
    <tr><td style="padding:6px 0;">🥇 人民币克价</td><td style="text-align:right;font-weight:600;color:#1a1a2e;font-size:16px;">¥${prices.price_cny_gram.toFixed(2)}/g</td></tr>
  </table>
</div>

<div class="section">
  <div class="test-note">
    ✅ <strong>测试邮件发送成功！</strong><br>
    这是一封测试报告，确认你的邮箱可以正常接收金价监控邮件。<br>
    正式报告将包含更多内容：涨跌分析、新闻资讯、重大事件日历等。<br><br>
    📅 正式报告推送时间：每日 07:30、13:00、18:00（北京时间）
  </div>
</div>

<div class="footer">
  ⚡ 黄金价格智能监控系统 · 测试报告<br>
  📧 ${timeStr}
</div>
</div>
</body></html>`
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email } = body

    if (!email || !email.includes('@')) {
      return NextResponse.json({ error: '请提供有效的邮箱地址' }, { status: 400 })
    }

    const rateLimitError = checkRateLimit(email)
    if (rateLimitError) {
      return NextResponse.json({ error: rateLimitError }, { status: 429 })
    }

    const resendApiKey = process.env.RESEND_API_KEY
    if (!resendApiKey) {
      return NextResponse.json(
        { error: '服务端未配置邮件发送密钥 (RESEND_API_KEY)，无法发送测试报告' },
        { status: 500 }
      )
    }

    const prices = await getGoldPrice()
    if (!prices) {
      return NextResponse.json({ error: '金价数据获取失败，请稍后重试' }, { status: 502 })
    }

    const senderName = process.env.SENDER_NAME || '黄金智能监控'
    const fromEmail = process.env.FROM_EMAIL || 'onboarding@resend.dev'
    const html = buildTestEmailHtml(prices)
    const subject = `🥇 黄金监控 — 测试报告 ¥${prices.price_cny_gram.toFixed(2)}/g`

    const resendRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: `${senderName} <${fromEmail}>`,
        to: [email],
        subject,
        html,
      }),
    })

    if (!resendRes.ok) {
      const errText = await resendRes.text()
      console.error('Resend API error:', errText)
      return NextResponse.json(
        { error: '邮件发送失败，请确认邮箱地址正确后重试' },
        { status: 502 }
      )
    }

    const resendData = await resendRes.json()

    return NextResponse.json({
      message: '测试报告已发送！请检查你的收件箱（包括垃圾邮件文件夹）。',
      price: `¥${prices.price_cny_gram.toFixed(2)}/g`,
      emailId: resendData.id,
    })
  } catch (error) {
    console.error('Test report error:', error)
    return NextResponse.json({ error: '服务器错误，请稍后重试' }, { status: 500 })
  }
}
