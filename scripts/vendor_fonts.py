"""Vendor the site's existing Google Fonts Latin faces and their OFL licences.

Run only when deliberately updating font assets; normal CSS builds are offline.
"""
from pathlib import Path
import re

import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700'
          '&family=Playfair+Display:wght@400;700&display=swap')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')


def download(url):
    response = requests.get(url, timeout=30, headers={'User-Agent': UA})
    response.raise_for_status()
    return response.content


def main():
    folder = ROOT / 'src/static/fonts'
    folder.mkdir(parents=True, exist_ok=True)
    stylesheet = download(SOURCE).decode()
    faces = re.findall(r'/\* latin \*/\s*(@font-face\s*\{[^}]+\})', stylesheet)
    if not faces:
        raise ValueError('Google Fonts did not return Latin WOFF2 faces')
    css = ['/* Self-hosted Google Fonts Latin faces. See ../fonts/*-OFL.txt. */']
    files, preload = {}, {}
    for face in faces:
        family = re.search(r"font-family:\s*'([^']+)'", face).group(1)
        weight = re.search(r'font-weight:\s*([^;]+)', face).group(1)
        remote = re.search(r'url\((https://fonts.gstatic.com/[^)]+\.woff2)\)', face).group(1)
        if remote not in files:
            name = family.lower().replace(' ', '-') + '-' + weight.replace(' ', '-') + '.woff2'
            (folder / name).write_bytes(download(remote))
            files[remote] = name
        css.append(face.replace(remote, '../fonts/' + files[remote]))
        if (family, weight) in {('Inter', '400'), ('Playfair Display', '700')}:
            preload[family] = files[remote]
    (ROOT / 'src/static/css/fonts.css').write_text('\n'.join(css), encoding='utf-8')
    for family, path in [('inter', 'inter'), ('playfair-display', 'playfairdisplay')]:
        (folder / f'{family}-OFL.txt').write_bytes(download(f'https://raw.githubusercontent.com/google/fonts/main/ofl/{path}/OFL.txt'))
    partial = ['{% load static %}'] + [
        f'<link rel="preload" href="{{% static \'fonts/{name}\' %}}" as="font" type="font/woff2" crossorigin>'
        for name in preload.values()]
    (ROOT / 'src/templates/partials/font_preloads.html').write_text('\n'.join(partial) + '\n', encoding='utf-8')
    print('Vendored', len(files), 'Latin font files with OFL licences and two preloads')


if __name__ == '__main__':
    main()
