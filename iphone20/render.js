const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');const path=require('path');
(async()=>{
 const mode=process.argv[2]||'video'; const tl=JSON.parse(fs.readFileSync('timeline.json'));
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
 await p.goto('file://'+path.resolve('render/index.html'));await p.evaluate(tl=>setTL(tl),tl);
 await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(500);
 if(mode==='stills'){const ts=process.argv.slice(3).map(Number);for(const t of ts){await p.evaluate(t=>renderAt(t),t);await p.screenshot({path:`stills/t${t}.jpg`,type:'jpeg',quality:80})}await b.close();return}
 const fps=30,N=Math.ceil(tl.total*fps);
 const ff=spawn('ffmpeg',['-y','-f','image2pipe','-framerate',''+fps,'-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','out/video_silent.mp4'],{stdio:['pipe','ignore','inherit']});
 for(let i=0;i<N;i++){await p.evaluate(t=>renderAt(t),i/fps);const buf=await p.screenshot({type:'jpeg',quality:93});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));if(i%150==0)console.log('frame',i,'/',N)}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done')})();
