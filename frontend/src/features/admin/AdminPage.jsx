import { useEffect, useRef, useState } from 'react'
import { Form, Link, useActionData, useLoaderData, useNavigation } from 'react-router-dom'
import {
  Activity, ArrowRight, BadgeCheck, Bot, Check, FileText, Headphones,
  LoaderCircle, MessageCircle, MessageSquare, Plus, ShieldCheck, Trash2,
  Upload, Users, X,
} from 'lucide-react'
import { Avatar, Field, Header, PageError } from '../../components/shared'
import { formatDate } from '../../utils/date'

export function AdminPage() {
  const { user, rooms, agents, documents, knowledgeError } = useLoaderData()
  const result = useActionData()
  const navigation = useNavigation()
  const uploadForm = useRef(null)
  const [tab, setTab] = useState('overview')
  const [agentForm, setAgentForm] = useState(false)
  const open = rooms.filter(room => room.status === 'open').length
  const assigned = rooms.filter(room => room.assigned_agent_id).length
  const uploading = navigation.state === 'submitting'
    && navigation.formData?.get('intent') === 'upload-document'

  useEffect(() => {
    if (result?.success === 'Document added to the AI knowledge library.') {
      uploadForm.current?.reset()
    }
  }, [result])

  return (
    <div className="staff-frame">
      <Header
        user={user}
        eyebrow="ADMINISTRATION"
        side={<Link to="/inbox" className="toolbar-button"><MessageSquare size={15}/> Agent inbox</Link>}
      />
      <main className="staff-content">
        <div className="staff-title">
          <div>
            <div className="section-eyebrow"><ShieldCheck size={13}/> WORKSPACE MANAGEMENT</div>
            <h1>Overview<span>.</span></h1>
            <p>Keep your team and conversations moving together.</p>
          </div>
          <span className="admin-badge"><ShieldCheck size={14}/> Admin access</span>
        </div>

        <div className="stat-grid">
          <Stat icon={<MessageSquare size={17}/>} label="Total conversations" value={rooms.length} color="lavender"/>
          <Stat icon={<Activity size={17}/>} label="Open right now" value={open} color="mint"/>
          <Stat icon={<Users size={17}/>} label="Support team" value={agents.length} color="peach"/>
          <Stat icon={<BadgeCheck size={17}/>} label="Assigned" value={assigned} color="blue"/>
        </div>

        <PageError error={result?.error}/>
        {result?.success && <p className="success-note"><Check size={15}/>{result.success}</p>}

        <div className="admin-tabs" role="tablist" aria-label="Admin sections">
          <button type="button" role="tab" aria-selected={tab === 'overview'} className={tab === 'overview' ? 'admin-tab-active' : 'admin-tab'} onClick={() => setTab('overview')}>
            <MessageCircle size={15}/> Conversations <span>{rooms.length}</span>
          </button>
          <button type="button" role="tab" aria-selected={tab === 'agents'} className={tab === 'agents' ? 'admin-tab-active' : 'admin-tab'} onClick={() => setTab('agents')}>
            <Users size={15}/> Agents <span>{agents.length}</span>
          </button>
          <button type="button" role="tab" aria-selected={tab === 'knowledge'} className={tab === 'knowledge' ? 'admin-tab-active' : 'admin-tab'} onClick={() => setTab('knowledge')}>
            <FileText size={15}/> Knowledge <span>{documents.length}</span>
          </button>
        </div>

        {tab === 'overview' && <ConversationPanel rooms={rooms} agents={agents}/>}
        {tab === 'agents' && (
          <AgentPanel agents={agents} agentForm={agentForm} setAgentForm={setAgentForm}/>
        )}
        {tab === 'knowledge' && (
          <KnowledgePanel
            documents={documents}
            error={knowledgeError}
            uploadForm={uploadForm}
            uploading={uploading}
          />
        )}
      </main>
    </div>
  )
}

