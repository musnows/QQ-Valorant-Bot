.PHONY:run
run:
	nohup python3.10 qqbot.py >> ./log/bot.log 2>&1 &

.PHONY:ps
ps:
	ps jax | head -1 && ps jax | grep qqbot.py | grep -v grep