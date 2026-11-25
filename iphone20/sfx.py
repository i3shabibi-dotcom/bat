import numpy as np,json,wave
SR=48000
tl=json.load(open('timeline.json')); T=tl['total']; N=int(T*SR)+SR
mix=np.zeros(N)
rng=np.random.default_rng(7)
def env(n,a,r):
    e=np.ones(n); a=int(a*SR); r=int(r*SR)
    e[:a]=np.linspace(0,1,a); e[-r:]*=np.linspace(1,0,r)**2; return e
def lp(x,alpha):
    y=np.empty_like(x); acc=0
    for i in range(len(x)): acc+=alpha[i]*(x[i]-acc); y[i]=acc
    return y
def whoosh(d=0.55,up=True):
    n=int(d*SR); x=rng.standard_normal(n)
    f=np.linspace(.02,.35,n) if up else np.linspace(.35,.02,n)
    sweep=np.sin(np.linspace(0,np.pi,n))
    return lp(x,f*sweep+.005)*env(n,d*.55,d*.4)*0.9
def hit(d=0.9):
    n=int(d*SR); t=np.arange(n)/SR; f=55*np.exp(-t*3)+38
    s=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*4.5)
    s+=lp(rng.standard_normal(n),np.full(n,.08))*np.exp(-t*25)*.6
    return s
def tick(f=2400,d=0.05):
    n=int(d*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*f*t)*np.exp(-t*90)*.5
def riser(d=1.2):
    n=int(d*SR); t=np.arange(n)/SR; f=200+900*(t/d)**2
    s=np.sin(2*np.pi*np.cumsum(f)/SR)*.15+lp(rng.standard_normal(n),np.linspace(.01,.4,n))*.8
    return s*np.linspace(0,1,n)**2
def add(sig,t,g):
    i=int(t*SR); j=min(N,i+len(sig)); 
    if i<0: sig=sig[-i:]; i=0
    mix[i:j]+=sig[:j-i]*g
S=tl['scenes']
add(hit(),0.15,0.55); add(whoosh(.5),0.0,.35); add(tick(1800),0.9,.4)
for k,s in enumerate(S[1:],1):
    add(whoosh(.55,k%2==0),s['start']-0.3,.28)
    add(tick(2600),s['start']+0.05,.3)
# scene-specific
o=S[1]; [add(tick(1500+i*40,.03),o['start']+0.3+2.2*(1-(1-i/20)**0.5)*0+ i*0.11,.18) for i in range(20)]
d=S[4]; add(hit(.6),d['start']+(d['end']-d['start'])*.18,.35)
for s in S:
    if s['id']=='tioled': add(whoosh(.5),s['start']+s['splitT']-0.35,.3)
c=S[-1]; add(riser(1.0),S[-2]['end']-0.9,.25); add(hit(.7),c['start']+0.05,.4)
mix=np.tanh(mix*1.2)*0.5
w=wave.open('out/sfx.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close(); print('sfx ok',T)
