1/ I run 39 AI agents and services on one Mac Mini. For months I assumed they were fine.

They weren't. A user told me.

2/ When I finally looked, here's what I found:

28 alive. 11 down. 28% failure rate I was completely blind to.

$112.45 in token spend I couldn't trace. One agent burned 91.5% of it.

3/ The number that got me wasn't the total. It was the 0.3% output/input ratio.

For every 100K tokens I fed my agents, I got back 300 tokens of useful output. The rest was context that never produced anything.

4/ I dug in. Found my Hermes skills were loading in their entirety on every turn. Every skill file, every reference doc, every template — all of it, every time.

Used the Brain Analysis tab to find the bloat. Ran Compression to trim it.

5/ I open-sourced the tool I built to find all this.

pip install observeco && observeco dashboard

60 seconds. No cloud. No Docker. MIT.

6/ I wrote the full story — what I found, what I fixed, and what's coming in v1.1 (auto-heal).

[link to X Article]

https://github.com/observeco/observeco