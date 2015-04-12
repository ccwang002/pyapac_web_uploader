"""\
Web uploader for PyCon APAC 2015.

See `pyapac-web -h` or README.md for its usage.
"""
__version__ = '0.4'

import functools
import logging
import operator
from pathlib import Path
import re
import sys
import textwrap

from bs4 import BeautifulSoup
import click
import requests
import six
import pandas as pd
if six.PY3:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse
    FileExistsError = IOError

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
LANG_CHOICES = ['en', 'zh', 'ja', 'kr']

_LOGIN_ERR_MSG = '''\
Something wrong with reading login info.
Edit file {:s} with following format:

    Account: 'YOUR ACCOUNT'
    Password: 'PASSWORD'
'''

# create logger instance
logger = logging.getLogger('pyapac-web')
logger.addHandler(logging.NullHandler())

# create a click arugment type that only allows input of existed file
_existed_file_type = functools.partial(
    click.Path,
    exists=True,
    file_okay=True,
    dir_okay=False,
    readable=True
)


class ConnectionError(Exception):
    def __init__(self, msg, resp):
        super().__init__(msg, resp)
        self.msg = msg
        self.resp = resp

    def format_message(self):
        return (
            'ConnectionError: {0.msg} with {0.resp.status_code}'
            .format(self)
        )

class SiteConnector:
    def __init__(self, url_base, lang):
        self._session = requests.session()
        self.url_base = url_base
        self.lang = lang
        self.login_url = self.url('accounts/login')
        self.logout_url = self.url('accounts/logout')
        self.edit_url = self.url('edit/')

    def login(self, keychain_pth='.web_keychain'):
        try:
            ACCOUNT, PASSWORD = self._read_keychain(keychain_pth)
        except Exception:
            six.print_(_LOGIN_ERR_MSG.format(keychain_pth))
            sys.exit(1)
        # standard Django login with CSRF protection
        r = self._session.get(self.login_url)
        login_payload = {
            'username': ACCOUNT,
            'password': PASSWORD,
            'csrfmiddlewaretoken': r.cookies['csrftoken']
        }
        r = self._session.post(
            self.login_url,
            data=login_payload,
            headers={'Referer': self.login_url}
        )
        if r.status_code != 200:
            raise ConnectionError('Login fail', r)
        return r

    def logout(self):
        return self._session.get(self.logout_url)

    def upload(self, page_name, src_pth):
        """Upload src_pth to self.url_base/self.lang/page_name"""
        with Path(src_pth).open() as f:
            html = f.read().replace('\n', '')

        # get page_url's session and page id
        page_url = self.url(page_name)
        r = self._session.get(page_url)
        soup = BeautifulSoup(r.content)
        content_form = soup.select('form.editable-form')[0]
        upload_payload = self._gen_form_payload(content_form)
        upload_payload['content'] = html

        # mimic the frontend editing POST
        r = self._session.post(
            self.edit_url,
            data=upload_payload,
            headers={'Referer': page_url}
        )
        if r.status_code != 200:
            raise ConnectionError('Update {} fail'.format(page_url), r)
        return r

    def download(self, page_name, dst_pth):
        """Download self.url_base/self.lang/page_name to dst_pth"""
        page_url = self.url(page_name)
        r = self._session.get(page_url)
        if r.status_code != 200:
            raise ConnectionError('Download {} fail'.format(page_url), r)

        # extract the form value for raw input
        soup = BeautifulSoup(r.content)
        page_raw_html = soup.select(
            'form.editable-form textarea.mceEditor.charfield'
        )[0].text

        # re-parse the raw input as a valid html structure
        page_content_soup = BeautifulSoup(page_raw_html, 'html.parser')
        page_normalized_html = page_content_soup.prettify()
        with Path(dst_pth).open('w') as f:
            six.print_(page_normalized_html, file=f)
        return r

    def url(self, url):
        """Return full URL self.url_base / self.lang / <url>"""
        return '/'.join([self.url_base, self.lang, url])

    def _gen_form_payload(self, form_soup):
        """Generate editing payload from given editing page"""
        payload = {
            k: form_soup.find('input', attrs={'name': k}).attrs['value']
            for k in ['app', 'model', 'id', 'fields', 'csrfmiddlewaretoken']
        }
        is_valid_form = (
            payload['app'] == 'pages' and payload['model'] == 'richtextpage'
        )
        if not is_valid_form:
            raise ValueError(
                'Editing a invalid page of id={id}, app={app}, model={model}'
                .format(**payload)
            )
        return payload

    def _read_keychain(self, keychain_pth):
        _field_regex = (
            r'^{name:s}\s*:\s*'               # Account :
            r'''(['"]?)(?P<field>\S+)\1'''    # myacc, or 'myacc', "myacc"
                                              # if containing spaces
        ).format
        _acc_regex = _field_regex(name='Account')
        _pwd_regex = _field_regex(name='Password')

        with open(keychain_pth) as f:
            ACCOUNT = re.match(_acc_regex, next(f)).group('field')
            PASSWORD = re.match(_pwd_regex, next(f)).group('field')

        return ACCOUNT, PASSWORD


