"""Tier 0: Launch a bounded, offline, resumable grouped review worker on Mac.
Records PID/status, locks per output, prevents idle sleep, clears API credentials.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/group_review/launch.py --out review/archive/13d-group-review-20260922
"""
import argparse,fcntl,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--supervise',action='store_true');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONIOENCODING='utf-8')
    for key in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','DEEPSEEK_API_KEY','MOONSHOT_API_KEY','KIMI_API_KEY']:env[key]=''
    if not args.supervise:
        with (out/'supervisor.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--supervise'],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        print(json.dumps({'supervisor_pid':child.pid,'output':str(out)}));return
    with (out/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (out/'run.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('prepare.py')),'--out',str(out)],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
            awake=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())])
            status={'status':'running','supervisor_pid':os.getpid(),'worker_pid':child.pid,'caffeinate_pid':awake.pid}
            (out/'launch.json').write_text(json.dumps(status,indent=2))
            try:code=child.wait()
            finally:awake.terminate();awake.wait()
            status.update(status='exited',exit_code=code);(out/'launch.json').write_text(json.dumps(status,indent=2))
if __name__=='__main__':main()
