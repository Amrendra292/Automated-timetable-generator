import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  Activity, ArrowDownToLine, ArrowUpRight, BookOpen, CalendarDays, CheckCircle2,
  DoorOpen, GraduationCap, LayoutDashboard, LogOut, Menu, Plus,
  ShieldCheck, Sparkles, Users, WandSparkles, X
} from 'lucide-react'
import { api, downloadCsv, saveToken } from './api'
import type { Course, Faculty, OptimizationProfile, QualityReport, Room, Stats, StudentGroup, TimeSlot, TimetableEntry } from './types'

type Tab = 'overview' | 'timetable' | 'insights' | 'courses' | 'faculty' | 'rooms' | 'groups'
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

function Login({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('admin@schedwise.dev')
  const [password, setPassword] = useState('Admin@123')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await onLogin(email, password) } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in') }
    finally { setBusy(false) }
  }
  return <main className="login-shell">
    <section className="login-visual">
      <div className="brand brand-light"><div className="brand-mark"><CalendarDays size={21}/></div><span>SchedWise</span></div>
      <div className="login-copy">
        <span className="eyebrow light-eyebrow"><Sparkles size={14}/> A smarter way to schedule</span>
        <h1>Make every<br/><em>hour count.</em></h1>
        <p>Build conflict-free academic timetables with constraint-based scheduling, resource intelligence and clear visibility.</p>
        <div className="login-mini-grid">
          <div><strong>01</strong><span>Define resources</span></div>
          <div><strong>02</strong><span>Optimize slots</span></div>
          <div><strong>03</strong><span>Publish schedules</span></div>
        </div>
      </div>
      <div className="visual-footer"><span>SMART SCHEDULING PLATFORM</span><span>v2.0.0</span></div>
    </section>
    <section className="login-panel">
      <div className="login-form-wrap">
        <div className="mobile-brand brand"><div className="brand-mark"><CalendarDays size={20}/></div><span>SchedWise</span></div>
        <span className="eyebrow">ADMIN WORKSPACE</span>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to manage your institution's timetable.</p>
        <form onSubmit={submit} className="stack-form login-form">
          <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="username"/></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password"/></label>
          {error && <div className="alert error"><X size={16}/>{error}</div>}
          <button className="primary-button full-button" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to dashboard'} <ArrowUpRight size={17}/></button>
        </form>
        <div className="demo-note"><ShieldCheck size={17}/><div><strong>Demo administrator access</strong><span>admin@schedwise.dev · Admin@123</span></div></div>
        <p className="login-disclaimer">Demo credentials are prefilled. Change the default password and JWT secret before deploying publicly.</p>
      </div>
    </section>
  </main>
}

function StatCard({ label, value, note, icon, tone }: { label: string; value: number | string; note: string; icon: ReactNode; tone: string }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}>{icon}</div><div className="stat-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div><ArrowUpRight className="stat-arrow" size={17}/></div>
}

