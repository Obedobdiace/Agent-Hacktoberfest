import { useState, useEffect, useRef } from 'react'
import './AeonUI.css'

// IPC Electron (only available in Electron context)
const ipc = window?.require ? window.require('electron').ipcRenderer : null

const STATES = {
  idle:  { dc:'var(--teal)', lbl:'en ligne',   speed:'5.5s',  coreCol:'rgba(184,146,74,.18)' },
  think: { dc:'var(--gold)', lbl:'réflexion',  speed:'2.2s',  coreCol:'rgba(184,146,74,.35)' },
  act:   { dc:'#7a9eb8',     lbl:'en action',  speed:'1.4s',  coreCol:'rgba(74,158,184,.3)'  },
  error: { dc:'var(--rose)', lbl:'erreur',     speed:'0.7s',  coreCol:'rgba(184,74,74,.3)'   },
};

const chs = 'abcdefghijklmnopqrstuvwxyz0123456789·—_/∷';

function decrypt(el, final, dur=900){
  let f=0; const tot=dur/16;
  const iv = setInterval(()=>{
    f++;
    const pct = f/tot;
    let s='';
    for(let i=0;i<final.length;i++){
      if(final[i]===' '){ s+=' '; continue; }
      s += i/final.length < pct ? final[i] : chs[Math.floor(Math.random()*chs.length)];
    }
    if(el) el.textContent = s;
    if(f>=tot){ if(el) el.textContent=final; clearInterval(iv); }
  }, 16);
}

