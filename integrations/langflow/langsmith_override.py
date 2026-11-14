"""Prepare private Compose overrides and reviewable commands. Never restart Docker."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess

REQUIRED={'LANGSMITH_TRACING','LANGSMITH_ENDPOINT','LANGSMITH_API_KEY','LANGSMITH_PROJECT',
          'LANGSMITH_HIDE_INPUTS','LANGSMITH_HIDE_OUTPUTS','LANGSMITH_HIDE_METADATA'}

CONFLICTS={'LANGSMITH_AGENT_ID','LANGSMITH_AGENT_ENVIRONMENT',
           'LANGCHAIN_PROJECT','LANGCHAIN_SESSION','LANGCHAIN_ENDPOINT'}
ENDPOINTS={'https://api.smith.langchain.com','https://eu.api.smith.langchain.com',
           'https://apac.api.smith.langchain.com','https://aws.api.smith.langchain.com'}

def prepare(container,envfile,out,refresh=False):
    envfile,out=Path(envfile).resolve(),Path(out).resolve()
    values={}
    for line in envfile.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        k,sep,v=line.partition('=')
        if not sep or k not in REQUIRED or k in values: raise ValueError('Unsupported or duplicate environment field.')
        values[k]=v.strip()
    if set(values)!=REQUIRED or not all(values.values()): raise ValueError('Complete all required fields.')
    if values['LANGSMITH_API_KEY']=='PASTE_KEY_PRIVATELY': raise ValueError('API key placeholder remains.')
    if values['LANGSMITH_ENDPOINT'] not in ENDPOINTS:
        raise ValueError('Use the exact regional HTTPS API endpoint without a trailing slash.')
    for k in ['LANGSMITH_TRACING','LANGSMITH_HIDE_INPUTS','LANGSMITH_HIDE_OUTPUTS','LANGSMITH_HIDE_METADATA']:
        if values[k].lower()!='true': raise ValueError('Initial tracing requires all privacy flags true.')
    inspected=json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
    labels=inspected['Config'].get('Labels',{})
    service=labels.get('com.docker.compose.service')
    project=labels.get('com.docker.compose.project')
    workdir=labels.get('com.docker.compose.project.working_dir')
    files=labels.get('com.docker.compose.project.config_files','').split(',')
    if not service or 'langflow' not in service.lower() or not project or not workdir or not Path(workdir).is_dir() or not all(Path(f).is_file() for f in files):
        raise ValueError('Compose provenance is missing or paths are not accessible in this shell. No files changed.')
    restore_path=out.parent/'restore-command.txt'
    commands_path=out.parent/'langsmith-commands.txt'
    if out.exists() and not refresh: raise FileExistsError('Override exists; review before using --refresh. Retain the original restore command.')
    if refresh and (not out.is_file() or not restore_path.is_file()):
        raise ValueError('Refresh needs the existing override and original restore-command.txt. No files changed.')
    override={'services':{service:{'environment':{}}}}
    if refresh:
        try: override=json.loads(out.read_text(encoding='utf-8'))
        except (ValueError,UnicodeError):
            raise ValueError('Refresh supports helper-generated JSON-form YAML only; review other YAML privately.') from None
        if set(override.get('services',{}))!={service} or not isinstance(override['services'][service].get('environment'),dict):
            raise ValueError('Existing override does not match the selected Langflow service. No files changed.')
    files=[f for f in files if Path(f).resolve()!=out]
    if not files: raise ValueError('Original Compose files unavailable. No files changed.')
    out.parent.mkdir(parents=True,exist_ok=True)
    os.chmod(out.parent,0o700)
    # JSON is valid YAML. Dollar escaping prevents Compose interpolation of secret content.
    override['services'][service]['environment'].update({k:v.replace('$','$$') for k,v in values.items()})
    # Compose null values unset inherited agent variables and legacy aliases.
    override['services'][service]['environment'].update({k:None for k in CONFLICTS})
    if refresh:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        for path in (out,commands_path):
            if path.exists():
                backup=path.with_name(path.name+'.backup-'+stamp)
                with backup.open('xb') as stream: stream.write(path.read_bytes())
                os.chmod(backup,0o600)
    out.write_text(json.dumps(override,indent=2),encoding='utf-8');os.chmod(out,0o600)
    base=['docker','compose','--project-directory',workdir,'-p',project]
    for f in files: base+=['-f',f]
    prefix='cd '+shlex.quote(workdir)+' && '
    apply=prefix+shlex.join(base+['-f',str(out),'up','-d','--no-deps','--force-recreate',service])
    restore=prefix+shlex.join(base+['up','-d','--no-deps','--force-recreate',service])
    if not restore_path.exists():
        with restore_path.open('x',encoding='utf-8') as stream: stream.write(restore+'\n')
    os.chmod(restore_path,0o600)
    commands_path.write_text('APPLY:\n'+apply+'\n\nOriginal restore command: restore-command.txt\n',encoding='utf-8')
    os.chmod(commands_path,0o600)
    print('Selected Compose project:',project,'service:',service)
    print('Review the selected service before running. Override contains a secret; do not print it.')
    print('APPLY:\n'+apply)
    print('Original restore-command.txt retained. No containers restarted.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--container',required=True);p.add_argument('--env-file',required=True);p.add_argument('--out',required=True)
    p.add_argument('--refresh',action='store_true',help='Back up an existing helper-generated override; retain its original restore command.')
    a=p.parse_args();prepare(a.container,a.env_file,a.out,refresh=a.refresh)
