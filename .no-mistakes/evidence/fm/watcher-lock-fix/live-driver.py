import os, pathlib, subprocess, time, signal, json
root=pathlib.Path.cwd(); base=root/'.watch-validation'; evidence=pathlib.Path('/Users/earljustinmangulabnan/.no-mistakes/evidence/01M2SKHNJ750141N4FDWX45FM2')
results=[]
def case(name,seed=None,mode='arm'):
 h=base/(name+'-retry'); s=h/'state'; s.mkdir(parents=True); (h/'config').mkdir(); (h/'data').mkdir()
 env=os.environ.copy(); env.update(FM_HOME=str(h),FM_STATE_OVERRIDE=str(s),FM_ROOT_OVERRIDE=str(h),FM_BACKEND='tmux',TMUX=str(h/'absent-tmux')+',0,0',FM_POLL='1',FM_SIGNAL_GRACE='1',FM_CHECK_INTERVAL='999999',FM_HEARTBEAT='999999',TMPDIR=str(base/'tmp'))
 for k in ['FM_TASK_ID','TASKS_AXI_FILE','TASKS_AXI_BACKEND']: env.pop(k,None)
 lock=s/'.watch.lock'
 if seed:
  owner=s/'.watch.lock.owner.seed';owner.mkdir();(owner/'pid').write_text(str(os.getpid() if seed=='live' else 999999)+'\n');lock.symlink_to(owner)
  if seed.startswith('foreign'):
   (owner/'fm-home').write_text(str(base/'other-home')+'\n');(s/'.last-watcher-beat').touch()
   if seed=='foreign-stale': os.utime(s/'.last-watcher-beat',(1,1))
 out=evidence/(name+'.log'); f=out.open('w'); cmd=[str(root/'bin'/('fm-watch-arm.sh' if mode=='arm' else 'fm-watch.sh'))]; cmd += ['--restart'] if name=='dead-partial-restart' else []; p=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 snapshots=[]; partial=False; deadline=time.time()+60
 try:
  while time.time()<deadline:
   if lock.exists() and (lock/'pid').exists() and (lock/'pid').read_text().strip() not in [str(os.getpid()),'999999']:
    try: record={k:(lock/k).read_text().strip() for k in ['pid','fm-home','watcher-path','pid-identity']}
    except FileNotFoundError: record={}
    if record:
     partial |= not all(record.values())
     if not snapshots: snapshots.append(record)
   txt=out.read_text()
   if 'watcher: started' in txt or p.poll() is not None: break
   time.sleep(.005)
  txt=out.read_text(); rc=p.poll()
  if seed in ['live','foreign-fresh']:
   ok=rc==0 and 'already running' in txt and (lock/'pid').read_text().strip()==str(os.getpid() if seed=='live' else 999999)
  else: ok=not partial and ('watcher: started' in txt or ('check: rearm-resurface' in txt and rc==0))
  if not seed and ok:
   peer=subprocess.run([str(root/'bin/fm-watch.sh')],env=env,capture_output=True,text=True,timeout=15)
   f.write('\nSECOND START rc='+str(peer.returncode)+'\n'+peer.stdout+peer.stderr);f.flush()
   ok &= peer.returncode==0 and 'already running pid' in peer.stdout
  f.write('\nOBSERVED OWNER RECORDS '+json.dumps(snapshots)+'\npartial_record_observed='+str(partial)+'\n'); f.flush()
  results.append({'name':name,'pass':bool(ok),'rc_before_cleanup':rc,'records':snapshots})
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  f.close()
for args in [('clean-start',None,'arm'),('dead-partial-autoarm','dead','arm'),('dead-partial-restart','dead','arm'),('live-partial-held','live','watch'),('foreign-fresh-held','foreign-fresh','watch'),('foreign-stale-recovered','foreign-stale','arm')]:
 case(*args)
print(json.dumps(results,indent=2));(evidence/'live-results.json').write_text(json.dumps(results,indent=2))
assert all(x['pass'] for x in results)
