#!/usr/bin/env python3
from bottle import Bottle, run, request, HTTPError
from bottle_log import LoggingPlugin
import os
import sys
import requests
import logging
import argparse

app = Bottle()


@app.route('/<org>/<repo>')
def slash(logger, org, repo):
    logger.debug("Got a request for {org}/{repo} with the following data: {data}".format(
        org=org, repo=repo, data={k: request.params.get(k) for k in request.params.keys()}
    ))
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
            url = 'https://api.github.com/repos/{org}/{repo}/issues/{num}'.format(
                org=org,
                repo=repo,
                num=issue)
            logger.debug('Getting the following url: {url}'.format(url=url))
            res = requests.get(url)
            res.raise_for_status()
            logger.debug('Got response: {data}'.format(data=res.json()))
        except requests.exceptions.HTTPError as e:
            errors.append('Unknown Issue number: {issue}'.format(issue=issue))
            logging.error('Got error from upstream: {e}'.format(e=e))
            continue
        res = res.json()

        if res.get('pull_request'):
            issuetype = "Pull Request"
            try:
                url = res.get('pull_request').get('url')
                logger.debug("Issue is a Pull Request, getting {url}".format(url=url))
                res = requests.get(url)
                res.raise_for_status()
                logger.debug('Got response: {data}'.format(data=res.json()))
            except requests.exceptions.HTTPError as e:
                errors.append('Unable to get PR information for {issue}'.format(issue=issue))
                logging.error('Got error from upstream: {e}'.format(e=e))
                continue
            res = res.json()

        issuestate = res['state']
        if issuetype == 'Pull Request' and issuestate == 'open':
            try:
                url = res.get('_links').get('statuses').get('href')
                logger.debug("Pull Request is open, getting extra data from {url}".format(url=url))
                ci_status = requests.get(url)
                ci_status = ci_status.json()[0]
                logger.debug('Got response: {data}'.format(data=ci_status.json()))
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
        logger.info("Had errors, sending response: {data}".format(data=resp))
        return resp

    resp.update({'text': '\n'.join(text)})
    logger.info("Done! Sending response: {data}".format(data=resp))
    return resp


argparser = argparse.ArgumentParser(prog='github-slash.py', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

argparser.add_argument('--config', '-c', action='store', metavar='CONFIGFILE', default='./github-slash.conf',
                       help='Configuration file to use.')
argparser.add_argument('--port', '-p', action='store', type=int, metavar='PORT', default=8080,
                       help='Port of listen on.')
argparser.add_argument('--address', '-a', action='store', metavar='ADDRESS', default='localhost',
                       help='IP address or hostname to listen on.')
argparser.add_argument('--verbose', '-v', action='count', help='Give more output', default=0)

args = argparser.parse_args()

if args.verbose == 1:
    app.config['logging.level'] = 'info'
if args.verbose > 1:
    app.config['logging.level'] = 'debug'

if not os.path.isfile(args.config):
    logging.error('File does not exist: {fname}'.format(fname=args.config))
    sys.exit(1)

app.install(LoggingPlugin(app.config))
app.config.load_config(args.config)

run(app, host=args.address, port=args.port)
