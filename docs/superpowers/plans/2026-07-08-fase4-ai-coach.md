# Fase 4 — AI Coach (Claude-powered duiding + chat)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elke atleet krijgt dagelijks een 1-2 zinnen NL-duiding van hun scores via Claude Haiku (snel, goedkoop), en een chat-interface via Claude Sonnet waarmee ze vragen kunnen stellen over hun training.

**Architecture:** `api/ai_coach.py` — twee functies: `daily_note(ctx)` (Haiku, context-bundle → string) en `chat(messages, ctx)` (Sonnet, chat-history → reply). `db.py` krijgt een `coach_chat` tabel voor chat-geschiedenis. Twee nieuwe routes in `api/routes.py`: `POST /athlete/{id}/coach/daily` en `POST /athlete/{id}/coach/chat`. Frontend: `CoachNote.jsx` toont dagelijkse duiding in de home-Hero; nieuwe `Coach` tab/scherm met chat-UI. `ANTHROPIC_API_KEY` in Vercel env + `.env`.

**Tech Stack:** Python 3.9, FastAPI, `anthropic` Python SDK (streaming niet nodig), React 19, Vite. Model: `claude-haiku-4-5-20251001` (daily), `claude-sonnet-5` (chat). Repo `~/garmin-coach`.

**Pre-condition:** `ANTHROPIC_API_KEY` staat in `.env` (haal op uit Bitwarden) en als Vercel-environment-variable voor `sidehustlehqs`.

---

## Bestandsstructuur

| Bestand | Actie | Verantwoordelijkheid |
|---|---|---|
| `api/requirements.txt` | Modify | Voeg `anthropic>=0.40.0` toe |
| `api/ai_coach.py` | Create | `daily_note(ctx)` + `chat(messages, ctx)` |
| `db.py` | Modify | `coach_chat` tabel |
| `api/routes.py` | Modify | `/coach/daily` + `/coach/chat` routes |
| `dashboard/src/ui/CoachNote.jsx` | Modify | Toon daily duiding (fetch on mount) |
| `dashboard/src/screens/Coach.jsx` | Create | Chat-scherm (bericht-lijst + input) |
| `dashboard/src/App.jsx` | Modify | Tab "coach" + route naar Coach.jsx |
| `dashboard/src/api.js` | Modify | `getDailyNote`, `sendChatMessage` |
| `tests/test_ai_coach.py` | Create | Unit-tests voor context-bundeling (gemockt) |
| `tests/test_api.py` | Modify | Coach-endpoint tests |
| `dashboard/dist/` | Rebuild | Na alle frontend-wijzigingen |

Tests: `.venv/bin/python -m pytest` · `cd dashboard && npm test`.

---

## Task 1: `anthropic` dep + `api/ai_coach.py`

**Files:** Modify `api/requirements.txt`, Create `api/ai_coach.py`

- [ ] **Step 1: Voeg anthropic toe aan `api/requirements.txt`**

Voeg toe na de laatste regel:
```
anthropic>=0.40.0
```

Controleer huidige inhoud eerst:
```bash
cat ~/garmin-coach/api/requirements.txt
```

- [ ] **Step 2: Schrijf de falende test voor daily_note**

