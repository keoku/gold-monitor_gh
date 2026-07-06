import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email } = body

    if (!email || !email.includes('@')) {
      return NextResponse.json(
        { error: '请提供有效的邮箱地址' },
        { status: 400 }
      )
    }

    const safeType = 'general'

    const githubToken = process.env.GITHUB_TOKEN
    const repoOwner = process.env.REPO_OWNER || 'ygh-wq'
    const repoName = process.env.REPO_NAME || 'gold-monitor_gh'

    if (githubToken) {
      const issueTitle = `[订阅请求] ${email}`
      const issueBody = [
        `## 新订阅请求`,
        '',
        `- **邮箱**: ${email}`,
        `- **类型**: ${safeType === 'personal' ? '完整报告（含持仓）' : '行情报告'}`,
        `- **时间**: ${new Date().toISOString()}`,
        '',
        '---',
        '',
        '请将此邮箱添加到 `recipients.json` 对应分组中，然后关闭此 Issue。',
      ].join('\n')

      const res = await fetch(
        `https://api.github.com/repos/${repoOwner}/${repoName}/issues`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${githubToken}`,
            Accept: 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: issueTitle,
            body: issueBody,
            labels: ['subscription'],
          }),
        }
      )

      if (!res.ok) {
        console.error('GitHub API error:', await res.text())
        return NextResponse.json(
          { error: '提交失败，请稍后重试' },
          { status: 500 }
        )
      }
    }

    return NextResponse.json({
      message: '订阅请求已提交！管理员会在 24 小时内处理，届时你将收到金价报告邮件。',
    })
  } catch (error) {
    console.error('Subscribe error:', error)
    return NextResponse.json(
      { error: '服务器错误，请稍后重试' },
      { status: 500 }
    )
  }
}
