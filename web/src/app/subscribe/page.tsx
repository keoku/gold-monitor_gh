'use client'

import { useState } from 'react'
import Link from 'next/link'

type SubmitStatus = 'idle' | 'loading' | 'success' | 'error'
type TestStatus = 'idle' | 'loading' | 'success' | 'error'

export default function SubscribePage() {
  const [email, setEmail] = useState('')
  const [type] = useState<'general' | 'personal'>('general')
  const [status, setStatus] = useState<SubmitStatus>('idle')
  const [message, setMessage] = useState('')

  const [testStatus, setTestStatus] = useState<TestStatus>('idle')
  const [testMessage, setTestMessage] = useState('')
  const [testPrice, setTestPrice] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !email.includes('@')) {
      setStatus('error')
      setMessage('请输入有效的邮箱地址')
      return
    }

    setStatus('loading')

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, type }),
      })

      const data = await res.json()

      if (res.ok) {
        setStatus('success')
        setMessage(data.message || '订阅请求已提交！')
      } else {
        setStatus('error')
        setMessage(data.error || '提交失败，请稍后重试')
      }
    } catch {
      setStatus('error')
      setMessage('网络错误，请检查网络后重试')
    }
  }

  const handleTestReport = async () => {
    if (!email || !email.includes('@')) {
      setTestStatus('error')
      setTestMessage('请先输入有效的邮箱地址')
      return
    }

    setTestStatus('loading')
    setTestMessage('')
    setTestPrice('')

    try {
      const res = await fetch('/api/test-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, type }),
      })

      const data = await res.json()

      if (res.ok) {
        setTestStatus('success')
        setTestMessage(data.message || '测试报告已发送！')
        setTestPrice(data.price || '')
      } else {
        setTestStatus('error')
        setTestMessage(data.error || '发送失败')
      }
    } catch {
      setTestStatus('error')
      setTestMessage('网络错误，请检查网络后重试')
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-lg mx-auto px-6 py-16">
        <Link href="/" className="text-gray-400 hover:text-gray-600 text-sm">
          ← 返回首页
        </Link>

        <div className="mt-8 bg-white rounded-2xl p-8 shadow-lg border border-gray-100">
          <div className="text-center mb-8">
            <div className="text-5xl mb-4">📬</div>
            <h1 className="text-2xl font-bold text-gray-800">
              免费订阅金价报告
            </h1>
            <p className="text-gray-500 mt-2">
              填写邮箱即可每日收到黄金价格监控报告
            </p>
          </div>

          {status === 'success' ? (
            <div className="text-center py-6">
              <div className="text-5xl mb-4">✅</div>
              <h2 className="text-xl font-bold text-green-700 mb-2">
                订阅成功！
              </h2>
              <p className="text-gray-600">{message}</p>

              <div className="mt-6 p-5 bg-gradient-to-br from-yellow-50 to-orange-50 border border-yellow-200 rounded-xl">
                <p className="text-sm font-semibold text-gray-700 mb-3">
                  想立即看到金价报告效果？
                </p>

                {testStatus === 'success' ? (
                  <div className="space-y-2">
                    <div className="text-3xl">📧</div>
                    <p className="text-sm font-bold text-green-700">{testMessage}</p>
                    {testPrice && (
                      <p className="text-xs text-gray-500">
                        当前金价：{testPrice}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">
                      如果收件箱中没找到，请检查垃圾邮件文件夹。
                    </p>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={handleTestReport}
                      disabled={testStatus === 'loading'}
                      className="w-full py-3 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 disabled:from-yellow-300 disabled:to-orange-300 text-white font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                    >
                      {testStatus === 'loading' ? (
                        <>
                          <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          正在获取金价并发送...
                        </>
                      ) : (
                        '📨 立即发送一份测试报告到我的邮箱'
                      )}
                    </button>
                    {testStatus === 'error' && (
                      <p className="text-xs text-red-600 mt-2">{testMessage}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">
                      将获取实时金价并发送一封完整的金价监控报告到 <strong>{email}</strong>
                    </p>
                  </>
                )}
              </div>

              <p className="text-sm text-gray-400 mt-4">
                正式报告推送时间：每日 07:30、13:00、18:00（北京时间）
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  你的邮箱
                </label>
                <input
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (testStatus !== 'idle') {
                      setTestStatus('idle')
                      setTestMessage('')
                    }
                  }}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 outline-none text-lg"
                />
              </div>

              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">📊</span>
                  <span className="font-semibold text-gray-800">行情报告</span>
                </div>
                <p className="text-xs text-gray-500">
                  包含实时金价、涨跌分析、市场新闻、重大事件日历
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  💡 含持仓盈亏的完整报告仅适用于
                  <a href="/deploy" className="text-yellow-600 hover:underline">自建部署</a>
                  的用户
                </p>
              </div>

              {/* Test Report Section */}
              <div className="border-t border-gray-100 pt-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-gray-700">
                    先看看效果？
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleTestReport}
                  disabled={testStatus === 'loading'}
                  className="w-full py-3 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-400 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {testStatus === 'loading' ? (
                    <>
                      <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      正在获取金价并发送...
                    </>
                  ) : (
                    '📧 立即发送一份测试报告到邮箱'
                  )}
                </button>

                {testStatus === 'success' && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-700 font-semibold">{testMessage}</p>
                    {testPrice && (
                      <p className="text-xs text-green-600 mt-1">
                        当前金价: {testPrice}
                      </p>
                    )}
                    <p className="text-xs text-green-500 mt-1">
                      请检查邮箱（包括垃圾邮件文件夹）
                    </p>
                  </div>
                )}

                {testStatus === 'error' && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                    {testMessage}
                  </div>
                )}
              </div>

              {status === 'error' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full py-3.5 bg-yellow-500 hover:bg-yellow-400 disabled:bg-yellow-300 text-gray-900 font-bold rounded-xl text-lg transition-colors"
              >
                {status === 'loading' ? '提交中...' : '确认订阅'}
              </button>

              <p className="text-xs text-gray-400 text-center">
                提交后管理员会审核并添加你的邮箱，预计 24 小时内生效。
                <br />
                你的邮箱不会用于任何其他用途。
              </p>
            </form>
          )}
        </div>
      </div>
    </main>
  )
}
