import contextlib
import io
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest import mock
import local_try as tool

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def link(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError:self.skipTest('Symlink creation unavailable')

class Workspace(Base):
    def test_new_structure(self):
        root=tool.create_workspace(self.root)
        self.assertEqual(sorted(p.name for p in root.iterdir()),['home','local-data','models'])
    def test_repeat_preserves_bytes_mtimes(self):
        root=tool.create_workspace(self.root);keep=root/'models'/'keep';keep.write_bytes(b'KEEP')
        before=keep.read_bytes(),keep.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):tool.create_workspace(self.root)
        self.assertEqual(before,(keep.read_bytes(),keep.stat().st_mtime_ns))
    def test_file_collision(self):
        keep=self.root/'local-ai-practice';keep.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):tool.create_workspace(self.root)
        self.assertEqual(keep.read_bytes(),b'KEEP')
    def test_linked_parent(self):
        link=self.root/'link';self.link(link,self.root,True)
        with self.assertRaises(OSError):tool.create_workspace(link)
        self.assertFalse((self.root/'local-ai-practice').exists())
    def test_linked_output(self):
        link=self.root/'local-ai-practice';self.link(link,self.root,True)
        with self.assertRaises(FileExistsError):tool.create_workspace(self.root)
    def test_traversal(self):
        with self.assertRaises(OSError):tool.create_workspace(self.root/'..'/self.root.name)
    def test_save_never_overwrites(self):
        tool.save(self.root,'result.json',{'a':1});target=self.root/'result.json';before=target.read_bytes(),target.stat().st_mtime_ns
        with self.assertRaises(FileExistsError):tool.save(self.root,'result.json',{'a':2})
        self.assertEqual(before,(target.read_bytes(),target.stat().st_mtime_ns))

class Binary(Base):
    def setUp(self):super().setUp();self.bin=self.root/'binary';self.bin.write_bytes(b'fictional')
    def test_ordinary(self):self.assertEqual(tool.ordinary(self.bin),self.bin)
    def test_hardlink(self):
        link=self.root/'hard';os.link(self.bin,link)
        with self.assertRaises(OSError):tool.ordinary(link)
    def test_symlink_and_loop(self):
        link=self.root/'link';self.link(link,self.bin)
        with self.assertRaises(OSError):tool.ordinary(link)
        link.unlink();self.link(link,link)
        with self.assertRaises(OSError):tool.ordinary(link)
    def test_directory_as_binary(self):
        with self.assertRaises(OSError):tool.ordinary(self.root)
    def test_pipe(self):
        if not hasattr(os,'mkfifo'):self.skipTest('Unix pipe unavailable')
        pipe=self.root/'pipe';os.mkfifo(pipe)
        with self.assertRaises(OSError):tool.ordinary(pipe)

class Environment(Base):
    def test_isolates_without_mutating_parent(self):
        with mock.patch.dict(os.environ,{'OLLAMA_HOST':'remote.invalid','OLLAMA_MODELS':'old-models','OLLAMA_CUSTOM':'old','HOME':'old-home','KEEP':'yes'},clear=True):
            before=dict(os.environ);env=tool.server_environment(self.root)
            self.assertEqual(os.environ,before)
            self.assertEqual(env['OLLAMA_HOST'],tool.HOST);self.assertEqual(env['OLLAMA_NO_CLOUD'],'1')
            self.assertEqual(env['OLLAMA_MODELS'],str(self.root/'models'));self.assertEqual(env['HOME'],str(self.root/'home'))
            self.assertEqual(env['USERPROFILE'],str(self.root/'home'));self.assertNotIn('OLLAMA_CUSTOM',env);self.assertEqual(env['KEEP'],'yes')
    def test_fixed_model_and_prompts(self):
        self.assertEqual(tool.MODEL,'llama3.2:1b');self.assertNotIn('cloud',tool.MODEL)
        self.assertEqual(len(tool.QUESTIONS),2)
    def test_17_prime_calculation(self):self.assertFalse(any(17%d==0 for d in range(2,int(17**.5)+1)))

