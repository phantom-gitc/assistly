import { redirect } from 'react-router-dom'
import { api } from '../api/client'
import { store, signedIn, setRooms, setRoom, setMessages } from './store'

export async function requireUser({ request }) {
  const token = store.getState().session.token
  if (!token) throw redirect(`/login?next=${encodeURIComponent(new URL(request.url).pathname)}`)
  try { const user = await api('/auth/me', { token, signal: request.signal }); store.dispatch(signedIn({ token, user })); return user }
  catch (error) { if (error.name === 'AbortError') throw error; throw redirect('/login') }
}
export const roleRoute = (role, path) => async args => { const user = await requireUser(args); const allowed = role === 'customer' ? ['customer', 'visitor'].includes(user.role) : user.role === role || (role === 'agent' && user.role === 'admin'); if (!allowed) throw redirect(path); return user }
export async function loginAction({ request }) {
  const data = await request.formData(); const email = String(data.get('email') || '').trim(); const password = String(data.get('password') || '')
  try { const result = await api('/auth/login', { token: null, method: 'POST', body: JSON.stringify({ email, password }) }); sessionStorage.setItem('support_token', result.access_token); store.dispatch(signedIn({ token: result.access_token, user: result.user })); const next = new URL(request.url).searchParams.get('next'); const safeNext = next?.startsWith('/') && !next.startsWith('//') ? next : null; return redirect(safeNext || (result.user.role === 'admin' ? '/admin' : result.user.role === 'agent' ? '/inbox' : '/')) } catch (error) { return { error: error.message } }
}
export async function guestStartAction() {
  try {
    const result = await api('/chat/guest/rooms', { token: null, method: 'POST', body: JSON.stringify({}) })
    sessionStorage.setItem('support_token', result.access_token)
    store.dispatch(signedIn({ token: result.access_token, user: result.user }))
    return redirect(`/chat/${result.room.id}`)
  } catch (error) {
    return { error: error.message }
  }
}
export async function registerAction({ request }) {
  const data = await request.formData(); const username = String(data.get('username') || '').trim(); const email = String(data.get('email') || '').trim(); const password = String(data.get('password') || '')
  try { await api('/users/register', { token: null, method: 'POST', body: JSON.stringify({ username, email, password }) }); return redirect('/login?created=1') } catch (error) { return { error: error.message } }
}
export async function customerLoader(args) { const user = await roleRoute('customer', '/inbox')(args); const rooms = await api('/chat/rooms', { signal: args.request.signal }); store.dispatch(setRooms(rooms)); return { user, rooms } }
export async function customerChatLoader({ params, request }) { const options = { signal: request.signal }; const [room, messages] = await Promise.all([api(`/chat/rooms/${params.id}`, options), api(`/chat/rooms/${params.id}/messages`, options)]); store.dispatch(setRoom(room)); store.dispatch(setMessages(messages)); return { room, messages } }
export async function agentLoader(args) { const user = await roleRoute('agent', '/')(args); const rooms = await api(user.role === 'admin' ? '/admin/rooms' : '/chat/agent/rooms', { signal: args.request.signal }); store.dispatch(setRooms(rooms)); return { user, rooms } }
export async function agentChatLoader(args) { const user = await roleRoute('agent', '/')(args); const { id } = args.params; const roomsPath = user.role === 'admin' ? '/admin/rooms' : '/chat/agent/rooms'; const options = { signal: args.request.signal }; const [rooms, room, messages] = await Promise.all([api(roomsPath, options), api(`/chat/agent/rooms/${id}/status`, options), api(`/chat/agent/rooms/${id}/messages`, options)]); store.dispatch(setRooms(rooms)); store.dispatch(setRoom(room)); store.dispatch(setMessages(messages)); return { user, room, messages, rooms } }
export async function adminLoader(args) {
  const user = await roleRoute('admin', '/inbox')(args)
  const options = { signal: args.request.signal }
  const [rooms, agents] = await Promise.all([api('/admin/rooms', options), api('/admin/agents', options)])
  let documents = []
  let knowledgeError = ''
  try { documents = await api('/admin/knowledge/documents', options) }
  catch (error) { if (error.name === 'AbortError') throw error; knowledgeError = error.message }
  store.dispatch(setRooms(rooms))
  return { user, rooms, agents, documents, knowledgeError }
}
export async function adminAction({ request }) {
  const form = await request.formData()
  const intent = form.get('intent')
  let success = 'Changes saved.'
  try {
    if (intent === 'create-agent') {
      await api('/admin/agents', { method: 'POST', body: JSON.stringify({ username: form.get('username'), email: form.get('email'), password: form.get('password') }) })
    } else if (intent === 'toggle-agent') {
      await api(`/admin/agents/${form.get('id')}/${form.get('active') === 'true' ? 'deactivate' : 'activate'}`, { method: 'PUT' })
    } else if (intent === 'assign') {
      await api(`/admin/rooms/${form.get('room')}/assign/${form.get('agent')}`, { method: 'PUT' })
    } else if (intent === 'close') {
      await api(`/admin/rooms/${form.get('id')}/close`, { method: 'PUT' })
    } else if (intent === 'delete-room') {
      await api(`/admin/rooms/${form.get('id')}`, { method: 'DELETE' })
      success = 'Conversation and its message history deleted.'
    } else if (intent === 'upload-document') {
      const file = form.get('file')
      if (!(file instanceof File) || !file.size) return { error: 'Choose a document to upload.' }
      const upload = new FormData()
      upload.append('file', file, file.name)
      await api('/admin/knowledge/documents', { method: 'POST', body: upload })
      success = 'Document added to the AI knowledge library.'
    } else if (intent === 'delete-document') {
      await api(`/admin/knowledge/documents/${encodeURIComponent(form.get('id'))}`, { method: 'DELETE' })
      success = 'Document removed from the AI knowledge library.'
    }
    return { success }
  } catch (error) {
    return { error: error.message }
  }
}
