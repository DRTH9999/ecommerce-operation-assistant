"""只解析公开静态 HTML。固定已校验的公网 IP，逐跳验证重定向，拒绝内网目标。"""
import http.client
import ipaddress
import math
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from fastapi import HTTPException

from ..schemas import http_url

MAX_BYTES = 1024 * 1024


def public_address(url):
    try:
        http_url(url)
        parsed = urlsplit(url)
        if parsed.port not in (None, 80, 443):
            raise ValueError('port')
        hostname = parsed.hostname.encode('idna').decode()
        addresses = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('not public')
        return parsed, addresses[0][4][0], hostname
    except (ValueError, OSError, UnicodeError):
        raise HTTPException(422, '只允许标准端口的公网 HTTP/HTTPS 链接，拒绝本机、内网和无法解析的地址')


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port):
        super().__init__(host, port, timeout=8, context=ssl.create_default_context())
        self.pinned_ip = ip

    def connect(self):
        sock = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class PageInfo(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_parts = []
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            self.meta[attrs.get('property', attrs.get('name', ''))] = attrs.get('content', '')[:4000]

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data[:1000])


def parse_public_page(url):
    for _ in range(4):
        parsed, ip, hostname = public_address(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        connection = PinnedHTTPS(hostname, ip, port) if parsed.scheme == 'https' else http.client.HTTPConnection(ip, port, timeout=8)
        try:
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
            connection.request('GET', path, headers={'Host': hostname, 'User-Agent': 'CommerceWorkbench/1.0 (public-metadata-only)',
                                                     'Accept': 'text/html', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                url = urljoin(url, response.getheader('Location', ''))
                continue
            if response.status != 200:
                raise HTTPException(422, f'公开页面返回 HTTP {response.status}；请改用人工录入或平台授权接口')
            if 'text/html' not in response.getheader('Content-Type', '').lower():
                raise HTTPException(422, '该链接不是可解析的公开 HTML 页面')
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise HTTPException(422, '页面超过 1 MB，已停止解析')
            parser = PageInfo()
            charset = response.headers.get_content_charset() or 'utf-8'
            parser.feed(data.decode(charset, errors='replace'))
            title = parser.meta.get('og:title') or ''.join(parser.title_parts).strip()
            if not title:
                raise HTTPException(422, '页面未提供公开标题，请手动补充')
            price_text = parser.meta.get('product:price:amount', parser.meta.get('og:price:amount', ''))
            try:
                price = float(price_text)
                if not math.isfinite(price) or price < 0 or price > 100000000:
                    price = 0
            except ValueError:
                price = 0
            return {'title': title[:500], 'price': price,
                    'main_image': urljoin(url, parser.meta['og:image']) if parser.meta.get('og:image') else '',
                    'selling_points': parser.meta.get('description', parser.meta.get('og:description', '')),
                    'source_url': url, 'note': '仅提取页面自带的静态元信息；未推断销量，不自动覆盖人工竞品。'}
        except HTTPException:
            raise
        except (OSError, http.client.HTTPException, ValueError, LookupError):
            raise HTTPException(422, '无法读取公开页面，可能需要登录或已限制访问；请改用人工录入')
        finally:
            connection.close()
    raise HTTPException(422, '重定向次数过多，已停止解析')