class API(unittest.TestCase):
    def result(self,raw):
        response=mock.MagicMock();response.__enter__.return_value.read.return_value=raw
        opener=mock.Mock();opener.open.return_value=response
        return opener
    def test_local_endpoint_and_proxy_disabled(self):
        opener=self.result(b'{"version":"test"}')
        with mock.patch('urllib.request.build_opener',return_value=opener),mock.patch('urllib.request.ProxyHandler') as proxy:
            self.assertEqual(tool.request('/api/version'),{'version':'test'});proxy.assert_called_once_with({})
        self.assertEqual(opener.open.call_args.args[0].full_url,'http://127.0.0.1:11439/api/version')
    def test_rejects_arbitrary_url(self):
        with self.assertRaises(ValueError):tool.request('https://remote.invalid')
    def test_json_error(self):
        with mock.patch('urllib.request.build_opener',return_value=self.result(b'{"error":"refused"}')):
            with self.assertRaises(ValueError):tool.request('/api/version')
    def test_nonobject(self):
        with mock.patch('urllib.request.build_opener',return_value=self.result(b'[]')):
            with self.assertRaises(ValueError):tool.request('/api/tags')
    def test_oversize(self):
        with mock.patch('urllib.request.build_opener',return_value=self.result(b'x'*1_000_001)):
            with self.assertRaises(ValueError):tool.request('/api/tags')
    def test_generate_payload(self):
        opener=self.result(b'{"done":true,"response":"test"}')
        with mock.patch('urllib.request.build_opener',return_value=opener):tool.request('/api/generate',{'model':tool.MODEL,'stream':False})
        self.assertIn(b'"stream": false',opener.open.call_args.args[0].data)

class Lifecycle(Base):
    def test_no_cloud_confirmation_no_request(self):
        log=self.root/'log';log.write_text('old version')
        process=mock.Mock();process.poll.return_value=None
        with mock.patch.object(tool,'request') as request:
            with self.assertRaises(RuntimeError):tool.wait_ready(process,log,seconds=0)
            request.assert_not_called()
    def test_confirmed_ready(self):
        log=self.root/'log';log.write_text('Ollama cloud disabled: true')
        process=mock.Mock();process.poll.return_value=None
        with mock.patch.object(tool,'request',return_value={'version':'test'}) as request:
            self.assertEqual(tool.wait_ready(process,log),{'version':'test'})
            request.assert_called_once_with('/api/version',timeout=2)
    def test_dead_server_stops(self):
        process=mock.Mock();process.poll.return_value=1
        with self.assertRaises(RuntimeError):tool.wait_ready(process,self.root/'absent')
    def test_only_owned_process_terminated(self):
        process=mock.Mock();process.poll.return_value=None
        tool.stop_owned(process);process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=15);process.kill.assert_not_called()
    def test_force_owned_only_after_timeout(self):
        process=mock.Mock();process.poll.return_value=None;process.wait.side_effect=[subprocess.TimeoutExpired('owned',15),0]
        tool.stop_owned(process);process.kill.assert_called_once()
    def test_already_exited_untouched(self):
        process=mock.Mock();process.poll.return_value=0
        tool.stop_owned(process);process.terminate.assert_not_called()
    def test_port_busy_refuses_before_workspace(self):
        with mock.patch.object(tool,'ordinary',return_value=self.root/'binary'),mock.patch('os.access',return_value=True),mock.patch('socket.socket') as socket_mock,mock.patch.object(tool,'create_workspace') as create:
            socket_mock.return_value.__enter__.return_value.bind.side_effect=OSError('busy')
            with self.assertRaises(OSError):tool.run('binary',self.root)
            create.assert_not_called()
    def test_failed_pull_stops_owned_server_and_retains_files(self):
        binary=self.root/'ollama';binary.write_bytes(b'fictional');binary.chmod(0o700)
        process=mock.Mock();process.poll.return_value=None
        with mock.patch('subprocess.Popen',return_value=process),mock.patch.object(tool,'wait_ready',return_value={'version':'test'}),mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,b'download refused')),mock.patch('socket.socket'),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):tool.run(binary,self.root)
        process.terminate.assert_called_once()
        self.assertEqual((self.root/'local-ai-practice'/'pull.log').read_bytes(),b'download refused')
        self.assertTrue((self.root/'local-ai-practice'/'models').is_dir())

    def test_failed_startup_does_not_pull(self):
        binary=self.root/'ollama';binary.write_bytes(b'fictional');binary.chmod(0o700)
        process=mock.Mock();process.poll.return_value=None
        with mock.patch('subprocess.Popen',return_value=process),mock.patch.object(tool,'wait_ready',side_effect=RuntimeError('no cloud confirmation')),mock.patch('subprocess.run') as pull,mock.patch('socket.socket'),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):tool.run(binary,self.root)
            pull.assert_not_called()
        process.terminate.assert_called_once()

    def test_usage(self):
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(tool.main(['script']),2)

if __name__=='__main__':unittest.main()
