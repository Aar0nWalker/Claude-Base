import Link from 'next/link'

export const metadata = { title: 'Пользовательское соглашение — {{PROJECT_NAME}}' }

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 12 }}>{title}</h2>
      <div style={{ fontSize: 14.5, lineHeight: 1.7, color: 'var(--fg-2)', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {children}
      </div>
    </section>
  )
}

export default function TermsPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--fg-1)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px 80px' }}>
        <Link href="/" style={{ fontSize: 13, color: 'var(--fg-3)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 32 }}>
          ← {'{{PROJECT_NAME}}'}
        </Link>

        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Пользовательское соглашение</h1>
        <p style={{ color: 'var(--fg-3)', fontSize: 14, marginBottom: 40 }}>Редакция от 9 июня 2026 г.</p>

        <Section title="1. Общие положения">
          <p>Настоящее Пользовательское соглашение (далее — «Соглашение») регулирует использование сервиса {'{{PROJECT_NAME}}'} (далее — «Сервис»). Регистрируясь в Сервисе, вы принимаете условия настоящего Соглашения в полном объёме.</p>
          <p>Если вы не согласны с условиями, воздержитесь от использования Сервиса.</p>
        </Section>

        <Section title="2. Описание сервиса">
          <p>{'{{PROJECT_NAME}}'} — {'{{PROJECT_TAGLINE}}'}.</p>
        </Section>

        <Section title="3. Регистрация и аккаунт">
          <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <li>Для использования Сервиса необходима регистрация с подтверждением email.</li>
            <li>Вы обязаны хранить данные для входа в тайне и нести ответственность за действия, совершённые под вашим аккаунтом.</li>
            <li>Один пользователь — один аккаунт. Создание нескольких аккаунтов для обхода ограничений запрещено.</li>
          </ul>
        </Section>

        <Section title="4. Права на контент">
          <p>Контент, созданный или загруженный пользователем при использовании Сервиса, принадлежит пользователю.</p>
          <p>Сервис не претендует на права на результаты использования, однако оставляет за собой право использовать обезличенные данные для улучшения качества работы.</p>
        </Section>

        <Section title="5. Запрещённое использование">
          <p>При использовании Сервиса запрещается:</p>
          <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <li>Создавать контент, нарушающий законодательство РФ.</li>
            <li>Генерировать материалы сексуального, экстремистского или дискриминационного характера.</li>
            <li>Нарушать права интеллектуальной собственности третьих лиц.</li>
            <li>Использовать Сервис для автоматизированных атак, спама или иных злоупотреблений.</li>
            <li>Пытаться обойти технические ограничения Сервиса.</li>
          </ul>
          <p>Нарушение данных условий влечёт блокировку аккаунта.</p>
        </Section>

        <Section title="6. Ограничение ответственности">
          <p>Сервис предоставляется «как есть». Мы не гарантируем непрерывную работу и соответствие результатов вашим ожиданиям.</p>
          <p>Мы не несём ответственности за убытки, возникшие в результате использования или невозможности использования Сервиса, если иное не предусмотрено законодательством РФ.</p>
        </Section>

        <Section title="7. Изменение условий">
          <p>Мы вправе изменять настоящее Соглашение. При существенных изменениях уведомим по email не менее чем за 7 дней. Продолжение использования Сервиса после вступления изменений в силу означает их принятие.</p>
        </Section>

        <Section title="8. Применимое право">
          <p>Соглашение регулируется законодательством Российской Федерации. Споры разрешаются в судебном порядке по месту нахождения Сервиса.</p>
        </Section>

        <Section title="9. Контакты">
          <p>По вопросам, связанным с Соглашением, обращайтесь: <a href="mailto:support@{{DOMAIN}}" style={{ color: 'var(--accent)' }}>{'support@{{DOMAIN}}'}</a>.</p>
        </Section>

        <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid var(--border-1)', display: 'flex', gap: 24, fontSize: 13 }}>
          <Link href="/privacy" style={{ color: 'var(--accent)' }}>Политика конфиденциальности</Link>
          <Link href="/" style={{ color: 'var(--fg-3)' }}>На главную</Link>
        </div>
      </div>
    </div>
  )
}
