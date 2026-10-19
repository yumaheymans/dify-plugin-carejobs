# Privacy Policy

**Plugin:** CareJobs.Now Healthcare Jobs (`yumaheymans/carejobs`)
**Contact:** hello@carejobs.now

## Summary

This plugin does not collect, store or log any user data. It has no credentials, no accounts,
no analytics and no telemetry. It only sends the arguments of each tool call to the public
CareJobs.Now API and returns the answer to your Dify app.

## What is sent, and where

When a tool runs, the plugin makes one HTTPS request to a single fixed address:

`https://carejobs.now/api/mcp` (the CareJobs.Now remote MCP server, a third-party service)

The request contains only the tool name and the arguments you or your app's model chose, for
example a keyword such as "ICU", a kind of job such as `nurses`, a US state, an employer name or
slug, a minimum hourly pay, a sort order and a result count. The plugin also sends a fixed
User-Agent header that names the plugin. The request goes out from the machine that runs your
Dify plugin daemon, so the CareJobs.Now service sees that machine's IP address, as any web
service would.

The plugin does not send API keys, Dify user or workspace identifiers, conversation history,
uploaded files, or any other data. Because search arguments are chosen by your app, please do
not put personal or sensitive information (names, health information, contact details) into the
search fields of a tool.

## What is stored or logged by the plugin

Nothing. The plugin keeps no database, files, cache, cookies or local storage, and it writes no
logs of the arguments or the answers. Answers are returned to Dify and handled under your own
Dify deployment's data settings.

## Third-party service

The CareJobs.Now service is operated by O-mega Enterprise, Inc. Requests to it are handled under
its own policies:

- Privacy Policy: https://carejobs.now/legal/privacy
- Terms: https://carejobs.now/legal/terms

The answers contain public job information (job titles, employers, places, posted pay and links
to CareJobs.Now pages). They contain no personal data about job seekers.

## Retention and deletion

The plugin retains no data, so there is nothing to delete on its side. For questions about
requests handled by the CareJobs.Now service, write to hello@carejobs.now.

## Changes

If the plugin starts sending different data or contacting another service, this file and the
plugin version will be updated in the same release.
