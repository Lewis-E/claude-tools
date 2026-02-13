# Walkthrough

1. Asked the LLM to research if there were any official Google Doc MCPs. I want to grab some RFCs for LLM-powered research, but don't want to risk insecure code with access to my GDrive.
2. There's no official MCPs. Let's use an API call instead.
3. LLM created a basic Python script using Google's official API client (google-api-python-client). It used the Docs API to fetch structured JSON and extract plain text. Auth
   was OAuth 2.0 with a credentials.json file from Google Cloud Console.
4. I know GDrive offers a download as markdown option, so I prompt to switch to that. This dropped the markdownify dependency.
5. I told Claude to make this into a skill. It created a skill at `~/.claude/skills/download-gdoc/SKILL.md` and moved the script into the relevant directory.
6. I tried the skill out and it summarized a doc for me, but really, I want to be able to do multiple searches on large files. So I prompted some design thoughts (instead of giving a specific implementation path!) This got me a little implementation plan that I liked.

`Let's think about this from a design perspective. Odds are, we will look at the same docs multiple times, probably from multiple different projects/claude sessions. Many docs will be large, so it'll be good to be able to search them multiple times in a session. We would want to save the doc, in a way where if we try to download it again, we can overwrite the old doc/reuse it if it hasn't changed, in a location that's not specific to any one Claude session but is easily findable by Claude. How should we do this memory feature?`

7. We did some testing, then I asked about distributing this skill. The Oauth credential path isn't great for that, but I know there's other gcloud auth tools available that might work for this. 

`Is there a way to do this auth through gcloud cli or otherwise?`

8. After a couple of failed iterations, the LLM came up with an auth command that worked and we integrated it into the script. 

Overall, you can see dev knowledge (gdrive, gcloud cli capabilities) were key to this process, but the actual code writing and iterative testing was easy to hand off. 