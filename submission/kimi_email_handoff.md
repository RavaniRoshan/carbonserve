# Kimi CLI handoff: send the arXiv endorsement request email

Copy everything below the line into Kimi CLI.

---

TASK: Send exactly ONE endorsement-request email from my Gmail, then stop.

CONTEXT: I am a first-time arXiv submitter (account user `RavaniRoshan`) and need
one endorsement for category cs.DC to post my preprint. arXiv issued endorsement
code **VFT3RE**. The paper is "CarbonServe: Uncertainty-Aware Carbon Routing for
SLO-Constrained LLM Inference Across Geo-Distributed Cloud Regions"
(carbon-aware LLM inference routing; builds on the recipient's EnsembleCI work).
I am: Ravani Roshan, Independent Research, ravaniroshansingh@gmail.com,
ORCID 0009-0007-4930-977X. Code: https://github.com/RavaniRoshan/carbonserve

SAFETY RULES (strict, in order):
1. First verify the Gmail identity: the sending account MUST be
   ravaniroshansingh@gmail.com. If you are logged in as any other address,
   STOP immediately and tell me — do not compose, do not send.
2. Compose the email below with the PDF attached (fetch it from
   https://raw.githubusercontent.com/RavaniRoshan/carbonserve/main/paper/CarbonServe.pdf).
3. Show me the full composed email (To / Subject / body / attachment name) and
   wait for my literal reply "send". Do not send before that.
4. Send exactly once, to exactly the address below. No CC, no BCC, no second email.
5. After sending, report the message ID + timestamp and stop. If the professor
   replies, NEVER answer on my behalf — show me the reply and wait.

EMAIL:
- To: yiding@purdue.edu
- Subject: Request for arXiv endorsement (cs.DC)
- Body:

Dear Prof. Ding,

I'm a graduate student working on carbon-aware LLM serving, and I'm writing to
ask for a one-time arXiv endorsement for cs.DC so I can submit my first paper.

The paper is called CarbonServe. It started from something that kept bothering
me about point-forecast carbon routing — workloads getting shifted into grids
that turned out dirtier than home once the forecast was wrong. Your HotCarbon'24
paper on uncertainty put words to exactly that problem, and I ended up building
the routing policy around it: only offload when the remote grid's pessimistic
band beats home's optimistic one. I also used the EnsembleCI datasets
throughout, so your group's work is all over this paper.

The endorsement code arXiv gave me is VFT3RE. I've attached the draft, and the
code is up at github.com/RavaniRoshan/carbonserve — happy to answer anything
about it. My ORCID is 0009-0007-4930-977X.

Thanks very much for considering it,

Ravani Roshan
Independent Research
