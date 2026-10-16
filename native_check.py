"""Windows-only native evidence using source from this checkout. Files are retained."""
import pathlib,tempfile,subprocess,sys,os,json,shutil
if os.name != 'nt':
    raise SystemExit('Native check requires Windows; use unittest on other platforms.')
root=pathlib.Path(tempfile.mkdtemp(prefix='lesson43-native-ci-'))
shutil.copyfile(pathlib.Path(__file__).parent/'local_try.py',root/'local_try.py')
def run(label,args,expected=0,timeout=1200):
    print('\n### CMD: '+label,flush=True)
    result=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    print(result.stdout,end='',flush=True)
    print('### EXIT: '+str(result.returncode),flush=True)
    if result.returncode != expected: raise SystemExit('Unexpected native exit')
import urllib.request,hashlib,zipfile
archive=root/'ollama-v0.40.5.zip'
print('Recorder downloads official standalone Ollama v0.40.5 into its NEW temporary runtime folder. No installer or existing-profile change.',flush=True)
urllib.request.urlretrieve('https://github.com/ollama/ollama/releases/download/v0.40.5/ollama-windows-amd64.zip',archive)
digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
if digest!='5134ce7e3bc8e94d0494721c799ec293b429450d0c52461b0ee3647dd3bb4bb7':raise SystemExit('Official archive hash mismatch')
print('Verified official standalone archive SHA256:',digest,flush=True)
runtime=root/'trusted-runtime';runtime.mkdir()
with zipfile.ZipFile(archive) as z:
 for info in z.infolist():
  name=pathlib.PurePosixPath(info.filename.replace('\\','/'))
  if name.is_absolute() or '..' in name.parts or ':' in info.filename or ((info.external_attr>>16)&0o170000)==0o120000:raise SystemExit('Unsafe archive member')
 z.extractall(runtime)
binaries=list(runtime.rglob('ollama.exe'))
if len(binaries)!=1:raise SystemExit('Expected one standalone binary')
binary=binaries[0]
run('python local_try.py FULL_PATH_TO_TRUSTED_OLLAMA_BINARY',[sys.executable,'local_try.py',str(binary)])
before={str(p.relative_to(root/'local-ai-practice')):(hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),p.stat().st_mtime_ns) for p in (root/'local-ai-practice').rglob('*') if p.is_file()}
run('python local_try.py FULL_PATH_TO_TRUSTED_OLLAMA_BINARY',[sys.executable,'local_try.py',str(binary)],2)
after={str(p.relative_to(root/'local-ai-practice')):(hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),p.stat().st_mtime_ns) for p in (root/'local-ai-practice').rglob('*') if p.is_file()}
assert before==after,'Repeat changed lesson files'
answers=[json.loads((root/'local-ai-practice'/f'answer{i}.json').read_text())['response'] for i in [1,2]]
print('Reviewer known-answer checks:', 'Paris' in answers[0], 'prime' in answers[1].lower() and not any(x in answers[1].lower() for x in ['not prime','not a prime','composite']),flush=True)
for name in ['version.json','models.json','memory.json','answer1.json','answer2.json']:
    print(name,(root/'local-ai-practice'/name).read_text(encoding='utf-8'),flush=True)
print('Native CI evidence retained in the ephemeral runner workspace. No runtime/model cleanup attempted.',flush=True)
