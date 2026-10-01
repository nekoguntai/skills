#!/usr/bin/env python3
"""Shared workflow run ledger and live cleanup gates. Never deletes Git resources."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import workflow_state as policy
from .core import CleanupError, capture_baselines, need
from .git_inventory import InventoryError, capture, owned_resource_present
from .state_io import locked, read, resolved, write, sync_directory
from .target import select_remote, verify_target


def checked(path):
    state = policy.validate(read(path))
    policy.outside_worktrees(state, path)
    return state


def save(path, state):
    policy.validate(state)
    policy.outside_worktrees(state, path)
    state['revision'] += 1
    write(path, state)


def initialize(args):
    path = resolved(args.path)
    cleanup = capture_baselines(str(resolved(args.repo_root)), args.companion_repo)
    state = {
        'workflow': args.workflow, 'schemaVersion': 1, 'revision': 0, 'runId': args.run_id,
        'repoRoot': str(resolved(args.repo_root)), 'targetBranch': args.target_branch,
        'currentSha': args.current_sha, 'targetRemote': select_remote(cleanup['baselines'][0], args.target_remote),
        'iteration': 1, 'maxPasses': args.max_passes if args.max_passes is not None else policy.DEFAULT_BUDGETS[args.workflow],
        'status': 'active', 'stage': 'audit', 'reason': None, 'cleanup': cleanup,
        'resources': [], 'artifacts': [], 'audits': [], 'deliveries': [],
    }
    policy.validate(state)
    policy.outside_worktrees(state, path)
    verify_target(state)
    with locked(path):
        need(not path.exists(), 'run already exists; resume its original baseline')
        write(path, state)
    print(path)


def replace(args):
    path = resolved(args.path)
    candidate = policy.validate(read(resolved(args.candidate)))
    with locked(path):
        current = checked(path)
        policy.transition(current, candidate)
        save(path, candidate)
    print(path)


def archive(args):
    path = resolved(args.path)
    source = resolved(args.source)
    with locked(path):
        state = checked(path)
        need(state['status'] not in {'complete', 'deferred'}, 'terminal run is read-only')
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        destination = path.parent / (path.stem + '-artifacts') / f"{len(state['artifacts']):04d}-{digest}"
        policy.outside_worktrees(state, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation protects an existing archive if a prior process crashed.
        store_artifact(destination, data)
        item = {'source': str(source), 'archive': str(destination), 'sha256': digest,
                'iteration': state['iteration'], 'kind': args.kind}
        state['artifacts'].append(item)
        save(path, state)
    print(json.dumps(item, sort_keys=True))


def store_artifact(destination, data):
    try:
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        need(destination.read_bytes() == data, 'archive collision; preserve it and investigate')
        sync_directory(destination.parent)
        return
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(destination.parent)


def verify_artifacts(args):
    path = resolved(args.path)
    with locked(path):
        state = checked(path)
        policy.verify_artifacts(state)
        latest = {item['source']: item for item in state['artifacts']}
        for source, item in latest.items():
            if Path(source).exists():
                need(hashlib.sha256(Path(source).read_bytes()).hexdigest() == item['sha256'],
                     'source changed since archive; archive final bytes before cleanup')
    print('artifacts verified')


def verify_cleanup(args):
    path = resolved(args.path)
    with locked(path):
        state = checked(path)
        collaborator_changes = policy.verify_cleanup(state)
        checks = state['cleanup']['checks']
        if not any(c['iteration'] == state['iteration'] for c in checks):
            checks.append({'iteration': state['iteration'],
                           'verifiedAt': datetime.now(timezone.utc).isoformat(),
                           'repositories': [b['root'] for b in state['cleanup']['baselines']]})
            save(path, state)
    print('cleanup verified')
    for root, changes in collaborator_changes.items():
        for change in changes:
            print(f'collaborator change (not owned, left in place) in {root}: {change}')


def validate(args):
    checked(resolved(args.path))
    print('valid')


def summary(args):
    state = checked(resolved(args.path))
    result = {key: state[key] for key in ('runId', 'status', 'stage', 'iteration', 'maxPasses', 'reason')}
    result['remainingResources'] = [r for r in state['resources'] if r['status'] != 'cleaned']
    result['cleanupChecks'] = state['cleanup']['checks']
    print(json.dumps(result, indent=2))


def stale(args):
    """List resources earlier loop runs reserved for this repository and never cleaned.

    These are this user's own forgotten branches and worktrees (for example
    after a context compaction or an interrupted run), unlike collaborator
    changes. Each still needs pr-delivery's merge, CI, and dirty-tree checks
    before removal; this command only reports and never deletes.
    """
    root = str(Path(args.repo_root).expanduser().resolve())
    inventory = capture(root)
    found = []
    for path in sorted(Path(args.state_root).expanduser().rglob('*.json')):
        if any(part.endswith('-artifacts') for part in path.parts):
            continue
        try:
            state = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(state, dict) or not isinstance(state.get('resources'), list):
            continue
        for resource in state['resources']:
            if not isinstance(resource, dict) or resource.get('repoRoot') != root or resource.get('status') == 'cleaned':
                continue
            if owned_resource_present(resource, inventory):
                found.append({'statePath': str(path), 'runId': state.get('runId'), 'workflow': state.get('workflow'),
                              'runStatus': state.get('status'), 'kind': resource.get('kind'),
                              'identifier': resource.get('identifier'), 'remote': resource.get('remote'),
                              'resourceStatus': resource.get('status')})
    print(json.dumps(found, indent=2, sort_keys=True))


def parser(default_workflow=None):
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    for name in ('path', 'run-id', 'repo-root', 'target-branch', 'current-sha'):
        init.add_argument('--' + name, required=True)
    init.add_argument('--target-remote')
    init.add_argument('--workflow', choices=sorted(policy.WORKFLOWS))
    init.add_argument('--max-passes', type=int)
    init.add_argument('--companion-repo', action='append', default=[])
    init.set_defaults(handler=initialize, workflow=default_workflow)
    stale_command = commands.add_parser('stale')
    stale_command.add_argument('--repo-root', required=True)
    stale_command.add_argument('--state-root', default=str(Path.home() / '.codex' / 'state'))
    stale_command.set_defaults(handler=stale)
    for name, handler in [('replace', replace), ('archive', archive), ('verify-cleanup', verify_cleanup),
                          ('verify-artifacts', verify_artifacts), ('validate', validate), ('summary', summary)]:
        command = commands.add_parser(name)
        command.add_argument('--path', required=True)
        if name == 'replace':
            command.add_argument('--candidate', required=True)
        if name == 'archive':
            command.add_argument('--source', required=True)
            command.add_argument('--kind', choices=['report', 'history', 'plan', 'evidence'], required=True)
        command.set_defaults(handler=handler)
    return root


def main(default_workflow=None):
    try:
        args = parser(default_workflow).parse_args()
        if args.command == "init":
            need(args.workflow is not None, "init requires --workflow")
            need(args.max_passes is None or args.max_passes > 0, "max-passes must be positive")
        args.handler(args)
    except (CleanupError, InventoryError, OSError, ValueError) as error:
        print(f'loop state error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
