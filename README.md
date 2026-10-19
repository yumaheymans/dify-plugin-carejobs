# CareJobs.Now Healthcare Jobs

**Author:** yumaheymans
**Version:** 0.0.1
**Type:** Tool

Give your Dify agents, chatflows and workflows live data on the US healthcare job market.
[CareJobs.Now](https://carejobs.now) is a free healthcare job board. It reads the open jobs of
more than 2,000 US hospitals, health systems, clinic groups and care companies (nurses, CNAs,
doctors, NPs and PAs, therapists, imaging and lab techs, pharmacy, caregivers, front office and
more). This plugin lets an app search those jobs, compare posted pay, look up an employer and
read job-market numbers by kind of job and by state. Each job result links to its page on
CareJobs.Now, where the person applies.

The CareJobs.Now API is public and free. **No API key, account or credential is needed.**

## Tools

| Tool | What it does |
|------|--------------|
| Search Healthcare Jobs | Search open jobs by keyword, kind of job, state, employer, remote only, minimum hourly pay, and sort order. Returns title, employer, posted pay, shift, place and a link. |
| Get Healthcare Pay | Median and typical hourly pay that open jobs post, for every kind of job, for one kind, for one employer, or for an employer and a kind. |
| Get Healthcare Job Market | How many healthcare jobs are open, how many are new this week, and the open jobs by kind, state and employer. |
| Get Healthcare Jobs by State | Every state's open jobs and employers, or one state's jobs by kind, pay, towns, employers and newest jobs (for example CNA jobs in Ohio). |
| List Healthcare Employers | Find employers (and AI-training programs and job boards) by name, kind of care, state or kind of job, and get the slugs the other tools use. |
| Get Healthcare Employer | One employer: what it is, where it hires, its open jobs by kind, its posted pay and its newest and best-paid jobs. |

Every tool returns a readable text summary and the same answer as structured JSON, so it works
for agents (the model reads the text) and for workflows (later nodes use the JSON).

Kinds of job: `nurses`, `nurse-practitioners`, `physicians`, `nursing-assistants`, `caregivers`,
`therapy-rehab`, `mental-health`, `pharmacy`, `imaging`, `lab`, `surgical-techs`,
`emts-paramedics`, `medical-assistants`, `dental`, `admin`, `allied-health`, `ai-training`.

## Setup

1. Install the plugin from the Dify Marketplace (Plugins, then Marketplace, then search for
   "CareJobs.Now").
2. There is nothing to configure. The tools are ready to use as soon as the plugin is installed.

## Usage

**Agent or chatflow.** Add the CareJobs.Now tools to an Agent node or an Agent app, then ask in
plain language:

- "Find night-shift ICU nursing jobs in Texas that pay at least $45 an hour."
- "What do CNAs make in Ohio, and which employers post the most?"
- "Which hospital systems hire remote case managers?"
- "How many healthcare jobs were listed this week?"

**Workflow.** Add a Tool node, pick one of the CareJobs.Now tools and fill in the parameters.
For example, Search Healthcare Jobs with `kind` set to `nurses`, `state` set to `TX` and `limit`
set to 5 returns five Texas nursing jobs. Use the text output in an LLM node, or read the JSON
output in later nodes.

Employers are identified by a slug such as `kaiser-permanente` or `cvs-health`. Use List
Healthcare Employers to find a slug, or pass the employer name.

## Connection requirements

The plugin makes outbound HTTPS requests to one fixed address, `https://carejobs.now/api/mcp`
(the CareJobs.Now remote MCP server). If your Dify deployment restricts outbound traffic, allow
the host `carejobs.now` on port 443. The address cannot be changed from inside Dify, and the
plugin follows no redirects. Requests time out after 5 seconds to connect and 30 seconds to read.

## Notes on the data

- Pay is what employers post, measured from the hourly rates open jobs state. It is before shift
  differentials and bonuses. A rate shown as "typical of" an employer's jobs is a measured
  figure, not a rate that posting states.
- Results cover US jobs only.
- Always send people to the link in each result to apply. The plugin never applies to a job.

## Privacy

The plugin sends only the arguments of the tool call, to CareJobs.Now, and stores nothing. See
[PRIVACY.md](PRIVACY.md) and the CareJobs.Now [privacy policy](https://carejobs.now/legal/privacy)
and [terms](https://carejobs.now/legal/terms).

## Source and contact

- Source repository: https://github.com/yumaheymans/dify-plugin-carejobs
- Contact: hello@carejobs.now
- Service: https://carejobs.now
- License: MIT