def make_review_table(table):
    def review_status(text):
        if text == 'Update':
            return True
        elif text == 'Review':
            return False
        else:
            return pd.np.nan

    def convert_col(col, dtype):
        tmp = col.copy()
        tmp[tmp == '－－－'] = pd.np.nan
        return tmp.astype(dtype)

    df = pd.io.html.read_html(str(table))[0]
    required_cols = [
        'ID', 'Author', 'Lang', 'Title', 'Speech Type',
        'Reviews', 'Sum. Rank', 'Avg. Rank'
    ]
    df_out = df.loc[:, required_cols]
    df_out['Review Status'] = df['Action'].apply(review_status)
    for col, col_type in zip(
        ['Reviews', 'Sum. Rank', 'Avg. Rank'],
        [int] * 2 + [float] * 1
    ):
        df_out[col] = convert_col(df_out.loc[:, col], float)

    return df_out


def get_review_url(talk_id):
    return (
        r'https://tw.pycon.org/2015apac/en/'
        r'proposal_review/review/{}/'.format(talk_id)
    )


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """PyCon APAC 2015 web content uploader.

    Check each command's usage by

    \b
        pyapac-web <subcmd> -h

    Most commands require .web_keychain for login.
    The format is:

    \b
        Account: 'YOUR ACCOUNT'
        Password: 'PASSWORD'
    """
    pass


def parse_page_param(ctx, param, value):
    if value is None:
        return
    url_tokens = urlparse(value).path.strip('/').split('/')
    if url_tokens[0] == '2015apac':
        url_tokens = url_tokens[1:]
    if url_tokens[0] in LANG_CHOICES:
        lang = url_tokens[0]
        page_name = '/'.join(url_tokens[1:])
    else:
        lang = None
        page_name = '/'.join(url_tokens)

    prev_lang = ctx.params.get('lang')
    if not lang and not prev_lang:
        raise click.BadParameter('lang code not set.')
    if lang and lang not in LANG_CHOICES:
        raise click.BadParameter('page url contains invalid lang code.')
    if lang and prev_lang and lang != prev_lang:
        raise click.BadParameter('lang code mismatch')

    final_lang = lang or prev_lang
    ctx.params['lang'] = final_lang

    return page_name


@cli.command(short_help='Upload html to web')
@click.argument('html', type=_existed_file_type(), metavar='<html_pth>')
@click.option(
    '--keychain', 'keychain_pth',
    help='Path to .web_keychain for login',
    default='.web_keychain',
    show_default=True,
    type=_existed_file_type(),
)
@click.option(
    '--target', 'page',
    help='Full or partial url to the page',
    metavar='<page_url>',
    callback=parse_page_param
)
def upload(html, keychain_pth, lang=None, page=None):
    """Upload html files to web content respecting lang

    To upload path/to/<lang>/<page>.html to /<lang>/<page>,

    \b
        pyapac-web upload path/to/<lang>/<page>.html
        pyapac-web upload src.html --target <lang>/<page>

    Note that on web /<lang>/<page> must exist.
    """
    click.echo('Uploading {:s} ...'.format(html))
    html_pth = Path(html).resolve()
    if lang and page:
        lang_suffix = lang
        page_name = page
    else:
        try:
            lang_ix = next(
                i for i, token in enumerate(html_pth.parts)
                if token in LANG_CHOICES
            )
        except StopIteration:
            raise click.BadParameter(
                'Unknown lang suffix of path {!s}'.format(html_pth),
                param_hint='<html_pth>',
            )
        lang_suffix = html_pth.parts[lang_ix]
        page_name = '/'.join(
            html_pth.parts[lang_ix + 1:-1] + (html_pth.stem, )
        )
    click.echo(
        'Lang: {:s} | Page: {:s}'
        .format(lang_suffix, page_name)
    )

    # main logics
    site = SiteConnector(
        url_base='https://tw.pycon.org/2015apac',
        lang=lang_suffix
    )
    site.login(keychain_pth)
    site.upload(page_name, html_pth)
    site.logout()


