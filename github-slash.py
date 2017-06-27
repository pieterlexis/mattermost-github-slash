#!/usr/bin/env python3
from bottle import Bottle, run, request, HTTPError
from bottle_log import LoggingPlugin
import requests
import logging

logger = logging.getLogger()

app = Bottle()
app.install(LoggingPlugin(app.config))

app.config.load_config('./github-slash.conf')


@app.route('/<org>/<repo>')
def slash(org, repo):
    token = app.config.get('{org}/{repo}.token'.format(org=org, repo=repo))
    if not token:
        logger.error("No configuration found for {org}/{repo}".format(
            org=org, repo=repo
        ))
        raise HTTPError(400)

    if request.params.token != token:
        logger.error("Token in request incorrect for {org}/{repo}".format(
            org=org, repo=repo
        ))
        raise HTTPError(400)

    issues = [issue.lstrip('#') for issue in request.params.text.split(' ')]

    if not issues:
        raise HTTPError(400)

    resp = {"response_type": "in_channel",
            "username": app.config.get('{org}/{repo}.username'.format(org=org, repo=repo), "GitHub"),
            "icon_url": app.config.get('{org}/{repo}.icon_url'.format(org=org, repo=repo),
                                       "https://octodex.github.com/images/original.png")}

    text = []
    errors = []
    for issue in issues:
        try:
            int(issue)
        except ValueError:
            errors.append('{issue} is not a valid issue number'.format(issue=issue))
            continue

        issuetype = "Issue"
        try:
            res = requests.get('https://api.github.com/repos/{org}/{repo}/issues/{num}'.format(
                org=org,
                repo=repo,
                num=issue))
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            errors.append('Unknown Issue number: {issue}'.format(issue=issue))
            logging.error('Got error from upstream: {e}'.format(e=e))
            continue
        res = res.json()

        if res.get('pull_request'):
            issuetype = "Pull Request"
            try:
                res = requests.get(res.get('pull_request').get('url'))
            except requests.exceptions.HTTPError as e:
                errors.append('Unable to get PR information for {issue}'.format(issue=issue))
                logging.error('Got error from upstream: {e}'.format(e=e))
                continue
            res = res.json()

        issuestate = res['state']
        if issuetype == 'Pull Request' and issuestate == 'open':
            try:
                ci_status = requests.get(res.get('_links').get('statuses').get('href'))
                ci_status = ci_status.json()[0]
                issuestate += ', {mergable}mergable, Travis: {ci}'.format(
                    mergable='' if res.get('mergeable') else 'not ',
                    ci=ci_status.get('state')
                )
            except requests.exceptions.HTTPError as e:
                issuestate += 'unable to fetch CI status'
                logger.warning('Could not get CI information: {e}'.format(e=e))

        text.append(" * [{issuetype} #{issue}]({issueurl}) [{issueauthor}]({issueauthorurl}) "
                    "({issuestate}): {issuetitle}".format(
                        issuetype=issuetype,
                        issue=issue,
                        issueurl=res.get('html_url'),
                        issueauthor=res.get('user').get('login'),
                        issueauthorurl=res.get('user').get('html_url'),
                        issuestate=issuestate,
                        issuetitle=res.get('title')))

    if errors:
        resp.update({'text': '\n'.join(errors), 'response_type': 'ephemeral'})
        return resp

    resp.update({'text': '\n'.join(text)})
    return resp


host = 'localhost'
address = '127.0.0.1'
port = 8081

if app.config.get('server'):
    host = app.config.get('server.host', 'localhost')
    address = app.config.get('server.address', '127.0.0.1')
    port = app.config.get('server.port', 8081)

run(app, host=host, port=port, address=address)
