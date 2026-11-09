import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, CircleHelp, Headphones, LogOut } from 'lucide-react'
import { store, signedOut } from '../app/store'

export function Mark({ small = false }) { return <span className={`brand-mark ${small ? 'brand-mark-small' : ''}`}><Headphones size={small ? 17 : 19} strokeWidth={2.4}/></span> }
export function Brand() { return <Link to="/" className="brand"><Mark/><span>assistly<span className="brand-light">.support</span></span></Link> }
export function Avatar({ name = 'Guest', size = '' }) { return <span className={`avatar ${size}`} aria-label={name}>{name.slice(0, 1).toUpperCase()}</span> }
export function Header({ user, eyebrow = 'CUSTOMER SUPPORT', side }) { const [menu, setMenu] = useState(false); return <header className="topbar"><Brand/><span className="topbar-label"><span className="online-indicator"/> {eyebrow}</span><div className="topbar-right">{side}<div className="profile-wrap"><button type="button" className="profile-button" aria-label="Account menu" onClick={() => setMenu(!menu)}><Avatar name={user?.username}/><ChevronDown size={14}/></button>{menu && <button className="profile-menu" onClick={() => { sessionStorage.removeItem('support_token'); store.dispatch(signedOut()); window.location.assign('/login') }}><LogOut size={15}/> Sign out</button>}</div></div></header> }
export function PageError({ error }) { const message = typeof error === 'string' ? error : error ? 'Something went wrong. Please try again.' : ''; return message && <div className="inline-error" role="alert"><CircleHelp size={15}/>{message}</div> }
export function Field({ label, ...props }) { return <label className="field"><span className="field-label">{label}</span><input className="text-input" {...props}/></label> }
