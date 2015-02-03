from pathlib import Path
import click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """PyCon APAC 2015 web content uploader"""
    pass

@cli.command(short_help='Upload html to web')
@click.argument(
    'html',
    type=click.Path(file_okay=True, dir_okay=False, readable=True)
)
def upload(html):
    """Upload a html to web content respecting lang

    For /path/to/<lang>/page.html, overwrites web content
    at https://tw.pycon.org/2015apac/<lang>/page

    Note that /<lang>/page must exist.
    """
    click.echo('Uploading {:s} ...'.format(html))
    html_pth = Path(html)
    *_, lang_suffix, __ = html_pth.parts
    page_name = html_pth.stem
    click.echo(
        'Lang: {:s} | Page: {:s}'
        .format(lang_suffix, page_name)
    )


if __name__ == '__main__':
    cli()
