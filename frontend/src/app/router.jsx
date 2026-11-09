import { createBrowserRouter, Navigate } from 'react-router-dom'
import RouteError from '../components/RouteError'
import { loginAction, registerAction, guestStartAction, customerLoader, customerChatLoader, agentLoader, agentChatLoader, adminLoader, adminAction } from './loaders'
import { AuthPage } from '../features/auth/AuthPage'
import { GuestStartPage } from '../features/auth/GuestStartPage'
import { CustomerHome, CustomerShell, ChatPage } from '../features/customer/CustomerPages'
import { AgentHome, AgentChat } from '../features/agent/AgentPages'
import { AdminPage } from '../features/admin/AdminPage'

export const router = createBrowserRouter([
  { path: '/login', action: loginAction, element: <AuthPage />, errorElement: <RouteError /> },
  { path: '/register', action: registerAction, element: <AuthPage register />, errorElement: <RouteError /> },
  { path: '/guest', action: guestStartAction, element: <GuestStartPage />, errorElement: <RouteError /> },
  { id: 'customer-shell', element: <CustomerShell />, loader: customerLoader, errorElement: <RouteError />, children: [ { index: true, element: <CustomerHome /> }, { path: 'chat/:id', loader: customerChatLoader, element: <ChatPage /> } ] },
  { path: '/inbox', loader: agentLoader, element: <AgentHome />, errorElement: <RouteError /> },
  { path: '/inbox/:id', loader: agentChatLoader, element: <AgentChat />, errorElement: <RouteError /> },
  { path: '/admin', loader: adminLoader, action: adminAction, element: <AdminPage />, errorElement: <RouteError /> },
  { path: '*', element: <Navigate to="/" replace /> },
])
