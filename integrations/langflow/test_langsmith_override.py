import contextlib
import io
import json
import shlex
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from langsmith_override import prepare

class OverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.base=self.root/'compose.yaml';self.base.write_text('services: {}')
        self.env=self.root/'tracing.env'
        self.env.write_text('LANGSMITH_TRACING=true\nLANGSMITH_ENDPOINT=https://api.smith.langchain.com\nLANGSMITH_API_KEY=PRIVATE_TEST_KEY\nLANGSMITH_PROJECT=lab\nLANGSMITH_HIDE_INPUTS=true\nLANGSMITH_HIDE_OUTPUTS=true\nLANGSMITH_HIDE_METADATA=true\n')
        self.labels={'com.docker.compose.service':'langflow','com.docker.compose.project':'openrag',
                     'com.docker.compose.project.working_dir':str(self.root),
                     'com.docker.compose.project.config_files':str(self.base)}

    def test_prepare_only_and_no_secret_output(self):
        out=self.root/'private/override.yaml';capture=io.StringIO()
        with patch('langsmith_override.subprocess.check_output',return_value=json.dumps([{'Config':{'Labels':self.labels}}])) as docker:
            with contextlib.redirect_stdout(capture):prepare('chosen-container',self.env,out)
            docker.assert_called_once_with(['docker','inspect','chosen-container'],text=True)
        self.assertNotIn('PRIVATE_TEST_KEY',capture.getvalue())
        data=json.loads(out.read_text())
        self.assertEqual(set(data['services']),{'langflow'})
        self.assertIn('PRIVATE_TEST_KEY',out.read_text())
        self.assertTrue((out.parent/'restore-command.txt').is_file())

    def test_missing_provenance_does_not_write(self):
        out=self.root/'bad.yaml'
        with patch('langsmith_override.subprocess.check_output',return_value='[{"Config":{"Labels":{}}}]'):
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,out)
        self.assertFalse(out.exists())

    def test_privacy_flags_required(self):
        self.env.write_text(self.env.read_text().replace('LANGSMITH_HIDE_INPUTS=true','LANGSMITH_HIDE_INPUTS=false'))
        with patch('langsmith_override.subprocess.check_output') as docker:
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,self.root/'bad.yaml')
            docker.assert_not_called()

    def test_refresh_preserves_restore_and_backs_up_secret(self):
        out=self.root/'private/override.yaml'
        mocked=json.dumps([{'Config':{'Labels':self.labels}}])
        with patch('langsmith_override.subprocess.check_output',return_value=mocked), contextlib.redirect_stdout(io.StringIO()):
            prepare('chosen-container',self.env,out)
        restore=out.parent/'restore-command.txt';original=restore.read_bytes()
        old=out.read_bytes()
        self.env.write_text(self.env.read_text().replace('https://api.smith.langchain.com','https://apac.api.smith.langchain.com').replace('LANGSMITH_PROJECT=lab','LANGSMITH_PROJECT=property-ops-rag-local'))
        labels={**self.labels,'com.docker.compose.project.config_files':str(self.base)+','+str(out)}
        capture=io.StringIO()
        with patch('langsmith_override.subprocess.check_output',return_value=json.dumps([{'Config':{'Labels':labels}}])),contextlib.redirect_stdout(capture):
            prepare('chosen-container',self.env,out,refresh=True)
        self.assertEqual(restore.read_bytes(),original)
        self.assertEqual(next(out.parent.glob('override.yaml.backup-*')).read_bytes(),old)
        self.assertNotIn('PRIVATE_TEST_KEY',capture.getvalue())
        environment=json.loads(out.read_text())['services']['langflow']['environment']
        self.assertEqual(environment['LANGSMITH_PROJECT'],'property-ops-rag-local')
        self.assertEqual(environment['LANGSMITH_ENDPOINT'],'https://apac.api.smith.langchain.com')
        self.assertIsNone(environment['LANGSMITH_AGENT_ID'])
        apply_line=capture.getvalue().split('APPLY:\n',1)[1].splitlines()[0]
        self.assertEqual(shlex.split(apply_line).count(str(out)),1)

    def test_existing_override_requires_explicit_refresh(self):
        out=self.root/'override.yaml';out.write_text('{}');before=out.read_bytes()
        with patch('langsmith_override.subprocess.check_output',return_value=json.dumps([{'Config':{'Labels':self.labels}}])):
            with self.assertRaises(FileExistsError):prepare('chosen-container',self.env,out)
        self.assertEqual(out.read_bytes(),before)

    def test_refresh_without_original_restore_refuses(self):
        out=self.root/'override.yaml';out.write_text('{}')
        with patch('langsmith_override.subprocess.check_output',return_value=json.dumps([{'Config':{'Labels':self.labels}}])):
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,out,refresh=True)
        self.assertEqual(out.read_text(),'{}')

    def test_untrusted_endpoint_refuses_before_docker(self):
        self.env.write_text(self.env.read_text().replace('https://api.smith.langchain.com','https://unrelated.invalid'))
        with patch('langsmith_override.subprocess.check_output') as docker:
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,self.root/'bad.yaml')
            docker.assert_not_called()

    def test_conflicting_agent_configuration_refuses(self):
        self.env.write_text(self.env.read_text()+'LANGSMITH_AGENT_ID=property-ops-rag\n')
        with patch('langsmith_override.subprocess.check_output') as docker:
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,self.root/'bad.yaml')
            docker.assert_not_called()

    def test_wrong_service_refuses(self):
        labels={**self.labels,'com.docker.compose.service':'opensearch'}
        with patch('langsmith_override.subprocess.check_output',return_value=json.dumps([{'Config':{'Labels':labels}}])):
            with self.assertRaises(ValueError):prepare('chosen-container',self.env,self.root/'bad.yaml')
        self.assertFalse((self.root/'bad.yaml').exists())

if __name__=='__main__':unittest.main(verbosity=2)
