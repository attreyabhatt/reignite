"""Build captioned still-frame walkthroughs from screenshots of the local web UI.

Capture input/result screenshots using the isolated preview, then run this script.
All output is explicitly labelled fictional and illustrative. No customer data is used.
"""
import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from seoapp.product_demos import DEMOS


STEPS = {
    'choose-a-reply': [
        'Add the latest exchange and choose the situation.',
        'Compare three illustrative suggestions. Choose one that fits the message.',
        'Copy, edit in your own voice, and use only details that are true for you.',
    ],
    'confirm-a-date': [
        'Add the agreed day, time and place from your conversation.',
        'Check that the suggested confirmation uses the actual arrangements.',
        'Keep it short. One practical confirmation is enough.',
    ],
    'reply-to-a-story': [
        'Add a real detail from their story. This example uses a bookshop.',
        'Compare the illustrative openers and choose one relevant question.',
        'Adapt the wording. Leave an unanswered first message alone.',
    ],
}


def font(size):
    for candidate in [Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def frame(source, title, step, target):
    image = Image.new('RGB', (1280, 850), '#10141e')
    draw = ImageDraw.Draw(image)
    draw.text((28, 14), title, font=font(25), fill='#ffffff')
    draw.text((28, 51), 'FICTIONAL MESSAGES | ILLUSTRATIVE OUTPUT | LOCAL WEB WALKTHROUGH', font=font(17), fill='#ffc069')
    screenshot = Image.open(source).convert('RGB')
    screenshot.thumbnail((1240, 660), Image.Resampling.LANCZOS)
    image.paste(screenshot, ((1280-screenshot.width)//2, 92))
    draw.text((28, 782), step, font=font(22), fill='#ffffff')
    image.save(target, 'PNG')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, default=ROOT / '.seo-audit/demo-frames')
    args = parser.parse_args()
    output = ROOT / 'src/static/demos'
    output.mkdir(parents=True, exist_ok=True)
    for demo in DEMOS.values():
        slug = demo['slug']
        screenshots = [args.frames / f'{slug}-input.jpg', args.frames / f'{slug}-result.jpg']
        if not all(path.exists() for path in screenshots):
            raise FileNotFoundError(f'Capture both input/result frames for {slug}')
        with TemporaryDirectory(prefix='tat-demo-') as temporary:
            folder = Path(temporary)
            segments = []
            for index, source in enumerate([screenshots[0], screenshots[1], screenshots[1]]):
                target = folder / f'scene-{index}.png'
                poster = frame(source, demo['title'], f'{index+1}. {STEPS[slug][index]}', target)
                if index == 0:
                    poster.save(output / f'{slug}.webp', 'WEBP', quality=85)
                segment = folder / f'scene-{index}.mp4'
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', str(target),
                    '-t', '8', '-r', '12', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                    '-pix_fmt', 'yuv420p', str(segment)], check=True)
                segments.append(segment)
            listing = folder / 'segments.txt'
            listing.write_text(''.join(f"file '{path.as_posix()}'\n" for path in segments), encoding='utf-8')
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing),
                            '-c', 'copy', '-movflags', '+faststart', str(output / f'{slug}.mp4')], check=True)
        captions = ['WEBVTT', '']
        for index, text in enumerate(STEPS[slug]):
            captions += [f'00:00:{index*8:02}.000 --> 00:00:{(index+1)*8:02}.000', text, '']
        (output / f'{slug}.vtt').write_text('\n'.join(captions), encoding='utf-8')
        print(f'{slug}: 24 seconds, English captions, poster and inline transcript', flush=True)


if __name__ == '__main__':
    main()
