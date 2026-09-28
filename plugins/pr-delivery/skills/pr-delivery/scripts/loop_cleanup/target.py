"""Read the authoritative workflow target without mutating Git refs."""
import subprocess

from .core import CleanupError, need


def select_remote(baseline, requested):
    names = {r['remote'] for r in baseline['remote_branches']}
    if requested is not None:
        need(requested in names, 'target remote is not in baseline')
        return requested
    if 'origin' in names:
        return 'origin'
    need(len(names) <= 1, 'multiple remotes require --target-remote')
    return next(iter(names), None)


def live_sha(state):
    ref = 'refs/heads/' + state['targetBranch']
    remote = state['targetRemote']
    if remote is None:
        args = ['rev-parse', '--verify', ref]
    else:
        args = ['ls-remote', '--heads', '--', remote, ref]
    try:
        result = subprocess.run(['git', '-C', state['repoRoot'], *args],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CleanupError('target SHA inspection failed or timed out') from error
    need(result.returncode == 0, 'target SHA inspection failed')
    if remote is None:
        return result.stdout.strip()
    matches = [line.split('\t', 1)[0] for line in result.stdout.splitlines()
               if line.endswith('\t' + ref)]
    need(len(matches) == 1, 'target branch is missing or ambiguous on remote')
    return matches[0]


def verify_target(state):
    need(live_sha(state) == state['currentSha'],
         'target branch advanced; refresh currentSha and audit evidence before cleanup/decision')
