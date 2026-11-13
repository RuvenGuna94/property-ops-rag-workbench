"""Prepare a new monitoring workspace without changing the existing API runtime."""
import argparse
import os
from pathlib import Path
import secrets
import shutil


def stage(api_source, runtime, out):
    api_source, runtime, out = [Path(p).resolve() for p in (api_source, runtime, out)]
    pack = Path(__file__).resolve().parent
    if out.exists():
        raise FileExistsError('Output exists; resume it rather than overwrite.')
    for name in ['asset_api.py', 'prepare_runtime.py']:
        if not (api_source / name).is_file():
            raise FileNotFoundError(name)
    for name in ['data/property_ops.sqlite', '.secrets/identities.json']:
        if not (runtime / name).is_file():
            raise FileNotFoundError(name)
    source = (api_source / 'asset_api.py').read_text(encoding='utf-8')
    marker = 'app = FastAPI(title='
    if source.count(marker) != 1:
        raise ValueError('Unrecognized API constructor; review before adapting.')
    source = source.replace(marker, 'app = FastAPI(telemetry={"tracing": False, "metrics": False, "logs": False, "auto_configure": False}, title=', 1)
    out.mkdir(parents=True)
    (out / 'api-build').mkdir()
    (out / 'evidence/private').mkdir(parents=True)
    private = out / '.secrets'
    private.mkdir(mode=0o700)
    os.chmod(private, 0o700)
    for name in ['collector.yaml', 'compose.yaml', 'dashboard.json', 'datasources.yaml', 'prometheus.yaml', 'tempo.yaml']:
        shutil.copyfile(pack / name, out / name)
        os.chmod(out / name, 0o644)
    for name in ['Dockerfile', 'observed_api.py', 'requirements.txt']:
        shutil.copyfile(pack / name, out / 'api-build' / name)
    shutil.copyfile(api_source / 'prepare_runtime.py', out / 'api-build/prepare_runtime.py')
    (out / 'api-build/asset_api.py').write_text(source, encoding='utf-8')
    env = out / '.env'
    env.write_text('GRAFANA_PASSWORD=' + secrets.token_urlsafe(24) + '\n', encoding='utf-8')
    os.chmod(env, 0o600)
    (out / '.gitignore').write_text('.env\n.secrets/\nevidence/private/\n', encoding='utf-8')
    print('Monitoring workspace prepared. Existing API source, database and credentials unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-source', required=True)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    stage(args.api_source, args.runtime, args.out)
