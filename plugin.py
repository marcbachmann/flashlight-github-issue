import copy, re, json

#
# Helper methods
#
def read_config():
    with open('config.json', 'r') as f:
        return json.load(f)


def write_config(data):
    with open('config.json', 'w') as f:
        json.dump(data, f)


def replace_tokens(html, content):
    if content.get('organisation'): html = html.replace("{{organisation}}", content.get('organisation'))
    html = html.replace("{{repository}}", content.get('repository') or '?')
    html = html.replace("{{title}}", content.get('title') or '')
    if isinstance(content.get('labels'), basestring): html = html.replace("{{labels}}", content.get('labels'))
    return html.replace("{{content}}", content.get('content') or '')


def build_html(template, content, config):
    html = open(template+'.html').read().decode('utf-8')
    html = html.replace("{{url}}", build_url(content))

    content = copy.copy(content)
    content['labels'] = build_label_html(content.get('labels'), config)
    html = replace_tokens(html, content)
    html = html.replace('{{user_id}}', config.get('user_id') or '')
    html = html.replace('{{user_name}}', config.get('user_name') or '')
    html = html.replace('{{organisation}}', config.get('user_name') or '')
    return html


def build_label_html(labels, config):
    html = ''
    if labels:
        if not config.has_key('colors'): config['colors'] = {}
        for label in labels:
            if config['colors'].has_key(label):
                color = config['colors'][label]
            elif config['colors'].has_key('default'):
                color = config['colors']['default']
            else:
                color = ["rgb(51,51,51)", "white", "rgb(210,210,210)"]
            style = 'color: %s; background: %s; border-color: %s;' % tuple(color)
            html += """<li class="label" style="%s"><span class="label-name">%s</span></li>""" % (style, label)
    return html


def build_url(content):
    url = replace_tokens('http://github.com/{{organisation}}/{{repository}}/issues/new?title={{title}}&body={{content}}', content)
    if content.has_key('labels'):
        for label in content.get('labels'):
            url += '&labels[]='+label
    return url


def parse_query(query, config):
    organisation = config.get('organisation') or ''
    repository = None
    title = None
    content = None
    labels = []

    match = re.match('([a-zA-Z0-9\-\._\/]*)\ ?(.*)?', query)
    if match:
        organisation_and_repository = (config['aliases'].get(match.group(1)) or match.group(1)).split('/', 1)
        if len(organisation_and_repository)>1:
            organisation, repository = organisation_and_repository
        elif len(organisation_and_repository)==1:
            repository = organisation_and_repository[0]

        title_and_content = match.group(2)
        contains_label = re.match('.*\ ?labels?=([a-zA-Z,;\.]*).*', title_and_content)
        if contains_label:
            labels = filter(None, re.split(',|;', contains_label.group(1)))
            title_and_content = re.compile("(.*)\ ?labels?=[a-zA-Z,;\.]*\ ?(.*)").split(title_and_content)
            title_and_content = ' '.join(title_and_content)

        title_and_content = title_and_content.split(',', 1)
        if len(title_and_content)==2:
            title, content = title_and_content
            content = content.replace('  ', '\n').strip()
        elif len(title_and_content)==1:
            title = title_and_content[0]

    return {
        "organisation": organisation,
        "repository": repository,
        "title": title,
        "content": content,
        "labels": labels
    }


#
# Query
#
# ghi alias livingdocs-engine=upfrontIO/livingdocs-engine
# ghi config user=marcbachmann
# ghi config organisation=upfrontIO
# ghi upfrontIO/livingdocs-engine test
ALPHA_NUMERIC_REGEX = '[a-zA-Z0-9\-\._\/]*'
def results(params, original_query):
    query = params['~query'] if params.has_key('~query') else ''
    match = re.match('([a-zA-Z0-9\-\._\/]*)\ ?(.*)?', query)
    action = match.group(1)
    config = read_config()
    if action == 'config':
        return process_config(match.group(2), config)
    elif action == 'alias':
        return process_alias(match.group(2), config)
    else:
        return process_create(query, config)


def process_alias(query, config):
    match = re.match('([a-zA-Z0-9\-\._\/]*)=([a-zA-Z0-9\-\._\/]*)', query)
    res = { "title": "Write alias" }

    if match:
        dst = match.group(1)
        src = match.group(2)
        action = "write" if src else "delete"

        content = {
            "action": action,
            "dst": dst,
            "src": src
        }

        res["title"] = "%s the alias %s" % (action, dst)
        res["html"] = build_html('config', content, config)
        res["run_args"] = ['alias', content, config]

    return res


def process_config(query, config):
    return {
        "title": "Show config",
        "run_args": ['config', query, config],
        "html": build_html('config', config, config)
    }


def process_create(query, config):
    title = 'Create a new issue'
    content = parse_query(query, config)
    return {
        'title': title,
        'run_args': ['create', content, config],
        'html': build_html('create', content, config),
        'webview_links_open_in_browser': True
    }


#
# Execute
#
def run(action, content, config):
    if action == 'create':
        return run_create(content, config)
    elif action == 'alias':
        return run_alias(content, config)
    elif action == 'config':
        return run_config(content, config)


def run_create(content, config):
    import subprocess
    url = build_url(content)
    subprocess.call(["""open '%s' """ %(url)], shell=True)
    # subprocess.call(['echo "'+output+'" | LANG=en_US.UTF-8  pbcopy && osascript -e \'display notification "Copied!" with title "Flashlight"\''], shell=True)


def run_alias(content, config):
    action = content.get('action')
    key = content.get('dst')
    if action == 'write':
        if not config.has_key('aliases'): config['aliases'] = {}
        config['aliases'][key] = content.get('src')
        write_config(config)

    else:
        del config['aliases'][key]
        write_config(config)

    import subprocess
    subprocess.call(['osascript -e \'display notification "Alias %s" with title "Flashlight"\'' % (action)], shell=True)


def run_config(content, config):
    import subprocess
    subprocess.call(['osascript -e \'display notification "Config" with title "Flashlight"\''], shell=True)


# test
# print results({'~query': 'engine labels=foo'}, 'ghi upfrontIO/livingdocs-editor')
# run(*results({'~query': 'alias engine=upfrontIO/livingdocs-engine'}, '')['run_args'])
