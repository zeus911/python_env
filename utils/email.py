# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals, print_function
import requests

import ConfigParser
cf = ConfigParser.ConfigParser()
cf.read('../conf/app.conf')

def send_email_by_sendcloud(to_email, subject="", html="",**kwargs, files=None):
    url = "http://api.sendcloud.net/apiv2/mail/send"
    params = {
        "api_user": cf.get('sendcloud','api_user'),
        "api_key": cf.get('sendcloud','api_key'),
        "from": cf.get('sendcloud','from'),
        "to": to_email.split(";"),
        "subject": subject,
        "html": html,
    }
    #kwargs['cc'] = ''
    #kwargs['bcc'] = ''
    params.update(kwargs)
    return requests.post(url, data=params)


def send_email_by_mailgun(to_email, subject, html, **kwargs,files=None):
    data = {"from": cf.get('mailgun','from'),
            "to": to_email.split(";"),
            "subject": subject,
            "html": html}
    data.update(kwargs)
    if files:
        return requests.post(
            "https://api.mailgun.net/v2/zoneke.com/messages",
            auth=("api", cf.get('mailgun','api_key')),
            data=data,
            files=files
        )
    return requests.post(
        "https://api.mailgun.net/v2/zoneke.com/messages",
        auth=("api", cf.get('mailgun','api_key')),
        data=data
    )