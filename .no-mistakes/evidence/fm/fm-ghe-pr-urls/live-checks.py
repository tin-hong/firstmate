import os, subprocess, pathlib, shutil
root=pathlib.Path.cwd()
base=root/'.test-ghe-gate/live'
evidence=pathlib.Path('/home/tin/.no-mistakes/evidence/01M57VPA183NS321E80CVYR61Z/live-cli-transcript.log')
(base/'home/config').mkdir(parents=True,exist_ok=True)
(base/'home/state').mkdir(parents=True,exist_ok=True)
(base/'home/config/github-hosts').unlink(missing_ok=True)
(base/'gh-config').mkdir(exist_ok=True)
(base/'code/bin').mkdir(parents=True,exist_ok=True)
(base/'code/config').mkdir(exist_ok=True)
for name in ['fm-pr-lib.sh','fm-pr-state.sh','fm-pr-reviewers.sh']:
    shutil.copy2(root/'bin'/name,base/'code/bin'/name)
(base/'code/config/github-hosts').write_text('leadsonline.ghe.com\n')
env={'PATH':os.environ['PATH'],'HOME':str(base/'home'),'GH_CONFIG_DIR':str(base/'gh-config'),'TMPDIR':str(root/'.test-ghe-gate/tmp'),'FM_HOME':str(base/'home'),'FM_CONFIG_OVERRIDE':str(base/'home/config'),'FM_STATE_OVERRIDE':str(base/'home/state')}
with evidence.open('w') as log:
    def run(args, en=env, expected=None):
        p=subprocess.run([str(a) for a in args],env=en,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        log.write('$ '+' '.join(str(a.relative_to(root)) if isinstance(a,pathlib.Path) and a.is_relative_to(root) else str(a) for a in args)+'\n')
        log.write(p.stdout+p.stderr+f'exit={p.returncode}\n\n');log.flush()
        if expected is not None:
            assert p.returncode==expected,(args,p.returncode,p.stderr)
        return p
    urls=['https://leadsonline.ghe.com/Org/repo/pull/7','https://leadsonline.ghe.com.evil/Org/repo/pull/7','https://github.com.evil/Org/repo/pull/7','https://other.ghe.com/Org/repo/pull/7','https://leadsonline.ghe.com/Org/repo/pull/0']
    for url in urls:
        for script in ['fm-pr-check.sh','fm-pr-merge.sh']:
            p=run([root/'bin'/script,'task-a',url],expected=2)
            assert 'invalid PR ' in p.stderr
    assert not list((base/'home/state').iterdir())
    log.write('All rejected requests left the isolated state directory empty.\n\n')
    for script in ['fm-pr-check.sh','fm-pr-merge.sh']:
        p=run([root/'bin'/script,'task-a','https://github.com/Org/repo/pull/7'])
        assert 'invalid PR ' not in p.stderr and p.returncode!=0
    (base/'home/config/github-hosts').write_text('leadsonline.ghe.com\n')
    for url in urls[1:]:
        for script in ['fm-pr-check.sh','fm-pr-merge.sh']:
            p=run([root/'bin'/script,'task-a',url],expected=2)
            assert 'invalid PR ' in p.stderr
    p=run([root/'bin/fm-pr-check.sh','task-a',urls[0]],expected=1)
    assert 'task metadata is unavailable' in p.stderr
    for script in ['fm-pr-state.sh','fm-pr-reviewers.sh']:
        clean=env.copy();clean.pop('FM_HOME');clean.pop('FM_CONFIG_OVERRIDE')
        p=run([base/'code/bin'/script,urls[0]],en=clean,expected=2)
        assert 'expected a GitHub' not in p.stderr and 'could not read' in p.stderr
        assert 'authenticate' in p.stderr or 'GH_TOKEN' in p.stderr or 'gh auth login' in p.stderr
    run(['gh','auth','status','--hostname','leadsonline.ghe.com'],expected=1)
    p=run([root/'bin/fm-pr-poll.sh','--validated','github',urls[0],'leadsonline.ghe.com','Org/repo','7'],expected=0)
    assert p.stdout==''
    log.write('An unauthenticated Enterprise lookup produced no merged notification.\n')
print(evidence)