`tests/test_ai_coach.py`:
```python
"""Tests voor ai_coach — gebruik unittest.mock zodat er nooit echte API-calls zijn."""
from unittest.mock import patch, MagicMock
from api.ai_coach import build_daily_context, daily_note, chat

SAMPLE_CTX = {
    "athlete_name": "Rowan",
    "readiness": 72,
    "hrv": 58,
    "sleep_s": 27000,  # 7.5u
    "sleep_score": 75,
    "body_battery": 80,
    "acwr": 0.92,
    "training_today": {"title": "Tempo 10km", "run_type": "quality", "target_pace_s": 295},
}

def test_build_daily_context_includes_key_fields():
    ctx_str = build_daily_context(SAMPLE_CTX)
    assert "Rowan" in ctx_str
    assert "72" in ctx_str  # readiness
    assert "Tempo 10km" in ctx_str

def test_daily_note_calls_haiku_and_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Goed herstel, train vol gas.")]
    with patch("api.ai_coach._client", mock_client):
        result = daily_note(SAMPLE_CTX)
    assert isinstance(result, str)
    assert len(result) > 0
    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_args.kwargs["max_tokens"] <= 100

def test_chat_calls_sonnet_and_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Je VO₂max is goed voor sub-4.")]
    with patch("api.ai_coach._client", mock_client):
        messages = [{"role": "user", "content": "Hoe ver ben ik van sub-4?"}]
        result = chat(messages, SAMPLE_CTX)
    assert isinstance(result, str)
    call_args = mock_client.messages.create.call_args
    assert "sonnet" in call_args.kwargs["model"].lower()

def test_daily_note_handles_missing_fields():
    """Geen crash als signalen ontbreken."""
    ctx = {"athlete_name": "Test"}
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Weinig data beschikbaar.")]
    with patch("api.ai_coach._client", mock_client):
        result = daily_note(ctx)
    assert isinstance(result, str)
```

- [ ] **Step 3: Run om te bevestigen dat ze falen**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_ai_coach.py -v
```
Verwacht: `ImportError: No module named 'api.ai_coach'`

- [ ] **Step 4: Implementeer `api/ai_coach.py`**

```python
"""AI-coach module — Claude Haiku voor dagelijkse note, Sonnet voor chat.
Geen I/O: alle DB-queries zitten in routes.py, die de context-dict samenstelt en hier doorgeeft."""
from __future__ import annotations
import os
import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_DAILY_SYSTEM = (
    "Je bent een persoonlijke hardloopcoach. Geef in 1-2 korte Nederlandse zinnen duiding "
    "op de gezondheids- en trainingsdata van de atleet. Wees direct en motiverend. "
    "Gebruik concrete getallen. Geen opsommingstekens, geen headers."
)

_CHAT_SYSTEM = (
    "Je bent een persoonlijke hardloopcoach. Beantwoord vragen over de training van de atleet "
    "in het Nederlands. Je hebt toegang tot de huidige gezondheids- en trainingsdata hieronder. "
    "Wees concreet, bondig (max 3 alinea's) en gebruik de data. Geen opsommingstekens tenzij "
    "de gebruiker er om vraagt."
)


def build_daily_context(ctx: dict) -> str:
    """Zet de context-dict om naar een leesbare tekst voor de prompt."""
    lines = [f"Atleet: {ctx.get('athlete_name', 'onbekend')}"]
    if ctx.get("readiness") is not None:
        lines.append(f"Readiness: {ctx['readiness']}/100")
    if ctx.get("hrv") is not None:
        lines.append(f"HRV: {ctx['hrv']} ms")
    if ctx.get("sleep_s") is not None:
        h = round(ctx["sleep_s"] / 3600, 1)
        lines.append(f"Slaap: {h}u" + (f" (score {ctx['sleep_score']})" if ctx.get("sleep_score") else ""))
    if ctx.get("body_battery") is not None:
        lines.append(f"Body battery: {ctx['body_battery']}")
    if ctx.get("acwr") is not None:
        lines.append(f"Belasting (ACWR): {ctx['acwr']}")
    if ctx.get("training_today"):
        t = ctx["training_today"]
        lines.append(f"Training vandaag: {t.get('title', t.get('run_type', '–'))}")
    return "\n".join(lines)


def daily_note(ctx: dict) -> str:
    """Genereer een dagelijkse 1-2 zinnen coaching-note via Claude Haiku."""
    context_text = build_daily_context(ctx)
    resp = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=_DAILY_SYSTEM,
        messages=[{"role": "user", "content": f"Data van vandaag:\n{context_text}"}],
    )
    return resp.content[0].text.strip()


