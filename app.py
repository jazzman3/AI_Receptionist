"""Inbound lead intake, slot booking, confirmation via safe local outbox."""
import os, re, sqlite3,uuid
from datetime import datetime,timezone
from pathlib import Path
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
DB=Path(os.getenv('DB_PATH',str(Path(__file__).parent/'reception.db')))
app=FastAPI(title='AI Receptionist and Appointment Setter')
def connect():
 c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row
 c.execute('CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY, name TEXT, email TEXT, message TEXT, intent TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS meetings (id TEXT PRIMARY KEY, lead_id TEXT, slot TEXT UNIQUE, status TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, kind TEXT, destination TEXT, body TEXT, sent INTEGER DEFAULT 0)')
 c.commit();return c
class Intake(BaseModel):
 name:str=Field(min_length=1)
 email:str=Field(min_length=3)
 message:str=Field(min_length=1)
class Booking(BaseModel):
 lead_id:str
 slot:str
class Chat(BaseModel):
 message:str

def classify(message):
 s=message.lower()
 if any(x in s for x in ('schedule','book','appointment','meeting','call')):return 'book'
 if any(x in s for x in ('price','cost','quote','fee')):return 'pricing'
 return 'general'

@app.post('/chat')
def chat(body:Chat):
 intent=classify(body.message)
 reply={'book':'I can help book a meeting. First submit your contact details, then select an available UTC slot.','pricing':'A team member can provide an accurate quote after discussing your requirements.','general':'Thanks for your message. Please leave your contact details so the team can follow up.'}[intent]
 return {'intent':intent,'reply':reply,'model':'deterministic_demo'}
@app.post('/leads')
def intake(body:Intake):
 id=str(uuid.uuid4());intent=classify(body.message);c=connect()
 with c:c.execute('INSERT INTO leads VALUES (?,?,?,?,?)',(id,body.name,body.email,body.message,intent))
 c.close();return {'lead_id':id,'intent':intent,'status':'captured'}
@app.get('/slots')
def slots():
 # Synthetic slots are for a local demo. Production should call Google Calendar free/busy API.
 from datetime import timedelta
 start=(datetime.now(timezone.utc)+timedelta(days=1)).replace(hour=15,minute=0,second=0,microsecond=0)
 proposed=[(start+timedelta(days=d,hours=h)).isoformat() for d in range(5) for h in (0,1,2)]
 c=connect();taken={r[0] for r in c.execute('SELECT slot FROM meetings WHERE status="confirmed"')};c.close()
 return {'timezone':'UTC','source':'synthetic_demo','slots':[s for s in proposed if s not in taken]}
@app.post('/meetings',status_code=201)
def book(body:Booking):
 try:
  parsed=datetime.fromisoformat(body.slot.replace('Z','+00:00'))
  if parsed.tzinfo is None:raise ValueError('Timezone required')
  slot=parsed.astimezone(timezone.utc).isoformat()
 except ValueError:raise HTTPException(422,'ISO8601 timezone-aware slot required')
 if slot not in slots()['slots']:raise HTTPException(409,'Slot not available')
 c=connect();lead=c.execute('SELECT * FROM leads WHERE id=?',(body.lead_id,)).fetchone()
 if not lead:c.close();raise HTTPException(404,'Lead not found')
 mid=str(uuid.uuid4())
 try:
  with c:
   c.execute('INSERT INTO meetings VALUES (?,?,?,?)',(mid,body.lead_id,slot,'confirmed'))
   c.execute('INSERT INTO outbox VALUES (?,?,?,?,0)',(str(uuid.uuid4()),'email',lead['email'],f'Your demo meeting is confirmed for {slot} (UTC).'))
 except sqlite3.IntegrityError:raise HTTPException(409,'Slot already booked')
 finally:c.close()
 return {'meeting_id':mid,'slot_utc':slot,'status':'confirmed','notification':'queued_not_sent'}
@app.get('/outbox')
def outbox():
 c=connect();rows=[dict(r) for r in c.execute('SELECT * FROM outbox')];c.close();return rows
@app.get('/metrics')
def metrics():
 c=connect();a=c.execute('SELECT COUNT(*) FROM leads').fetchone()[0];b=c.execute('SELECT COUNT(*) FROM meetings').fetchone()[0];c.close()
 return {'leads':a,'bookings':b,'booking_rate':round(b/a,3) if a else None,'dataset':'local demo'}