function ConversationPanel({ rooms, agents }) {
  return (
    <section className="admin-panel">
      <div className="panel-header">
        <div><h2>All conversations</h2><p>Assign conversations and keep track of what needs attention.</p></div>
      </div>
      {rooms.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Conversation</th><th>Status</th><th>Mode</th><th>Assigned agent</th><th>Started</th><th/></tr></thead>
            <tbody>{rooms.map(room => (
              <tr key={room.id}>
                <td><span className="table-name">{room.room_name}</span><span className="table-id">Conversation #{room.id}</span></td>
                <td><span className={`status-pill ${room.status === 'closed' ? 'status-muted' : ''}`}><span/>{room.status}</span></td>
                <td><span className="mode-tag">{room.chat_mode === 'bot' ? <Bot size={13}/> : <Headphones size={13}/>} {room.chat_mode === 'bot' ? 'AI assisted' : 'Human'}</span></td>
                <td>{room.status === 'closed' ? <span className="table-id">—</span> : (
                  <Form method="post">
                    <input type="hidden" name="intent" value="assign"/>
                    <input type="hidden" name="room" value={room.id}/>
                    <select name="agent" aria-label={`Assign conversation ${room.id}`} defaultValue={room.assigned_agent_id || ''} onChange={event => event.currentTarget.form.requestSubmit()} required>
                      <option value="" disabled>Choose an agent</option>
                      {agents.filter(agent => agent.is_active).map(agent => <option key={agent.id} value={agent.id}>{agent.username}</option>)}
                    </select>
                  </Form>
                )}</td>
                <td className="table-date">{formatDate(room.created_at)}</td>
                <td className="conversation-actions">{room.status === 'open' && (
                  <Form method="post">
                    <input type="hidden" name="intent" value="close"/>
                    <input type="hidden" name="id" value={room.id}/>
                    <button className="close-action" aria-label={`Close conversation ${room.id}`} title="Close conversation"><X size={15}/></button>
                  </Form>
                )}
                  <Form method="post" onSubmit={event => { if (!window.confirm(`Permanently delete conversation ${room.id} and its message history?`)) event.preventDefault() }}>
                    <input type="hidden" name="intent" value="delete-room"/>
                    <input type="hidden" name="id" value={room.id}/>
                    <button className="delete-action" aria-label={`Delete conversation ${room.id}`} title="Delete conversation"><Trash2 size={15}/></button>
                  </Form>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : <Empty icon={<MessageCircle/>} title="No conversations yet" detail="New customer conversations will appear here."/>}
    </section>
  )
}

function AgentPanel({ agents, agentForm, setAgentForm }) {
  return (
    <section className="admin-panel">
      <div className="panel-header">
        <div><h2>Your support team</h2><p>Manage access and invite a support agent.</p></div>
        <button type="button" className="button button-primary" onClick={() => setAgentForm(!agentForm)}>
          {agentForm ? <X size={15}/> : <Plus size={15}/>} {agentForm ? 'Cancel' : 'Add agent'}
        </button>
      </div>
      {agentForm && (
        <Form method="post" className="create-agent-form" onSubmit={() => setAgentForm(false)}>
          <input type="hidden" name="intent" value="create-agent"/>
          <Field label="Username" name="username" placeholder="agent_name" minLength="3" required/>
          <Field label="Email" name="email" type="email" placeholder="agent@example.com" required/>
          <Field label="Temporary password" name="password" type="password" placeholder="At least 8 characters" minLength="8" required/>
          <button className="button button-primary create-agent-submit">Create agent <ArrowRight size={15}/></button>
        </Form>
      )}
      <div className="agent-list">
        {agents.map(agent => (
          <div className="agent-row" key={agent.id}>
            <Avatar name={agent.username}/>
            <span className="agent-info"><strong>{agent.username}</strong><span>{agent.email} · Agent #{agent.id}</span></span>
            <span className={`status-pill ${agent.is_active ? '' : 'status-muted'}`}><span/>{agent.is_active ? 'Active' : 'Inactive'}</span>
            <Form method="post">
              <input type="hidden" name="intent" value="toggle-agent"/>
              <input type="hidden" name="id" value={agent.id}/>
              <input type="hidden" name="active" value={String(agent.is_active)}/>
              <button className="button button-outline">{agent.is_active ? 'Deactivate' : 'Reactivate'}</button>
            </Form>
          </div>
        ))}
        {!agents.length && <Empty icon={<Users/>} title="Your team starts here" detail="Add an agent so customers can talk to a real person."/>}
      </div>
    </section>
  )
}

function KnowledgePanel({ documents, error, uploadForm, uploading }) {
  return (
    <section className="admin-panel knowledge-panel">
      <div className="panel-header">
        <div><h2>AI knowledge library</h2><p>Upload company policies and guides. Assistly will use them to answer customer questions.</p></div>
      </div>
      <div className="knowledge-content">
        <Form ref={uploadForm} method="post" encType="multipart/form-data" className="knowledge-upload">
          <input type="hidden" name="intent" value="upload-document"/>
          <label className="knowledge-file-label" htmlFor="knowledge-file">
            <span className="knowledge-file-icon"><Upload size={18}/></span>
            <span><strong>Choose a company document</strong><small>PDF, TXT, or Markdown · up to 10 MB</small></span>
            <input id="knowledge-file" name="file" type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" required/>
          </label>
          <button className="button button-primary" type="submit" disabled={uploading}>
            {uploading ? <><LoaderCircle size={15} className="spin"/> Reading and indexing…</> : <><Upload size={15}/> Upload to knowledge base</>}
          </button>
        </Form>
        {error && <PageError error={error}/>}
        <div className="knowledge-note"><Bot size={15}/><span>Upload only information customers are allowed to receive. Assistly stores extracted text in PostgreSQL and searchable vectors in Qdrant; original files are not retained.</span></div>
        <div className="knowledge-list-heading"><h3>Indexed documents</h3><span>{documents.length} {documents.length === 1 ? 'document' : 'documents'}</span></div>
        {error ? (
          <Empty icon={<FileText/>} title="Knowledge library unavailable" detail="Refresh the page and try again in a moment."/>
        ) : documents.length ? (
          <div className="document-list">
            {documents.map(document => (
              <div className="document-row" key={document.id}>
                <span className="document-icon"><FileText size={17}/></span>
                <span className="document-details">
                  <strong>{document.filename}</strong>
                  <small>{document.chunks} searchable {document.chunks === 1 ? 'section' : 'sections'} · Added {formatDate(document.uploaded_at)}</small>
                </span>
                <Form method="post">
                  <input type="hidden" name="intent" value="delete-document"/>
                  <input type="hidden" name="id" value={document.id}/>
                  <button className="document-delete" type="submit" aria-label={`Remove ${document.filename}`} title="Remove document"><Trash2 size={16}/></button>
                </Form>
              </div>
            ))}
          </div>
        ) : <Empty icon={<FileText/>} title="No documents indexed yet" detail="Upload a company guide or policy to give the AI answers grounded in your information."/>}
      </div>
    </section>
  )
}

function Empty({ icon, title, detail }) {
  return <div className="staff-empty"><span className="empty-icon">{icon}</span><strong>{title}</strong><span>{detail}</span></div>
}

export function Stat({ icon, label, value, color }) {
  return <div className="stat-card"><span className={`stat-icon stat-${color}`}>{icon}</span><span className="stat-value">{value}</span><span className="stat-label">{label}</span></div>
}