def chat(messages: list[dict], ctx: dict) -> str:
    """Chat-reply via Claude Sonnet. messages = [{"role": "user/assistant", "content": "..."}]."""
    context_text = build_daily_context(ctx)
    system_with_ctx = f"{_CHAT_SYSTEM}\n\nHuidige data:\n{context_text}"
    resp = _client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        system=system_with_ctx,
        messages=messages,
    )
    return resp.content[0].text.strip()
```

- [ ] **Step 5: Run tests**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_ai_coach.py -v
```
Verwacht: alle 4 PASS.

- [ ] **Step 6: Commit**
```bash
git add api/ai_coach.py api/requirements.txt tests/test_ai_coach.py
git commit -m "feat(fase4): ai_coach module (Haiku daily + Sonnet chat)"
```

---

## Task 2: `coach_chat` tabel in db.py

**Files:** Modify `db.py`

- [ ] **Step 1: Schrijf de falende test**

`tests/test_db.py` — voeg toe:
```python
def test_coach_chat_table_exists():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        migrate_db(db_path)
        with get_conn(db_path) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "coach_chat" in tables
```

- [ ] **Step 2: Run om te bevestigen dat het faalt**
```bash
.venv/bin/python -m pytest tests/test_db.py::test_coach_chat_table_exists -v
```

- [ ] **Step 3: Voeg `coach_chat` toe in `db.py`**

