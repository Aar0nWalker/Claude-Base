'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import Icon from '@/components/icon'
import '@/styles/landing.css'

const FEATURES = [
  { icon: 'zap', title: 'Быстрый старт', desc: 'Зарегистрируйся и начни работать за пару минут — без лишних настроек.' },
  { icon: 'shield', title: 'Надёжно', desc: 'Данные защищены, доступ — только у тебя. Прозрачная работа с аккаунтом.' },
  { icon: 'sliders-horizontal', title: 'Гибко', desc: 'Настраивай под себя — платформа растёт вместе с задачами.' },
]

const STEPS = [
  { n: 1, title: 'Регистрация', desc: 'Создай аккаунт и подтверди email.' },
  { n: 2, title: 'Настройка', desc: 'Заполни профиль и настрой рабочее пространство.' },
  { n: 3, title: 'Работа', desc: 'Начни пользоваться сервисом прямо из дашборда.' },
]

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [showTop, setShowTop] = useState(false)

  useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > 480)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <header className="hdr">
        <div className="wrap hdr-in">
          <Link href="/" className="brand">{'{{PROJECT_NAME}}'}</Link>
          <nav className="nav">
            <a href="#features">Возможности</a>
            <a href="#how-it-works">Как это работает</a>
          </nav>
          <div className="hdr-cta">
            <Link href="/login" className="login">Войти</Link>
            <Link href="/register" className="btn btn-grad">Начать бесплатно</Link>
          </div>
          <button type="button" className="burger" aria-label="Меню" onClick={() => setMenuOpen(v => !v)}>
            <Icon name={menuOpen ? 'x' : 'menu'} className="ic" />
          </button>
        </div>
        {menuOpen && (
          <>
            <div className="m-menu-overlay" onClick={() => setMenuOpen(false)} />
            <div className="m-menu">
              <a href="#features" onClick={() => setMenuOpen(false)}>Возможности</a>
              <a href="#how-it-works" onClick={() => setMenuOpen(false)}>Как это работает</a>
              <div className="m-menu-sep" />
              <Link href="/login" className="m-menu-login" onClick={() => setMenuOpen(false)}>Войти</Link>
              <Link href="/register" className="btn btn-grad m-menu-cta" onClick={() => setMenuOpen(false)}>Начать бесплатно</Link>
            </div>
          </>
        )}
      </header>

      <section className="hero">
        <div className="hero-glow" />
        <div className="wrap hero-lead">
          <span className="eyebrow"><Icon name="sparkles" className="ic" style={{ width: 14, height: 14 }} />{'{{PROJECT_NAME}}'}</span>
          <h1 className="hero-lead-h">{'{{PROJECT_TAGLINE}}'}</h1>
          <p className="sub">Стартуй с готовой платформой: аккаунты, авторизация и панель управления уже настроены — сосредоточься на своей задаче.</p>
          <div className="hero-cta">
            <Link href="/register" className="btn btn-grad btn-lg">
              Начать бесплатно
              <Icon name="arrow-right" className="ic" />
            </Link>
            <Link href="/login" className="btn btn-ghost btn-lg">Войти</Link>
          </div>
          <ul className="hero-points">
            <li><Icon name="check" className="ic" />Без сложной настройки</li>
            <li><Icon name="check" className="ic" />Готовая авторизация</li>
            <li><Icon name="check" className="ic" />Админ-панель из коробки</li>
          </ul>
        </div>
      </section>

      <section className="section" id="features">
        <div className="wrap">
          <div className="sec-head">
            <span className="sec-eyebrow">Возможности</span>
            <h2>Всё нужное для старта</h2>
            <p>Базовый набор, который есть в любом SaaS-продукте — уже готов.</p>
          </div>
          <div className="feat-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="feat">
                <div className="fi"><Icon name={f.icon} className="ic" /></div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="how-it-works">
        <div className="wrap">
          <div className="sec-head">
            <span className="sec-eyebrow">Как это работает</span>
            <h2>Три шага до старта</h2>
          </div>
          <div className="steps">
            {STEPS.map(s => (
              <div key={s.n} className="step">
                <div className="sn">{s.n}</div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="cta-final">
        <div className="wrap cta-final-in">
          <h2>Готовы начать?</h2>
          <p>Зарегистрируйся и получи доступ прямо сейчас.</p>
          <Link href="/register" className="btn btn-grad btn-lg">
            Создать аккаунт
            <Icon name="arrow-right" className="ic" />
          </Link>
        </div>
      </section>

      <footer className="ftr">
        <div className="wrap ftr-in">
          <div>
            <Link href="/" className="brand">{'{{PROJECT_NAME}}'}</Link>
            <p className="ftr-tag">{'{{PROJECT_TAGLINE}}'}</p>
          </div>
          <div className="ftr-legal">
            <Link href="/privacy">Конфиденциальность</Link>
            <Link href="/terms">Соглашение</Link>
          </div>
        </div>
        <div className="wrap ftr-bottom">
          <span>© {new Date().getFullYear()} {'{{PROJECT_NAME}}'}</span>
        </div>
      </footer>

      <button
        type="button"
        className={`to-top${showTop ? ' show' : ''}`}
        aria-label="Наверх"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      >
        <Icon name="arrow-up" className="ic" />
      </button>
    </>
  )
}
