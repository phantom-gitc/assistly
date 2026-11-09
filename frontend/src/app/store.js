import { configureStore, createSlice } from '@reduxjs/toolkit'

const sessionSlice = createSlice({ name: 'session', initialState: { token: sessionStorage.getItem('support_token'), user: null }, reducers: { signedIn(s, a) { s.token = a.payload.token; s.user = a.payload.user }, signedOut(s) { s.token = null; s.user = null } } })
const chatSlice = createSlice({ name: 'chat', initialState: { rooms: [], messages: [], activeRoom: null }, reducers: { setRooms(s, a) { s.rooms = a.payload }, setMessages(s, a) { s.messages = a.payload }, setRoom(s, a) { s.activeRoom = a.payload }, appendMessage(s, a) { if (!s.messages.some(x => x.id != null && x.id === a.payload.id)) s.messages.push(a.payload) } } })
export const store = configureStore({ reducer: { session: sessionSlice.reducer, chat: chatSlice.reducer } })
export const { signedIn, signedOut } = sessionSlice.actions
export const { setRooms, setMessages, setRoom, appendMessage } = chatSlice.actions