function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><CalendarDays size={23}/></div><h3>{title}</h3><p>{body}</p>{action}</div>
}

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('smartsched_token'))
  const [tab, setTab] = useState<Tab>('overview')
  const [mobileNav, setMobileNav] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [stats, setStats] = useState<Stats>({ courses: 0, faculty: 0, rooms: 0, groups: 0, scheduled_sessions: 0, weekly_sessions_required: 0 })
  const [faculty, setFaculty] = useState<Faculty[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [groups, setGroups] = useState<StudentGroup[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [slots, setSlots] = useState<TimeSlot[]>([])
  const [schedule, setSchedule] = useState<TimetableEntry[]>([])
  const [selectedGroup, setSelectedGroup] = useState('')
  const [search, setSearch] = useState('')
  const [optimizationProfile, setOptimizationProfile] = useState<OptimizationProfile>('balanced')
  const [quality, setQuality] = useState<QualityReport | null>(null)

  async function loadAll(activeToken: string) {
    const [s, f, r, g, c, t, sl] = await Promise.all([
      api<Stats>('/api/dashboard/stats', {}, activeToken),
      api<Faculty[]>('/api/faculty', {}, activeToken),
      api<Room[]>('/api/rooms', {}, activeToken),
      api<StudentGroup[]>('/api/groups', {}, activeToken),
      api<Course[]>('/api/courses', {}, activeToken),
      api<TimetableEntry[]>('/api/timetable', {}, activeToken),
      api<TimeSlot[]>('/api/slots', {}, activeToken),
    ])
    setStats(s); setFaculty(f); setRooms(r); setGroups(g); setCourses(c); setSchedule(t); setSlots(sl)
    setSelectedGroup(current => current || (g[0] ? String(g[0].id) : ''))
  }

  useEffect(() => {
    if (!token) return
    loadAll(token).catch(() => { saveToken(null); setToken(null) })
  }, [token])

  async function handleLogin(email: string, password: string) {
    const result = await api<{ access_token: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    saveToken(result.access_token); setToken(result.access_token)
  }

  function flash(kind: 'success' | 'error', text: string) {
    setNotice({ kind, text }); window.setTimeout(() => setNotice(null), 4500)
  }

  function logout() { saveToken(null); setToken(null); setSchedule([]); setTab('overview') }

  async function generate() {
    if (!token) return
    setBusy(true); setNotice(null)
    try {
      const result = await api<{ message: string; scheduled_sessions: number; optimization_profile: OptimizationProfile; quality: QualityReport; entries: TimetableEntry[] }>('/api/timetable/generate', { method: 'POST', body: JSON.stringify({ optimization_profile: optimizationProfile }) }, token)
      setSchedule(result.entries); setQuality(result.quality)
      const updated = await api<Stats>('/api/dashboard/stats', {}, token); setStats(updated)
      setTab('timetable'); flash('success', `${result.scheduled_sessions} sessions scheduled using ${result.quality.profile_label}. Audit found ${result.quality.hard_conflicts} hard conflict(s).`)
    } catch (err) { flash('error', err instanceof Error ? err.message : 'Could not generate timetable') }
    finally { setBusy(false) }
  }

  async function exportCsv() {
    if (!token) return
    try { await downloadCsv(token); flash('success', 'CSV export downloaded.') }
    catch (err) { flash('error', err instanceof Error ? err.message : 'Export failed') }
  }

  async function addResource(event: FormEvent<HTMLFormElement>, endpoint: string, transform: (data: FormData) => object) {
    event.preventDefault(); if (!token) return
    const form = event.currentTarget
    const data = new FormData(form)
    setBusy(true)
    try {
      await api(endpoint, { method: 'POST', body: JSON.stringify(transform(data)) }, token)
      await loadAll(token); form.reset(); flash('success', 'New record added successfully.')
    } catch (err) { flash('error', err instanceof Error ? err.message : 'Could not save record') }
    finally { setBusy(false) }
  }

  useEffect(() => {
    if (!token || tab !== 'insights') return
    api<QualityReport>('/api/analytics/quality', {}, token)
      .then(setQuality)
      .catch(err => flash('error', err instanceof Error ? err.message : 'Could not load quality insights'))
  }, [token, tab, schedule.length])

  const filteredCourses = useMemo(() => courses.filter(c => `${c.code} ${c.title} ${c.group_name} ${c.faculty_name}`.toLowerCase().includes(search.toLowerCase())), [courses, search])
  const activeGroupId = selectedGroup ? Number(selectedGroup) : groups[0]?.id
  const activeGroup = groups.find(g => g.id === activeGroupId)
  const visibleSchedule = schedule.filter(entry => entry.group_id === activeGroupId)
  const orderedSlots = useMemo(() => { const byOrder = new Map<number, TimeSlot>(); slots.forEach(slot => byOrder.set(slot.slot_order, slot)); return Array.from(byOrder.values()).sort((a, b) => a.slot_order - b.slot_order) }, [slots])
  const navItems: { id: Tab; label: string; icon: ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={18}/> },
    { id: 'timetable', label: 'Timetable', icon: <CalendarDays size={18}/> },
    { id: 'insights', label: 'Quality insights', icon: <Activity size={18}/> },
    { id: 'courses', label: 'Courses', icon: <BookOpen size={18}/> },
    { id: 'faculty', label: 'Faculty', icon: <Users size={18}/> },
    { id: 'rooms', label: 'Classrooms', icon: <DoorOpen size={18}/> },
    { id: 'groups', label: 'Student groups', icon: <GraduationCap size={18}/> },
  ]

  if (!token) return <Login onLogin={handleLogin}/>

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="sidebar-top"><div className="brand"><div className="brand-mark"><CalendarDays size={20}/></div><span>SchedWise</span></div><button className="mobile-close icon-button" onClick={() => setMobileNav(false)} aria-label="Close menu"><X size={19}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="side-nav">
        {navItems.map(item => <button key={item.id} className={`nav-item ${tab === item.id ? 'active' : ''}`} onClick={() => { setTab(item.id); setMobileNav(false) }}>{item.icon}<span>{item.label}</span>{item.id === 'timetable' && schedule.length > 0 && <i className="nav-count">{schedule.length}</i>}</button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="optimizer-card"><div className="optimizer-icon"><WandSparkles size={17}/></div><strong>Smart optimizer</strong><p>Find a balanced schedule while respecting hard constraints.</p><button onClick={generate} disabled={busy}>Generate timetable <ArrowUpRight size={14}/></button></div>
        <div className="profile-row"><div className="avatar">AD</div><div className="profile-copy"><strong>Administrator</strong><span>Workspace owner</span></div><button className="icon-button logout-button" onClick={logout} title="Sign out"><LogOut size={17}/></button></div>
      </div>
    </aside>
    {mobileNav && <button className="mobile-scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation"/>}

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu icon-button" onClick={() => setMobileNav(true)} aria-label="Open menu"><Menu size={20}/></button><div><span className="breadcrumb">Workspace <span>/</span> {navItems.find(x => x.id === tab)?.label}</span><h1>{tab === 'overview' ? 'Overview' : navItems.find(x => x.id === tab)?.label}</h1></div></div><div className="topbar-actions"><div className="status-pill"><span/> System operational</div><div className="topbar-date">Academic scheduling <span>·</span> 2026–27</div><div className="avatar top-avatar">AD</div></div></header>
      <div className="page-content">
        {notice && <div className={`toast ${notice.kind}`}><span>{notice.kind === 'success' ? <CheckCircle2 size={17}/> : <X size={17}/>}</span>{notice.text}<button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={15}/></button></div>}

        {tab === 'overview' && <>
          <section className="welcome-row"><div><span className="eyebrow">YOUR ACADEMIC CONTROL CENTER</span><h2>Plan smarter. Teach better.</h2><p>Here’s a live snapshot of your scheduling workspace.</p></div><button className="primary-button" onClick={generate} disabled={busy}><WandSparkles size={17}/>{busy ? 'Optimizing…' : 'Generate timetable'}</button></section>
          <section className="stats-grid">
            <StatCard label="Courses" value={stats.courses} note="Academic subjects" icon={<BookOpen size={19}/>} tone="purple"/>
            <StatCard label="Faculty members" value={stats.faculty} note="Teaching resources" icon={<Users size={19}/>} tone="blue"/>
            <StatCard label="Classrooms & labs" value={stats.rooms} note="Available spaces" icon={<DoorOpen size={19}/>} tone="orange"/>
            <StatCard label="Student groups" value={stats.groups} note="Learning cohorts" icon={<GraduationCap size={19}/>} tone="green"/>
          </section>
          <section className="overview-grid">
            <div className="panel schedule-panel"><div className="panel-heading"><div><span className="eyebrow">SCHEDULING STATUS</span><h3>Weekly timetable</h3></div><span className={`state-tag ${schedule.length ? 'complete' : 'pending'}`}>{schedule.length ? 'Generated' : 'Not generated'}</span></div>
              {schedule.length ? <div className="generated-state"><div className="generated-icon"><CheckCircle2 size={23}/></div><div><strong>{schedule.length} sessions scheduled</strong><p>Current timetable is available for review and export.</p></div><button className="text-button" onClick={() => setTab('timetable')}>View timetable <ArrowUpRight size={15}/></button></div> : <EmptyState title="Your timetable is waiting" body="Add your academic resources, then run the optimizer to generate a conflict-free weekly schedule." action={<button className="outline-button" onClick={() => setTab('courses')}>Review courses <ArrowUpRight size={15}/></button>}/>}
            </div>
            <div className="panel readiness-panel"><div className="panel-heading"><div><span className="eyebrow">WORKSPACE READINESS</span><h3>Setup progress</h3></div><Activity size={19} className="subtle-icon"/></div>
              {[['Courses', stats.courses], ['Faculty', stats.faculty], ['Rooms', stats.rooms], ['Student groups', stats.groups]].map(([label, value]) => <div className="readiness-row" key={String(label)}><div><span>{label}</span><strong>{value}</strong></div><div className="progress-track"><i style={{ width: `${Math.min(100, Number(value) * 20)}%` }}/></div></div>)}
              <p className="readiness-hint">Add enough rooms and faculty availability to improve scheduling flexibility.</p>
            </div>
          </section>
          <section className="panel quick-panel"><div className="panel-heading"><div><span className="eyebrow">GET STARTED</span><h3>Manage your scheduling data</h3></div><span className="muted small">Build your resource catalogue</span></div><div className="quick-grid">
            {[{tab:'courses' as Tab, icon:<BookOpen/>, title:'Add courses', desc:'Subjects and weekly sessions'},{tab:'faculty' as Tab, icon:<Users/>, title:'Add faculty', desc:'Teaching staff and availability'},{tab:'rooms' as Tab, icon:<DoorOpen/>, title:'Add classrooms', desc:'Capacity and room type'},{tab:'groups' as Tab, icon:<GraduationCap/>, title:'Add student groups', desc:'Class sections and strength'}].map(item => <button className="quick-action" key={item.tab} onClick={() => setTab(item.tab)}><div className="quick-icon">{item.icon}</div><div><strong>{item.title}</strong><span>{item.desc}</span></div><ArrowUpRight size={16}/></button>)}
          </div></section>
        </>}

        {tab === 'timetable' && <>
          <section className="welcome-row"><div><span className="eyebrow">CONFLICT-AWARE SCHEDULING</span><h2>Weekly timetable</h2><p>Review the generated schedule by student group.</p></div><div className="action-group"><button className="outline-button" onClick={exportCsv} disabled={!schedule.length}><ArrowDownToLine size={16}/> Export CSV</button><button className="primary-button" onClick={generate} disabled={busy}><WandSparkles size={17}/>{busy ? 'Optimizing…' : 'Regenerate'}</button></div></section>
          <section className="panel timetable-panel"><div className="timetable-toolbar"><div><span className="eyebrow">SCHEDULE VIEW</span><h3>{activeGroup?.name || 'Select a student group'}</h3></div><div className="toolbar-controls"><label className="select-label">Optimization mode<select value={optimizationProfile} onChange={e => setOptimizationProfile(e.target.value as OptimizationProfile)}><option value="balanced">Balanced campus</option><option value="student_first">Student-first</option><option value="resource_saver">Resource efficient</option></select></label><label className="select-label">Student group<select value={selectedGroup} onChange={e => setSelectedGroup(e.target.value)}>{groups.map(g => <option key={g.id} value={g.id}>{g.name} · {g.size} students</option>)}</select></label></div></div>
            {!schedule.length ? <EmptyState title="No timetable generated yet" body="The optimizer will allocate courses, faculty and rooms across the weekly time slots." action={<button className="primary-button" onClick={generate} disabled={busy}><WandSparkles size={16}/> Generate timetable</button>}/> : <div className="table-scroll"><div className="week-grid"><div className="week-head time-head">TIME</div>{DAYS.map(day => <div className="week-head" key={day}>{day.slice(0, 3).toUpperCase()}</div>)}
              {orderedSlots.map(slot => <div className="week-row" key={slot.slot_order} style={{display:'contents'}}><div className="time-cell"><strong>{slot.start_time}</strong><span>{slot.end_time}</span></div>{DAYS.map(day => { const entry = visibleSchedule.find(x => x.day === day && x.slot_order === slot.slot_order); return <div className="week-cell" key={`${day}-${slot.slot_order}`}>{entry ? <div className={`class-card ${entry.room_type === 'lab' ? 'lab-card' : ''}`}><strong>{entry.course_code}</strong><span>{entry.course_title}</span><small><Users size={12}/> {entry.faculty_name}</small><small><DoorOpen size={12}/> {entry.room_name}</small></div> : <div className="free-slot">—</div>}</div> })}</div>)}
            </div></div>}
            {schedule.length > 0 && <div className="timetable-legend"><span><i className="legend-dot lecture"/> Lecture</span><span><i className="legend-dot lab"/> Laboratory</span><span className="legend-note"><CheckCircle2 size={14}/> Hard-constraint conflicts: 0</span></div>}
          </section>
        </>}

        {tab === 'insights' && <>
          <section className="welcome-row"><div><span className="eyebrow">EXPLAINABLE OPTIMIZATION</span><h2>Schedule quality insights</h2><p>Audit the current timetable, inspect trade-offs and see practical improvement suggestions.</p></div><button className="primary-button" onClick={generate} disabled={busy}><WandSparkles size={17}/>{busy ? 'Optimizing…' : 'Re-run optimizer'}</button></section>
          {!quality?.generated ? <section className="panel insights-panel"><EmptyState title="No schedule to audit yet" body="Generate a timetable first. SchedWise will calculate compactness, resource fit, weekday distribution and hard-constraint checks." action={<button className="primary-button" onClick={generate} disabled={busy}><WandSparkles size={16}/> Generate timetable</button>}/></section> : <>
            <section className="quality-summary"><div className="quality-score-card"><span className="eyebrow">INDICATIVE QUALITY INDEX</span><strong>{quality.quality_score}<small>/100</small></strong><p>{quality.profile_label} · {quality.sessions_scheduled} scheduled sessions</p><div className="quality-track"><i style={{width:`${quality.quality_score}%`}}/></div></div>
              <div className="quality-metric"><span>Hard conflicts</span><strong className={quality.hard_conflicts ? 'metric-warning' : 'metric-good'}>{quality.hard_conflicts}</strong><small>Faculty, group, room and capacity audit</small></div>
              <div className="quality-metric"><span>Compactness</span><strong>{quality.compactness_score}%</strong><small>{quality.average_idle_gaps_per_group_day} average idle gaps per active group-day</small></div>
              <div className="quality-metric"><span>Avg. campus days</span><strong>{quality.average_campus_days_per_group}</strong><small>Active weekdays per scheduled student group</small></div>
              <div className="quality-metric"><span>Seat utilization</span><strong>{quality.seat_utilization_pct}%</strong><small>Average assigned group size / room capacity</small></div>
              <div className="quality-metric"><span>Weekday load balance</span><strong>{quality.weekday_load_balance_score}%</strong><small>Distribution of scheduled sessions across weekdays</small></div>
            </section>
            <section className="insights-grid"><div className="panel insights-panel"><div className="panel-heading"><div><span className="eyebrow">CAMPUS LOAD PROFILE</span><h3>Sessions by weekday</h3></div><Activity size={18} className="subtle-icon"/></div><div className="weekday-bars">{(Object.entries(quality.daily_session_load) as [string, number][]).map(([day, count]) => { const peak = Math.max(1, ...Object.values(quality.daily_session_load) as number[]); return <div className="weekday-row" key={day}><span>{day.slice(0,3)}</span><div className="weekday-track"><i style={{width:`${count / peak * 100}%`}}/></div><strong>{count}</strong></div> })}</div><p className="insight-footnote">This distribution is a planning signal, not a target that every institution must match.</p></div>
              <div className="panel insights-panel"><div className="panel-heading"><div><span className="eyebrow">EXPLAINABLE RECOMMENDATIONS</span><h3>Next best actions</h3></div><Sparkles size={18} className="subtle-icon"/></div><div className="recommendation-list">{quality.recommendations.map((item, index) => <div className="recommendation-item" key={`${item.title}-${index}`}><span className={`priority-dot ${item.priority.replace(' ', '-')}`}/><div><strong>{item.title}</strong><p>{item.detail}</p></div></div>)}</div></div></section>
            <p className="score-method">{quality.score_method}</p>
          </>}
        </>}

        {tab === 'courses' && <ResourcePage title="Courses" eyebrow="ACADEMIC CATALOGUE" description="Define subjects, assigned faculty, student groups and weekly session requirements." count={courses.length} countLabel="courses">
          <form className="resource-form course-form" onSubmit={e => addResource(e, '/api/courses', d => ({ code: String(d.get('code')), title: String(d.get('title')), faculty_id: Number(d.get('faculty_id')), group_id: Number(d.get('group_id')), sessions_per_week: Number(d.get('sessions_per_week')), room_type: String(d.get('room_type')) }))}>
            <div className="form-title"><Plus size={17}/> Add a course</div><label>Course code<input name="code" placeholder="e.g. CS401" required/></label><label>Course title<input name="title" placeholder="e.g. Cloud Computing" required/></label><label>Faculty<select name="faculty_id" required defaultValue="">{faculty.length === 0 && <option value="">Add faculty first</option>}{faculty.map(f => <option value={f.id} key={f.id}>{f.name}</option>)}</select></label><label>Student group<select name="group_id" required defaultValue="">{groups.length === 0 && <option value="">Add a group first</option>}{groups.map(g => <option value={g.id} key={g.id}>{g.name}</option>)}</select></label><label>Sessions / week<input name="sessions_per_week" type="number" min="1" max="10" defaultValue="2" required/></label><label>Room type<select name="room_type"><option value="classroom">Classroom</option><option value="lab">Laboratory</option></select></label><button className="primary-button form-submit" disabled={busy || !faculty.length || !groups.length}>Add course <Plus size={16}/></button>
          </form>
          <div className="table-heading"><div><h3>Course directory</h3><span>{courses.length} records</span></div><input className="search-input" placeholder="Search courses…" value={search} onChange={e => setSearch(e.target.value)}/></div>
          <div className="data-table-wrap"><table className="data-table"><thead><tr><th>COURSE</th><th>FACULTY</th><th>STUDENT GROUP</th><th>SESSIONS / WK</th><th>ROOM</th></tr></thead><tbody>{filteredCourses.map(c => <tr key={c.id}><td><strong>{c.code}</strong><span>{c.title}</span></td><td>{c.faculty_name}</td><td><span className="group-chip">{c.group_name}</span></td><td>{c.sessions_per_week}</td><td><span className={`type-chip ${c.room_type}`}>{c.room_type}</span></td></tr>)}</tbody></table>{filteredCourses.length === 0 && <p className="table-empty">No courses found. Add your first course above.</p>}</div>
        </ResourcePage>}

        {tab === 'faculty' && <ResourcePage title="Faculty" eyebrow="TEACHING RESOURCES" description="Manage instructors and their maximum daily teaching load." count={faculty.length} countLabel="faculty members">
          <form className="resource-form" onSubmit={e => addResource(e, '/api/faculty', d => ({ name: String(d.get('name')), email: String(d.get('email')), max_daily_load: Number(d.get('max_daily_load')) }))}>
            <div className="form-title"><Plus size={17}/> Add faculty member</div><label>Full name<input name="name" placeholder="e.g. Dr. Priya Sharma" required/></label><label>Work email<input name="email" type="email" placeholder="name@university.edu" required/></label><label>Max classes / day<input name="max_daily_load" type="number" min="1" max="10" defaultValue="4" required/></label><button className="primary-button form-submit" disabled={busy}>Add faculty <Plus size={16}/></button>
          </form>
          <div className="table-heading"><div><h3>Faculty directory</h3><span>{faculty.length} records</span></div></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>FACULTY MEMBER</th><th>EMAIL</th><th>MAX DAILY LOAD</th><th>STATUS</th></tr></thead><tbody>{faculty.map(f => <tr key={f.id}><td><div className="person-cell"><div className="mini-avatar">{f.name.split(' ').slice(-1)[0]?.[0] || 'F'}</div><strong>{f.name}</strong></div></td><td>{f.email}</td><td>{f.max_daily_load} sessions</td><td><span className="state-tag complete">Available</span></td></tr>)}</tbody></table>{faculty.length === 0 && <p className="table-empty">No faculty members added yet.</p>}</div>
        </ResourcePage>}

        {tab === 'rooms' && <ResourcePage title="Classrooms & labs" eyebrow="PHYSICAL RESOURCES" description="Register teaching spaces and define capacity and room requirements." count={rooms.length} countLabel="rooms">
          <form className="resource-form" onSubmit={e => addResource(e, '/api/rooms', d => ({ name: String(d.get('name')), capacity: Number(d.get('capacity')), room_type: String(d.get('room_type')) }))}>
            <div className="form-title"><Plus size={17}/> Add a room</div><label>Room name<input name="name" placeholder="e.g. Block 34 · Room 201" required/></label><label>Seating capacity<input name="capacity" type="number" min="1" max="500" placeholder="e.g. 60" required/></label><label>Room type<select name="room_type"><option value="classroom">Classroom</option><option value="lab">Laboratory</option></select></label><button className="primary-button form-submit" disabled={busy}>Add room <Plus size={16}/></button>
          </form>
          <div className="table-heading"><div><h3>Room directory</h3><span>{rooms.length} records</span></div></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>ROOM</th><th>TYPE</th><th>CAPACITY</th><th>UTILIZATION</th></tr></thead><tbody>{rooms.map(r => <tr key={r.id}><td><div className="person-cell"><div className="room-avatar"><DoorOpen size={16}/></div><strong>{r.name}</strong></div></td><td><span className={`type-chip ${r.room_type}`}>{r.room_type}</span></td><td>{r.capacity} seats</td><td><span className="state-tag complete">Registered</span></td></tr>)}</tbody></table>{rooms.length === 0 && <p className="table-empty">No rooms added yet.</p>}</div>
        </ResourcePage>}

        {tab === 'groups' && <ResourcePage title="Student groups" eyebrow="LEARNING COHORTS" description="Create class sections and define the number of students in each group." count={groups.length} countLabel="student groups">
          <form className="resource-form" onSubmit={e => addResource(e, '/api/groups', d => ({ name: String(d.get('name')), size: Number(d.get('size')) }))}>
            <div className="form-title"><Plus size={17}/> Add a student group</div><label>Group name<input name="name" placeholder="e.g. CSE-A" required/></label><label>Number of students<input name="size" type="number" min="1" max="500" placeholder="e.g. 45" required/></label><button className="primary-button form-submit" disabled={busy}>Add group <Plus size={16}/></button>
          </form>
          <div className="table-heading"><div><h3>Student group directory</h3><span>{groups.length} records</span></div></div><div className="data-table-wrap"><table className="data-table"><thead><tr><th>GROUP</th><th>STUDENT STRENGTH</th><th>COURSES ASSIGNED</th><th>STATUS</th></tr></thead><tbody>{groups.map(g => <tr key={g.id}><td><div className="person-cell"><div className="group-avatar"><GraduationCap size={16}/></div><strong>{g.name}</strong></div></td><td>{g.size} students</td><td>{courses.filter(c => c.group_id === g.id).length} courses</td><td><span className="state-tag complete">Active</span></td></tr>)}</tbody></table>{groups.length === 0 && <p className="table-empty">No student groups added yet.</p>}</div>
        </ResourcePage>}
      </div>
      <footer className="app-footer"><span>SchedWise <b>·</b> Constraint-based timetable optimizer</span><span>Built for smarter academic planning</span></footer>
    </main>
  </div>
}

function ResourcePage({ title, eyebrow, description, count, countLabel, children }: { title: string; eyebrow: string; description: string; count: number; countLabel: string; children: ReactNode }) {
  return <><section className="welcome-row resource-welcome"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div><div className="count-box"><strong>{count}</strong><span>{countLabel}</span></div></section><section className="panel resource-panel">{children}</section></>
}

export default App
