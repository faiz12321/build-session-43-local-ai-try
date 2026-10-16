"""Try a locally installed Ollama binary in a NEW lesson-owned workspace.
No install, uninstall, recursive delete or reset. Only fictional prompts.
Requires a trusted current Ollama binary supporting OLLAMA_NO_CLOUD=1.
"""
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
import urllib.request

MODEL = 'llama3.2:1b'
HOST = '127.0.0.1:11439'
QUESTIONS = ['What is the capital of France? Answer in one short sentence.',
             'Is 17 a prime number? Answer in one short sentence.']


def ordinary(value, directory=False):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Links/reparse points are unsupported.')
    info = path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode): raise OSError('Expected an ordinary directory.')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise OSError('Expected an ordinary singly linked file.')
    return path


def create_workspace(base):
    base = ordinary(base, directory=True)
    root = base/'local-ai-practice'
    root.mkdir()  # existing paths refuse, no reset or cleanup
    for name in ['models', 'home', 'local-data']:
        (root/name).mkdir()
    return root


def server_environment(root):
    env = {key:value for key,value in os.environ.items() if not key.upper().startswith('OLLAMA_')}
    env.update(OLLAMA_MODELS=str(root/'models'), OLLAMA_HOST=HOST,
               OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1', OLLAMA_CONTEXT_LENGTH='2048',
               HOME=str(root/'home'), USERPROFILE=str(root/'home'),
               LOCALAPPDATA=str(root/'local-data'), APPDATA=str(root/'local-data'),
               XDG_CONFIG_HOME=str(root/'home'), NO_PROXY='127.0.0.1,localhost')
    return env


def request(path, payload=None, timeout=180):
    if path not in ['/api/version','/api/tags','/api/generate','/api/ps']:
        raise ValueError('Unsupported lesson endpoint.')
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://'+HOST+path,data=data,
                                 headers={'Content-Type':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=timeout) as response:
        raw = response.read(1_000_001)
    if len(raw)>1_000_000: raise ValueError('Response exceeds lesson limit.')
    result=json.loads(raw)
    if not isinstance(result,dict): raise ValueError('Expected an API object.')
    if result.get('error'): raise ValueError('Ollama returned an error: '+str(result['error']))
    return result


def save(root, name, value):
    with (root/name).open('x',encoding='utf-8') as handle:
        json.dump(value,handle,indent=2)
        handle.write('\n')


def wait_ready(process, log, seconds=30):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if process.poll() is not None: raise RuntimeError('Lesson server stopped; inspect its local log.')
        text=log.read_text(encoding='utf-8',errors='replace')
        # Official FAQ says this confirms the server accepted local-only configuration.
        if 'Ollama cloud disabled: true' in text:
            try: return request('/api/version',timeout=2)
            except (OSError,ValueError): pass
        time.sleep(.25)
    raise RuntimeError('Could not verify cloud-disabled lesson server. No model or prompt sent.')


def stop_owned(process):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=15)


def run(binary, base):
    binary=ordinary(binary)
    if not os.access(binary,os.X_OK): raise OSError('Ollama binary is not executable.')
    # Refuse a currently occupied port instead of talking to someone else's server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',11439))
    root=create_workspace(base)
    print('Created NEW local-ai-practice. Model download uses disk/network; no automatic deletion.',flush=True)
    env=server_environment(root)
    log=root/'server.log'
    with log.open('xb') as output:
        process=subprocess.Popen([str(binary),'serve'],env=env,cwd=root,
                                 stdout=output,stderr=subprocess.STDOUT)
        try:
            version=wait_ready(process,log)
            save(root,'version.json',version)
            print('Verified lesson server reports cloud disabled. Version:',version.get('version'),flush=True)
            pull=subprocess.run([str(binary),'pull',MODEL],env=env,cwd=root,
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
            with (root/'pull.log').open('xb') as handle:handle.write(pull.stdout)
            if pull.returncode:raise RuntimeError('Model pull failed; inspect pull.log. Partial files remain.')
            tags=request('/api/tags')
            matches=[m for m in tags.get('models',[]) if m.get('name')==MODEL]
            if len(matches)!=1 or not matches[0].get('digest'):
                raise ValueError('Expected one downloaded local model with a digest.')
            save(root,'models.json',tags)
            print('Downloaded local model:',MODEL,'digest:',matches[0]['digest'],flush=True)
            for i,prompt in enumerate(QUESTIONS,1):
                result=request('/api/generate',{'model':MODEL,'prompt':prompt,'stream':False,
                                                 'keep_alive':'1m','options':{'num_predict':80,'temperature':0}})
                if not result.get('done') or not isinstance(result.get('response'),str) or not result['response'].strip():
                    raise ValueError('No complete model answer.')
                save(root,f'answer{i}.json',result)
                print('Question:',prompt,flush=True)
                print('Recorded answer:',result['response'].strip(),flush=True)
            save(root,'memory.json',request('/api/ps'))
            total=sum(p.stat().st_size for p in (root/'models').rglob('*') if p.is_file())
            print('Logical model-file bytes:',total,'(not physical allocation or total program cost)',flush=True)
            print('Answers are model output, not verified truth. 17 is prime: only 2,3,4 need testing.',flush=True)
        finally:
            stop_owned(process)
    print('Stopped the owned server process. Files remain in local-ai-practice for your review.',flush=True)
    print('No uninstall/delete/reset ran. Child runners, OS logs/caches and other software are not a restoration guarantee.',flush=True)


def main(argv):
    if len(argv)!=2:
        print('Usage: python local_try.py FULL_PATH_TO_TRUSTED_OLLAMA_BINARY')
        return 2
    try:run(argv[1],Path(__file__).absolute().parent)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('Stopped:',error)
        print('Partial lesson files may remain. No automatic reset or recursive deletion.')
        return 2
    return 0


if __name__=='__main__':sys.exit(main(sys.argv))