function AeonUI() {
  const [logs, setLogs] = useState([])
  const [instruction, setInstruction] = useState('')
  const [typing, setTyping] = useState(false)
  const [subtitle, setSubtitle] = useState('_')
  const ws = useRef(null)
  const messagesEndRef = useRef(null)
  const arcCanvasRef = useRef(null)
  const btxtRef = useRef(null)
  const bdotRef = useRef(null)

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, typing])

  useEffect(() => {
    // Set state function
    const setState = (s) => {
      const st = STATES[s]||STATES.idle;
      if (bdotRef.current) {
        bdotRef.current.style.background  = st.dc;
        bdotRef.current.style.boxShadow   = `0 0 10px ${st.dc}`;
        bdotRef.current.style.animationDuration = st.speed;
      }
      if (btxtRef.current) {
        btxtRef.current.style.color = st.dc;
        decrypt(btxtRef.current, st.lbl, 400);
      }
      document.documentElement.style.setProperty('--breath', st.speed);
    };

    if (typing) {
      setState('think');
    } else {
      setState('idle');
    }
  }, [typing])

  useEffect(() => {
    let reconnectTimeout;
    
    const connect = () => {
      const socket = new WebSocket('ws://127.0.0.1:8000/ws')
      ws.current = socket
      
      socket.onopen = () => {
        setLogs(prev => [...prev, { role: 'agent', content: 'Système Hacktoberfest en ligne. En attente d\'instructions.' }])
      }
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'log') {
            setTyping(false)
            setLogs(prev => [...prev, { role: 'agent', content: `[${data.level}] ${data.message}` }])
          } else if (data.type === 'confirmation_request') {
            setTyping(false)
            setLogs(prev => [...prev, { role: 'agent', content: `[ACTION REQUISE] ${data.action_type}: ${JSON.stringify(data.params)}` }])
          }
        } catch (e) {
          console.error('Erreur WS', e)
        }
      }
      
      socket.onclose = () => {
        setLogs(prev => [...prev, { role: 'agent', content: 'Déconnecté du serveur. Tentative de reconnexion dans 3s...' }])
        reconnectTimeout = setTimeout(connect, 3000)
      }
    }

    connect()

    // Subtitles cycle
    const subtitles = [
      'entité autonome · instance 7',
      'analyse environnement',
      'prêt à agir',
      'en écoute profonde',
      'traitement visuel actif',
      'mémoire de session chargée'
    ];
    let subIdx = 0;
    const subEl = document.getElementById('ent-sub');
    const cycleSubtitle = () => {
      if (subEl) decrypt(subEl, subtitles[subIdx], 900);
      subIdx = (subIdx + 1) % subtitles.length;
    }
    cycleSubtitle();
    const subInterval = setInterval(cycleSubtitle, 4500)
    
    // Canvas animation
    const acv = arcCanvasRef.current;
    let animationId;
    if (acv) {
      const actx = acv.getContext('2d');
      acv.width = 420;
      acv.height = 420;

      const arcs = Array.from({length:11}, ()=>({
        a : Math.random()*Math.PI*2,
        spd: (Math.random()-.5)*.009,
        r  : 85+Math.random()*28,
        len: Math.PI*(.12+Math.random()*.45),
        al : Math.random()*.2+.04,
        col: Math.random()>.55 ? '184,146,74' : '74,140,126',
        w  : Math.random()*1.1+.3
      }));

      const drawArcs = () => {
        actx.clearRect(0,0,420,420);
        const cx=210, cy=210;
        arcs.forEach(a=>{
          a.a += a.spd;
          actx.beginPath();
          actx.arc(cx, cy, a.r, a.a, a.a+a.len);
          const g = actx.createLinearGradient(
            cx+Math.cos(a.a)*a.r,       cy+Math.sin(a.a)*a.r,
            cx+Math.cos(a.a+a.len)*a.r, cy+Math.sin(a.a+a.len)*a.r
          );
          g.addColorStop(0,'transparent');
          g.addColorStop(.5,`rgba(${a.col},${a.al})`);
          g.addColorStop(1,'transparent');
          actx.strokeStyle = g;
          actx.lineWidth   = a.w;
          actx.stroke();
        });
        animationId = requestAnimationFrame(drawArcs);
      };
      drawArcs();
    }
    
    // Cursor logic
    const curEl  = document.getElementById('cur');
    const haloEl = curEl?.querySelector('.cur-halo');
    let mx=0, my=0, rx=0, ry=0;
    
    const onMouseMove = e => {
      mx = e.clientX; my = e.clientY;
      if(curEl) {
        curEl.style.left  = mx+'px';
        curEl.style.top   = my+'px';
      }
    };
    
    let trackId;
    const trackHalo = () => {
      rx += (mx-rx)*.1; ry += (my-ry)*.1;
      trackId = requestAnimationFrame(trackHalo);
    };
    
    document.addEventListener('mousemove', onMouseMove);
    trackHalo();

    // Splash on click
    const pal = ['#b8924a','#4a8c7e','#9a8e82','#b86060','#7a9eb8'];
    const onClick = e => {
      for(let i=0;i<10;i++){
        const p=document.createElement('div');
        p.className='sp';
        const a = Math.PI*2/10*i + Math.random()*.5;
        const d = 18+Math.random()*48;
        const c = pal[Math.floor(Math.random()*pal.length)];
        const s = (2+Math.random()*4)+'px';
        Object.assign(p.style,{
          left:e.clientX+'px', top:e.clientY+'px',
          width:s, height:s,
          background:c, boxShadow:`0 0 6px ${c}`,
          '--dx':Math.cos(a)*d+'px', '--dy':Math.sin(a)*d+'px'
        });
        document.body.appendChild(p);
        setTimeout(()=>p.remove(), 720);
      }
    };
    document.addEventListener('click', onClick);

    // Initial name decrypt
    const entName = document.getElementById('ent-name');
    if (entName) decrypt(entName, 'Hacktoberfest', 1400);
      
    return () => {
      clearInterval(subInterval)
      clearTimeout(reconnectTimeout)
      cancelAnimationFrame(animationId)
      cancelAnimationFrame(trackId)
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('click', onClick)
      if (ws.current) {
        ws.current.onclose = null
        ws.current.close()
      }
    }
  }, [])

  const sendInstruction = (e) => {
    e.preventDefault()
    if (!instruction.trim()) return
    
    setLogs(prev => [...prev, { role: 'user', content: instruction }])
    
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'instruction', instruction }))
      setTyping(true)
    } else {
      setLogs(prev => [...prev, { role: 'agent', content: 'Erreur: Non connecté au serveur.' }])
    }
    
    setInstruction('')
  }

  return (
    <>
      <div id="cur">
        <div className="cur-halo"></div>
        <div className="cur-dot"></div>
      </div>
      <div id="shell">
        {/* L'ÊTRE */}
        <div id="being">
          <div id="orb-sys">
            <div className="membrane mem-1"></div>
            <div className="membrane mem-2"></div>
            <div className="membrane mem-3"></div>

            <div className="orbit-ring or-a"><div className="gem"></div></div>
            <div className="orbit-ring or-b"><div className="gem gem-b"></div></div>

            <div className="ripple"></div>
            <div className="ripple"></div>
            <div className="ripple"></div>

            <canvas id="arc-cv" ref={arcCanvasRef}></canvas>

            <div id="core"></div>
          </div>

          <div id="ent-text">
            <div id="ent-name" data-t="Hacktoberfest">Hacktoberfest</div>
            <div id="ent-sub">_</div>
            <div id="breath-pill">
              <div className="b-dot" id="bdot" ref={bdotRef}></div>
              <span className="b-txt" id="btxt" ref={btxtRef}>en ligne</span>
            </div>
          </div>
        </div>

        {/* CONVERSATION */}
        <div id="chat">

          {/* ── Titlebar draggable ── */}
          <div id="titlebar">
            <div id="titlebar-drag">
              <span id="titlebar-name">Hacktoberfest</span>
              <span id="titlebar-sub">session active</span>
            </div>
            <div id="titlebar-controls">
              <button className="tb-btn" id="btn-pin" title="Épingler" onClick={() => ipc?.send('toggle-always-on-top')}>⊕</button>
              <button className="tb-btn" id="btn-min" title="Réduire" onClick={() => ipc?.send('minimize-window')}>−</button>
              <button className="tb-btn" id="btn-cls" title="Fermer" onClick={() => ipc?.send('close-window')}>×</button>
            </div>
          </div>

          {/* ── Messages ── */}
          <div id="msgs">
            {logs.map((log, i) => {
              const isAgent = log.role === 'agent';
              // Nettoie le préfixe [INFO] résiduel si présent
              const content = log.content.replace(/^\[(INFO|WARNING|ERROR|DEBUG)\]\s*/i, '');
              return (
                <div key={i} className={`msg ${isAgent ? 'msg-a' : 'msg-u'}`}>
                  {isAgent ? (
                    /* Bulle agent */
                    <>
                      <div className="msg-avatar agent-avatar">◉</div>
                      <div className="msg-col">
                        <div className="msg-sender">Hacktoberfest <span className="msg-time">{new Date().toTimeString().slice(0,5)}</span></div>
                        <div className="msg-bubble">{content}</div>
                      </div>
                    </>
                  ) : (
                    /* Bulle utilisateur */
                    <>
                      <div className="msg-col msg-col-right">
                        <div className="msg-sender user-sender">vous <span className="msg-time">{new Date().toTimeString().slice(0,5)}</span></div>
                        <div className="msg-bubble user-bubble">{content}</div>
                      </div>
                      <div className="msg-avatar user-avatar">◈</div>
                    </>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* ── Typing indicator ── */}
          <div id="typing" className={typing ? 'on' : ''}>
            <div className="t-dots">
              <div className="td"></div><div className="td"></div><div className="td"></div>
            </div>
            <span className="t-lbl">Hacktoberfest réfléchit...</span>
          </div>

          {/* ── Input ── */}
          <div id="input-zone">
            <form id="iw" onSubmit={sendInstruction}>
              <input 
                id="inp" 
                type="text" 
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Dis quelque chose à Hacktoberfest…" 
                autoComplete="off" 
                spellCheck="false" 
              />
              <button id="sb" type="submit">↑</button>
            </form>
            <div id="hint">
              <span>Entrée pour envoyer</span>
              <span className="k">↵</span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default AeonUI
