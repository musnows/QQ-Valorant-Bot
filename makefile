.PHONY:run
run:
	nohup python3.10 qqahri.py >> ./log/nohup.log 2>&1 &

.PHONY:ps
ps:
	ps jax | head -1 && ps jax | grep qqahri.py | grep -v grep