import { ArrowRight, Headphones, LoaderCircle, MessageCircle } from 'lucide-react'
import { Form, Link, useActionData, useNavigation } from 'react-router-dom'
import { Brand, PageError } from '../../components/shared'

export function GuestStartPage() {
  const action = useActionData()
  const navigation = useNavigation()
  const busy = navigation.state === 'submitting'

  return (
    <div className="auth-page">
      <div className="auth-brand"><Brand/><span className="auth-trust"><Headphones size={14}/> A little more human</span></div>
      <main className="auth-card guest-card">
        <div className="auth-icon"><MessageCircle size={22}/></div>
        <div className="section-eyebrow">QUICK SUPPORT</div>
        <h1>How can we help?</h1>
        <p className="auth-subtitle">Start a private support conversation without creating an account.</p>
        <PageError error={action?.error}/>
        <Form method="post" className="guest-start-form">
          <button className="button button-primary auth-submit" type="submit" disabled={busy}>
            {busy ? <LoaderCircle className="spin" size={16}/> : <MessageCircle size={16}/>}
            {busy ? 'Preparing your chat…' : 'Start chatting'}
            {!busy && <ArrowRight size={16}/>}
          </button>
        </Form>
        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </main>
    </div>
  )
}