@cli.command(short_help='Download web page as html')
@click.argument('page', metavar='<page_url>', callback=parse_page_param)
@click.argument('dst', metavar='<html_pth>', default='.', required=False)
@click.option(
    '--lang',
    type=click.Choice(LANG_CHOICES),
    help='Lang code for page',
    is_eager=True
)
@click.option(
    '--force',
    help='Overwrite existed file',
    is_flag=True,
    default=False
)
@click.option(
    '--keychain', 'keychain_pth',
    help='Path to .web_keychain for login',
    default='.web_keychain',
    show_default=True,
    type=_existed_file_type(),
)
def download(lang, page, dst, force, keychain_pth):
    """Download web page from <page_url> as html.

    To grab a page,

    \b
        pyapac-web download https://tw.pycon.org/apac2015/en/venue
        pyapac-web download en/venue
        pyapac-web download --lang=en venue

    If <html_pth> is an existed folder, it stores the html page at
    <html_pth>/<lang>_<page>.html.

    Otherwise, it will write the html to <html_pth> and
    abort if that path exists unless --force is given.

    By default it indents at 1 space. In vim use gg=G to re-indent.
    You should really check the downloaded html before overwriting.
    """
    dst_pth = Path(dst)
    if dst_pth.is_dir():
        # create new file
        out_pth = dst_pth / '{}_{}.html'.format(lang, page.replace('/', '-'))
    else:
        # if not dir, write to this path
        out_pth = dst_pth
    if out_pth.exists() and not force:
        raise FileExistsError(
            '<html_pth> {!s} exists. Set --force to overwrite'
            .format(out_pth)
        )
    click.echo(
        'lang: {} | page: {} | out to {}'
        .format(lang, page, str(out_pth))
    )

    # main logic
    site = SiteConnector(
        url_base='https://tw.pycon.org/2015apac',
        lang=lang
    )
    site.login(keychain_pth)
    site.download(page, out_pth)
    site.logout()

@cli.command(short_help='Get proposal statistics')
@click.option(
    '--review',
    help='Get proposal review status',
    is_flag=True,
    default=False
)
@click.option(
    '--csv', 'out_csv', metavar='PATH',
    help='Store result as csv',
)
@click.option(
    '--keychain', 'keychain_pth',
    help='Path to .web_keychain for login',
    default='.web_keychain',
    show_default=True,
    type=_existed_file_type(),
)
def stat(keychain_pth, review, out_csv):
    """Get proposal statistics, grouped by talk type and language.

    \b
        pyapac-web stat --keychain='../.web_keychain'

    If --review is passed, get review statistics.
    """
    # main logic
    site = SiteConnector(
        url_base='https://tw.pycon.org/2015apac',
        lang='en'
    )
    site.login(keychain_pth)
    if review:
        proposal_review_url = (
            r'https://tw.pycon.org/2015apac/en/'
            r'proposal_review/proposals'
        )
        r = site._session.get(proposal_review_url)
        soup = BeautifulSoup(r.content)
        table = soup.find('table')
        df_talks = make_review_table(table)
        pd.set_option('display.max_rows', len(df_talks) * 2)
        pd.set_option('display.max_colwidth', 256)
        if out_csv:
            df_talks.to_csv(out_csv)
        else:
            click.echo(df_talks)
    else:
        proposal_url = (
            r'https://tw.pycon.org/2015apac/admin/proposal/proposalmodel/'
        )
        r = site._session.get(proposal_url)
        soup = BeautifulSoup(r.content)
        table = soup.find('table')
        df_talks = pd.io.html.read_html(str(table))[0]
        grouper = df_talks.groupby(['Type of the proposal', 'Language']).size()
        click.echo(grouper)
        click.echo('-' * 32)
        click.echo('Total: {:d} proposals'.format(len(df_talks)))
    site.logout()


@cli.command(short_help='Get proposal review status')
@click.argument('id', metavar='<review_id>')
@click.option(
    '--keychain', 'keychain_pth',
    help='Path to .web_keychain for login',
    default='.web_keychain',
    show_default=True,
    type=_existed_file_type(),
)
def review(keychain_pth, id):
    """Get the proposal info by its proposal id
    """
    # main logic
    site = SiteConnector(
        url_base='https://tw.pycon.org/2015apac',
        lang='en'
    )
    site.login(keychain_pth)
    r = site._session.get(get_review_url(id))
    soup = BeautifulSoup(r.content)
    title, _, author = soup.select('h3.d-title')[0].text.strip().split('\n')
    for header, content in zip(
        ['Title', 'Author'],
        [title, author]
    ):
        click.echo(header.strip())
        click.echo('=' * len(header))
        click.echo(content.strip())
        click.echo()

    # for rewrapping proposal info under 70 chars
    _, *proposal_content = map(
        operator.attrgetter('text'),
        soup.select('dl.dl-info dd > pre')
    )
    wrapper = textwrap.TextWrapper(width=70, replace_whitespace=False)
    for header, content in zip(
        ['Tags', 'Abstract', 'Description', 'Reference'],
        proposal_content
    ):
        click.echo('\n' * 1)
        click.echo(header)
        click.echo('-' * len(header))
        click.echo(wrapper.fill(content))


if __name__ == '__main__':
    cli()
