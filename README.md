# `githib-slash` -- A Mattermost slash-command receiver for GitHub issues

This program can be used as a target for [Mattermost slash-commands](https://docs.mattermost.com/developer/slash-commands.html).
It accepts the slash-command data over both POST and GET on the `/organisation/repository` path and returns some information about the requested issues.

## Installing

At the moment, `github-slash` can be installed with a simple

```bash
git clone https://github.com/pieterlexis/mattermost-github-slash
```

## Configuring

`github-slash` uses an ini-style configuration language.
Each section is the name of a repository and 3 settings are supported for each repository:

* `token` (mandatory) -- The token (shared secret) as provided by Mattermost
* `icon_url` -- The url for an icon to use as the avatar for this slash-command (![https://octodex.github.com/images/original.png](https://octodex.github.com/images/original.png)) by default
* `username` -- The username that is displayed for messages from this slash-command (default: GitHub)

For an example configuration, see `github-slash.conf.example` in the repository root.

### Adding a slash command to Mattermost

1. Go to Menu > Integrations > Slash Command > Add Slash Command
2. Fill in the fields as you like
3. For "Request URL", fill in the name of the server running `github-slash` and use the name of the repository as the path (e.g. `https://github-slash.example.com/pieterlexis/mattermost-github-slash`)
4. Hit 'Save'
5. Add the token provided by Mattermost for this slash command to `github-slash.conf`
6. (re)start `github-slash`

Now try to use the newly created slash command e.g. "/github #123 #223".

## Running

After installing and configuring, start `github-slash`.
An example unit file for systemd is provided.

`github-slash` can also be run from the commandline.
It has as `--help` switch that shows all available options.

## License
MIT
