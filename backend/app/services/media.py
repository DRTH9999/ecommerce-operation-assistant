import base64
import html
import io
import json
from pathlib import Path
import subprocess
import uuid

import httpx
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont


def demo_svg(product, plan):
    title = html.escape(plan['content_json'].get('copy', product['name'])[:40])
    name = html.escape(product['name'][:32])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#eff5ed"/><stop offset="1" stop-color="#d9e8dc"/></linearGradient>
<linearGradient id="b" x2="1"><stop stop-color="#28746a"/><stop offset=".5" stop-color="#5d9a8b"/><stop offset="1" stop-color="#347b6d"/></linearGradient></defs>
<rect width="1080" height="1080" fill="url(#bg)"/>
<circle cx="810" cy="720" r="350" fill="#d1e2d1"/>
<text x="75" y="110" font-family="sans-serif" font-size="24" fill="#327368" letter-spacing="6">QINGHE · CREATIVE STUDIO</text>
<text x="75" y="215" font-family="Microsoft YaHei,sans-serif" font-size="40" font-weight="bold" fill="#23483e">{title}</text>
<ellipse cx="570" cy="855" rx="215" ry="38" fill="#23483e" opacity=".12"/>
<rect x="415" y="340" width="280" height="490" rx="80" fill="url(#b)"/>
<rect x="448" y="300" width="214" height="95" rx="34" fill="#214e45"/>
<rect x="470" y="450" width="18" height="270" rx="9" fill="white" opacity=".13"/>
<text x="555" y="610" text-anchor="middle" fill="#edf3e5" font-size="32" font-family="sans-serif" letter-spacing="4">QINGHE</text>
<text x="75" y="960" font-family="Microsoft YaHei,sans-serif" font-size="28" fill="#23483e">{name}  /  ¥{product['price']:.2f}</text>
<text x="75" y="1020" font-family="Microsoft YaHei,sans-serif" font-size="22" fill="#61796c">演示排版示意 · 商品造型为占位，请用真实商品图替换后审核</text></svg>'''


def font(size):
    for path in ['C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrapped(draw, text, xy, fill, size=22, width=400, max_lines=5):
    x, y = xy
    face = font(size)
    line = ''
    lines = []
    for char in text:
        if char == '\n' or draw.textlength(line + char, font=face) > width:
            lines.append(line)
            line = '' if char == '\n' else char
        else:
            line += char
    if line:
        lines.append(line)
    for i, line in enumerate(lines[:max_lines]):
        draw.text((x, y + i * (size + 10)), line, fill=fill, font=face)


def demo_video(path, product, plan):
    content = plan['content_json']
    captions = [content.get('hook', product['name']), content.get('voiceover', product['selling_points']),
                content.get('cta', '查看商品详情')]
    frames = []
    for index, caption in enumerate(captions):
        image = Image.new('RGB', (480, 480), '#edf3eb')
        draw = ImageDraw.Draw(image)
        draw.text((32, 26), 'QINGHE / STORYBOARD', font=font(17), fill='#327368')
        draw.text((32, 67), f'0{index + 1}  /  分镜示意', font=font(21), fill='#214e45')
        draw.rounded_rectangle((185, 130, 295, 300), radius=30, fill='#438475')
        draw.rounded_rectangle((198, 114, 282, 144), radius=12, fill='#214e45')
        wrapped(draw, caption, (32, 327), '#214e45', 19, max_lines=3)
        draw.text((32, 451), '演示动态分镜 · 非真实拍摄 / AI 视频', font=font(13), fill='#647a70')
        frames.append(image.tobytes() * 20)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'rawvideo',
        '-vcodec', 'rawvideo', '-s', '480x480', '-pix_fmt', 'rgb24', '-r', '10', '-i', '-',
        '-an', '-vcodec', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(path)], input=b''.join(frames), capture_output=True, timeout=45, check=True)


def generate_media(settings, product, plan, job):
    directory = settings.data_dir / 'media'
    directory.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex
    is_video = job['job_kind'] == 'video'
    if settings.ai_mode == 'demo':
        path = directory / (file_id + ('.mp4' if is_video else '.svg'))
        if is_video:
            demo_video(path, product, plan)
        else:
            path.write_text(demo_svg(product, plan), encoding='utf-8')
        return {'asset_url': '/media/' + path.name, 'model_name': 'demo-storyboard' if is_video else 'demo-layout',
                'width': 480 if is_video else 1080, 'height': 480 if is_video else 1080,
                'duration_sec': 6 if is_video else 0}
    prompt = json.dumps({'product_name': product['name'], 'selling_points': product['selling_points'],
                         'plan': plan['content_json']}, ensure_ascii=False)
    if is_video:
        if not settings.video_api_url or not settings.video_api_key:
            raise ValueError('视频服务尚未配置，请设置 VIDEO_API_URL 和 VIDEO_API_KEY，或切回演示模式')
        with httpx.Client(timeout=min(settings.job_timeout_seconds - 1, 150), trust_env=False) as client:
            response = client.post(settings.video_api_url,
                headers={'Authorization': 'Bearer ' + settings.video_api_key},
                json={'prompt': prompt, 'format': 'mp4', 'duration_sec': 6})
            response.raise_for_status()
        data = response.json()
        raw = base64.b64decode(data['video_base64'], validate=True)
        if len(raw) > 50 * 1024 * 1024 or raw[4:8] != b'ftyp':
            raise ValueError('视频服务返回无效的 MP4 文件或文件过大')
        path = directory / (file_id + '.mp4')
        path.write_bytes(raw)
        return {'asset_url': '/media/' + path.name, 'model_name': 'configured-video-service',
                'width': 0, 'height': 0, 'duration_sec': 6}
    if not settings.ai_api_key or not settings.ai_image_model:
        raise ValueError('图片模型尚未配置，请设置 AI_API_KEY 和 AI_IMAGE_MODEL，或切回演示模式')
    with httpx.Client(timeout=min(settings.job_timeout_seconds - 1, 150), trust_env=False) as client:
        response = client.post(settings.ai_base_url.rstrip('/') + '/images/generations',
            headers={'Authorization': 'Bearer ' + settings.ai_api_key},
            json={'model': settings.ai_image_model, 'prompt': prompt, 'size': '1024x1024',
                  'n': 1, 'response_format': 'b64_json'})
        response.raise_for_status()
    raw = base64.b64decode(response.json()['data'][0]['b64_json'], validate=True)
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError('图片输出超过 25 MB')
    with Image.open(io.BytesIO(raw)) as original:
        original.load()
        width, height = original.size
        image = original.convert('RGB')
        path = directory / (file_id + '.png')
        image.save(path)
    return {'asset_url': '/media/' + path.name, 'model_name': settings.ai_image_model,
            'width': width, 'height': height, 'duration_sec': 0}
