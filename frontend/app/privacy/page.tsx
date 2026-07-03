import Link from 'next/link'

export const metadata = { title: 'Политика конфиденциальности — {{PROJECT_NAME}}' }

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

export default function PrivacyPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--fg-1)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px 80px' }}>
        <Link href="/" style={{ fontSize: 13, color: 'var(--fg-3)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 32 }}>
          ← {'{{PROJECT_NAME}}'}
        </Link>

        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Политика конфиденциальности</h1>
        <p style={{ color: 'var(--fg-3)', fontSize: 14, marginBottom: 40 }}>Редакция от 9 июня 2026 г.</p>

        <Section title="1. Оператор персональных данных">
          <p>Оператором персональных данных является сервис {'{{PROJECT_NAME}}'} (далее — «Сервис», «мы»). Контактный адрес: <a href="mailto:support@{{DOMAIN}}" style={{ color: 'var(--accent)' }}>{'support@{{DOMAIN}}'}</a>.</p>
        </Section>

        <Section title="2. Какие данные мы собираем">
          <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <li><strong>Учётные данные:</strong> адрес электронной почты, хеш пароля.</li>
            <li><strong>Данные об использовании:</strong> история действий в Сервисе, дата регистрации.</li>
            <li><strong>Технические данные:</strong> IP-адрес (только для защиты от злоупотреблений, не хранится постоянно).</li>
          </ul>
        </Section>

        <Section title="3. Цели обработки">
          <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <li>Предоставление функций Сервиса: регистрация, вход, работа с аккаунтом.</li>
            <li>Отправка транзакционных писем (подтверждение email, сброс пароля).</li>
            <li>Предотвращение злоупотреблений и обеспечение безопасности.</li>
          </ul>
        </Section>

        <Section title="4. Правовое основание">
          <p>Обработка осуществляется на основании согласия субъекта персональных данных (ст. 6 Федерального закона № 152-ФЗ «О персональных данных»). Согласие выражается при регистрации в Сервисе.</p>
        </Section>

        <Section title="5. Хранение и защита">
          <p>Данные хранятся на серверах в России. Пароли хранятся исключительно в виде хеша (bcrypt). Передача данных по сети осуществляется по протоколу HTTPS.</p>
          <p>Срок хранения данных аккаунта — до удаления аккаунта пользователем или по истечении 3 лет с последней активности.</p>
        </Section>

        <Section title="6. Передача третьим лицам">
          <p>Мы не продаём и не передаём персональные данные третьим лицам, за исключением случаев, предусмотренных законодательством РФ.</p>
        </Section>

        <Section title="7. Права пользователя">
          <p>В соответствии с ФЗ-152 вы вправе:</p>
          <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <li>Получить информацию об обработке ваших данных.</li>
            <li>Потребовать исправления неточных данных.</li>
            <li>Потребовать удаления данных (право на забвение).</li>
            <li>Отозвать согласие на обработку.</li>
          </ul>
          <p>Для реализации прав обратитесь на <a href="mailto:support@{{DOMAIN}}" style={{ color: 'var(--accent)' }}>{'support@{{DOMAIN}}'}</a>. Запрос будет рассмотрен в течение 30 дней.</p>
        </Section>

        <Section title="8. Файлы cookie">
          <p>Сервис использует только технически необходимую сессионную cookie для авторизации. Рекламные или аналитические cookie не используются.</p>
        </Section>

        <Section title="9. Изменения политики">
          <p>Мы можем обновлять настоящую Политику. При существенных изменениях уведомим по email. Продолжение использования Сервиса после изменений означает согласие с новой редакцией.</p>
        </Section>

        <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid var(--border-1)', display: 'flex', gap: 24, fontSize: 13 }}>
          <Link href="/terms" style={{ color: 'var(--accent)' }}>Пользовательское соглашение</Link>
          <Link href="/" style={{ color: 'var(--fg-3)' }}>На главную</Link>
        </div>
      </div>
    </div>
  )
}