In `SCHEMA_SQLITE`:
```sql
CREATE TABLE IF NOT EXISTS coach_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id TEXT NOT NULL,
    role TEXT NOT NULL,          -- 'user' of 'assistant'
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

In `SCHEMA_PG`:
```sql
CREATE TABLE IF NOT EXISTS coach_chat (
    id SERIAL PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Migratiefunctie:
```python
def _migrate_coach_chat(path: Path) -> None:
    with get_conn(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS coach_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT, athlete_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')))""")
        conn.commit()
```

Roep aan in `migrate_db`.

- [ ] **Step 4: Run tests**
```bash
.venv/bin/python -m pytest tests/test_db.py -v
```

- [ ] **Step 5: Commit**
```bash
git add db.py tests/test_db.py
git commit -m "feat(fase4): coach_chat tabel in db.py"
```

---

## Task 3: Coach API routes

**Files:** Modify `api/routes.py`

- [ ] **Step 1: Schrijf de falende tests**

`tests/test_api.py` — voeg toe:
```python
def test_coach_daily_returns_note(client, athlete_id):
    """POST /athlete/{id}/coach/daily moet een noot teruggeven (gemockte Anthropic)."""
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Goed herstel, train vol gas vandaag.")]
    with patch("api.ai_coach._client") as mock_client:
        mock_client.messages.create.return_value = mock_resp
        resp = client.post(f"/athlete/{athlete_id}/coach/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert "note" in data
    assert isinstance(data["note"], str)

def test_coach_chat_returns_reply(client, athlete_id):
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Je VO₂max is goed.")]
    with patch("api.ai_coach._client") as mock_client:
        mock_client.messages.create.return_value = mock_resp
        resp = client.post(f"/athlete/{athlete_id}/coach/chat",
                           json={"message": "Hoe ver ben ik van sub-4?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)

def test_coach_chat_persists_messages(client, athlete_id):
    """Chat-history moet worden opgeslagen en teruggegeven."""
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Prima vraag!")]
    with patch("api.ai_coach._client") as mock_client:
        mock_client.messages.create.return_value = mock_resp
        client.post(f"/athlete/{athlete_id}/coach/chat",
                    json={"message": "Vraag 1"})
        client.post(f"/athlete/{athlete_id}/coach/chat",
                    json={"message": "Vraag 2"})
    history_resp = client.get(f"/athlete/{athlete_id}/coach/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 4  # 2× user + 2× assistant
```

- [ ] **Step 2: Run om te bevestigen dat het faalt**
```bash
.venv/bin/python -m pytest tests/test_api.py::test_coach_daily_returns_note -v
```

- [ ] **Step 3: Voeg routes toe aan `api/routes.py`**

Voeg imports toe bovenaan (na bestaande imports):
```python
from api import ai_coach
```

Voeg routes toe (na de `trigger_replan`/`get_plan_meta` routes):
```python
@router.post("/athlete/{athlete_id}/coach/daily")
def get_coach_daily(athlete_id: str) -> dict:
    """Genereer dagelijkse 1-2 zinnen duiding via Claude Haiku."""
    with _conn() as conn:
        _athlete_or_404(conn, athlete_id)
        # Bouw context uit DB
        home = get_home.__wrapped__(athlete_id) if hasattr(get_home, "__wrapped__") else _build_context(conn, athlete_id)
        note = ai_coach.daily_note(home)
        return {"note": note}


@router.post("/athlete/{athlete_id}/coach/chat")
def post_coach_chat(athlete_id: str, body: dict) -> dict:
    """Stuur een chat-bericht naar de coach en sla op in history."""
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is vereist")
    with _conn() as conn:
        _athlete_or_404(conn, athlete_id)
        # Haal history op (laatste 20 berichten)
        rows = conn.execute(
            "SELECT role, content FROM coach_chat WHERE athlete_id=? ORDER BY id DESC LIMIT 20",
            (athlete_id,)).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        history.append({"role": "user", "content": message})
        ctx = _build_context(conn, athlete_id)
        reply = ai_coach.chat(history, ctx)
        # Sla user + assistant op
        conn.execute("INSERT INTO coach_chat (athlete_id, role, content) VALUES (?,?,?)",
                     (athlete_id, "user", message))
        conn.execute("INSERT INTO coach_chat (athlete_id, role, content) VALUES (?,?,?)",
                     (athlete_id, "assistant", reply))
        conn.commit()
        return {"reply": reply}


@router.get("/athlete/{athlete_id}/coach/history")
def get_coach_history(athlete_id: str, limit: int = 40) -> list[dict]:
    """Haal chat-geschiedenis op."""
    with _conn() as conn:
        _athlete_or_404(conn, athlete_id)
        rows = conn.execute(
            "SELECT role, content, created_at FROM coach_chat WHERE athlete_id=? ORDER BY id DESC LIMIT ?",
            (athlete_id, limit)).fetchall()
        return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
                for r in reversed(rows)]
```

Voeg helper `_build_context` toe (vlak voor de routes, na `_fitness`):
```python
def _build_context(conn, athlete_id: str) -> dict:
    """Bouw een context-dict voor de AI coach vanuit de DB."""
    athlete = conn.execute("SELECT display_name FROM athlete WHERE id=?", (athlete_id,)).fetchone()
    health = conn.execute(
        "SELECT readiness_score, hrv, sleep_duration_s, sleep_score, body_battery "
        "FROM daily_health WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,)).fetchone()
    load_row = conn.execute(
        "SELECT acwr FROM training_load WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,)).fetchone()
    today_wo = conn.execute(
        "SELECT COALESCE(adjusted_title, title) as title, "
        "COALESCE(adjusted_run_type, run_type) as run_type, "
        "COALESCE(adjusted_target_pace_s, target_pace_s) as target_pace_s "
        "FROM planned_workout WHERE athlete_id=? AND planned_date=?",
        (athlete_id, str(_dt.date.today()))).fetchone()
    return {
        "athlete_name": athlete["display_name"] if athlete else athlete_id,
        "readiness": health["readiness_score"] if health else None,
        "hrv": health["hrv"] if health else None,
        "sleep_s": health["sleep_duration_s"] if health else None,
        "sleep_score": health["sleep_score"] if health else None,
        "body_battery": health["body_battery"] if health else None,
        "acwr": load_row["acwr"] if load_row else None,
        "training_today": dict(today_wo) if today_wo else None,
    }
```

- [ ] **Step 4: Run alle tests**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/ -v
```
Verwacht: alle tests PASS (mock zorgt dat er geen echte API-calls zijn).

- [ ] **Step 5: Commit**
```bash
git add api/routes.py
git commit -m "feat(fase4): /coach/daily + /coach/chat + /coach/history endpoints"
```

---

## Task 4: Frontend — CoachNote dagelijkse duiding

**Files:** Modify `dashboard/src/ui/CoachNote.jsx`, `dashboard/src/screens/Home.jsx`, `dashboard/src/api.js`

- [ ] **Step 1:** Voeg `getDailyNote` toe aan `dashboard/src/api.js`:
```js
export async function getDailyNote(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/daily`, { method: 'POST' })
  if (!r.ok) throw new Error('coach/daily failed')
  return r.json()
}
```

- [ ] **Step 2:** Update `dashboard/src/ui/CoachNote.jsx` — toon string direct (geen wrapper nodig):

```jsx
export default function CoachNote({ children }) {
  if (!children) return null
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--green)',
      borderRadius: 10, padding: '8px 12px', marginTop: 10,
      fontSize: 13, color: 'var(--muted)', lineHeight: 1.45,
      fontStyle: 'italic',
    }}>
      <span style={{ color: 'var(--green)', fontStyle: 'normal', fontWeight: 700 }}>Coach · </span>
      {children}
    </div>
  )
}
```

- [ ] **Step 3:** Update `Home.jsx` — haal dagelijkse note op en toon in ReadinessHero:

Voeg toe aan de Home-component (naast de andere useEffect-fetches):
```jsx
import { getDailyNote } from '../api'

const [coachNote, setCoachNote] = useState(null)
useEffect(() => {
  if (!athleteId) return
  getDailyNote(athleteId).then(d => setCoachNote(d.note)).catch(() => {})
}, [athleteId])
```

Geef `coachNote` door aan `ReadinessHero`:
```jsx
<ReadinessHero readiness={{ ...readiness, duiding: coachNote }} />
```

- [ ] **Step 4:** Controleer in browser dev (met dev server):
- Haiku-call werkt alleen met echte `ANTHROPIC_API_KEY` in `.env`.
- Als API-key ontbreekt: note is `null`, geen crash.

- [ ] **Step 5: Commit**
```bash
git add dashboard/src/ui/CoachNote.jsx dashboard/src/screens/Home.jsx dashboard/src/api.js
git commit -m "feat(fase4): dagelijkse coach-note in Home (Haiku)"
```

---

## Task 5: Frontend — Coach chat-scherm

**Files:** Create `dashboard/src/screens/Coach.jsx`, Modify `dashboard/src/App.jsx`, `dashboard/src/api.js`

- [ ] **Step 1:** Voeg `sendChatMessage` + `getChatHistory` toe aan `dashboard/src/api.js`:
```js
export async function sendChatMessage(athleteId, message) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('coach/chat failed')
  return r.json()
}

export async function getChatHistory(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/history`)
  if (!r.ok) throw new Error('coach/history failed')
  return r.json()
}
```

- [ ] **Step 2:** Maak `dashboard/src/screens/Coach.jsx`:
```jsx
import { useState, useEffect, useRef } from 'react'
import { sendChatMessage, getChatHistory } from '../api'

export default function Coach({ athleteId }) {
  const [messages, setMessages] = useState([])   // [{role, content}]
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!athleteId) return
    getChatHistory(athleteId)
      .then(hist => setMessages(hist.map(h => ({ role: h.role, content: h.content }))))
      .catch(() => {})
  }, [athleteId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const data = await sendChatMessage(athleteId, msg)
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Er ging iets mis. Probeer opnieuw.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', padding: '0 16px' }}>
      <div style={{ padding: '12px 0 8px' }}>
        <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.06em', margin: 0 }}>
          AI Coach · Claude Sonnet
        </p>
      </div>

      {/* Berichtenlijst */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: 12 }}>
        {messages.length === 0 && !loading && (
          <p style={{ color: 'var(--muted)', fontSize: 13, margin: '24px 0', textAlign: 'center' }}>
            Stel een vraag over je training.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
            background: m.role === 'user' ? 'var(--blue)' : 'var(--card)',
            color: m.role === 'user' ? '#fff' : 'var(--ink)',
            borderRadius: m.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
            padding: '9px 13px', fontSize: 14, lineHeight: 1.4,
          }}>
            {m.content}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start', color: 'var(--muted)', fontSize: 13 }}>
            Coach denkt na…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 8, paddingBottom: 16 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Vraag de coach iets…"
          style={{
            flex: 1, background: 'var(--card)', border: '1px solid var(--line)',
            borderRadius: 22, padding: '10px 16px', color: 'var(--ink)',
            fontSize: 14, outline: 'none',
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            background: loading ? 'var(--line)' : 'var(--blue)', color: '#fff',
            border: 'none', borderRadius: '50%', width: 42, height: 42,
            fontSize: 18, cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          ↑
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3:** Voeg "coach" tab toe aan `dashboard/src/App.jsx`:

In de tabs-array:
```jsx
{ id: 'coach', label: '🤖', screen: Coach }
```

Importeer:
```jsx
import Coach from './screens/Coach'
```

Geef `athleteId` door:
```jsx
case 'coach': return <Coach athleteId={athleteId} />
```

- [ ] **Step 4:** Controleer in browser dev — chat-tab zichtbaar, input werkt, berichten scrollen. (Zonder ANTHROPIC_API_KEY in `.env` geeft de API een error — 500 in de console is normaal in dev als de key ontbreekt.)

- [ ] **Step 5: Commit**
```bash
git add dashboard/src/screens/Coach.jsx dashboard/src/App.jsx dashboard/src/api.js
git commit -m "feat(fase4): Coach chat-scherm (Sonnet)"
```

---

## Task 6: Secrets + build + deploy

- [ ] **Step 1: Controleer `ANTHROPIC_API_KEY` in `.env`**
```bash
grep ANTHROPIC ~/garmin-coach/.env
```
Als ontbreekt: haal op uit Bitwarden → zet in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```
Controleer dat `.gitignore` de `.env` uitsluit:
```bash
grep ".env" ~/garmin-coach/.gitignore
```

- [ ] **Step 2: Zet `ANTHROPIC_API_KEY` als Vercel env var**

Via Vercel dashboard: garmin-coach-phi → Settings → Environment Variables → Add:
- Key: `ANTHROPIC_API_KEY`
- Value: `sk-ant-...`
- Environment: Production (+ Preview)

Of via CLI (account verificatie EERST):
```bash
npx vercel@latest whoami
# Moet tonen: sidehustlehqs
npx vercel@latest env add ANTHROPIC_API_KEY
```

- [ ] **Step 3: Vitest — alle tests groen**
```bash
cd ~/garmin-coach/dashboard && npm test -- --run
```

- [ ] **Step 4: pytest — alle tests groen**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/ -v
```

- [ ] **Step 5: Build + deploy**
```bash
cd ~/garmin-coach/dashboard && npm run build
cd ~/garmin-coach
git add dashboard/dist
git commit -m "feat(fase4): build voor productie-deploy"
git push
npx vercel@latest whoami  # MOET sidehustlehqs zijn
npx vercel@latest --prod
```

- [ ] **Step 6: Smoke-test productie**
```bash
# Daily note (echte Haiku-call — vereist geldige API-key in prod)
curl -s -X POST https://garmin-coach-phi.vercel.app/api/athlete/rowan/coach/daily | python3 -m json.tool
```
Verwacht: `{"note": "<Nederlandse zin>"}`.

- [ ] **Step 7: Update Obsidian vault**

In `~/SideHQ/Persoonlijk/Marathon & Hyrox/Garmin-coach status.md`:
- Fase 4: `KLAAR & LIVE` — dagelijkse Haiku-note in Home + Sonnet-chat tab
- Volgende: uitbreiden (push-notificatie ochtendrapport, voice?)
