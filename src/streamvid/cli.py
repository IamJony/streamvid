#!/usr/bin/env python3
# CLI de Streamvid. by IamJony

import argparse
import sys

from .extractors import (
    MP4UploadExtractor,
    FileMoonExtractor,
    VoeExtractor,
    StreamtapeExtractor,
    OkRuExtractor,
    UniversalExtractor,
    MixdropExtractor,
)


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


EXTRACTOR_INFO = {
    'mp4upload': {
        'name': 'MP4Upload',
        'class': MP4UploadExtractor,
        'example': 'https://www.mp4upload.com/embed-9lxsg2qkoclq.html'
    },
    'streamtape': {
        'name': 'Streamtape',
        'class': StreamtapeExtractor,
        'example': 'https://streamtape.com/e/jpYjkraO4ZhzVZk/01.mp4'
    },
    'filemoon': {
        'name': 'FileMoon',
        'class': FileMoonExtractor,
        'example': 'https://sfastwish.com/e/t0skqlzi01j0'
    },
    'voe': {
        'name': 'Voe',
        'class': VoeExtractor,
        'example': 'https://voe.sx/e/vnooybqweztc'
    },
    'okru': {
        'name': 'OkRu',
        'class': OkRuExtractor,
        'example': 'https://ok.ru/videoembed/6127798127135'
    },
    'mixdrop': {
        'name': 'Mixdrop',
        'class': MixdropExtractor,
        'example': 'https://mxdrop.to/e/4d99e8q1sn6jp'
    },
    'universal': {
        'name': 'Universal',
        'class': UniversalExtractor,
        'example': 'https://luluvdo.com/e/k60tod6pn7zk'
    }
}


def color_text(text, color):
    return f"{color}{text}{Colors.END}"


def detect_extractor(url):
    """Auto-detecta el extractor usando soporta() de cada uno."""
    for key, info in EXTRACTOR_INFO.items():
        if key == 'universal':
            continue
        try:
            if info['class']().soporta(url):
                return key
        except AttributeError:
            continue
    return 'universal'


def list_servers():
    print(f"\n{color_text('AVAILABLE SERVERS:', Colors.BOLD)}\n")
    for key, info in EXTRACTOR_INFO.items():
        print(f"  {color_text(key, Colors.CYAN)} {info['example']}")


def run_self_test():
    """Autotest offline: valida que los extractores están bien formados."""
    print_info("Autotest offline de extractores...\n")
    fallos = 0

    for key, info in EXTRACTOR_INFO.items():
        cls = info['class']
        nombre = info['name']
        try:
            cls(debug=False)
            print(f"  {color_text('✓', Colors.GREEN)} {nombre}")
        except Exception as e:
            print(f"  {color_text('✗', Colors.RED)} {nombre}: {e}")
            fallos += 1

    total = len(EXTRACTOR_INFO)
    print(f"\n{total - fallos}/{total} extractores válidos")
    return fallos == 0


def print_error(message):
    print(f"{color_text('Error:', Colors.RED)} {message}")


def print_success(message):
    print(f"{color_text('Success:', Colors.GREEN)} {message}")


def print_info(message):
    print(f"{color_text('Info:', Colors.BLUE)} {message}")


def run_extractor(name, url, debug=False):
    """Devuelve (resultado, extractor) para poder consultar obtener_headers()."""
    extractor_cls = EXTRACTOR_INFO[name]['class']
    extractor = extractor_cls(debug=debug)
    result = extractor.extraer(url)
    return result, extractor


def main():
    parser = argparse.ArgumentParser(
        description="Video extractor from multiple platforms",
        usage="%(prog)s [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] [--headers] <URL>"
    )

    parser.add_argument('url', nargs='?', help='Video embed URL to extract')
    parser.add_argument('-e', '--extractor', choices=EXTRACTOR_INFO.keys(),
                        help='Specify extractor to use')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug logging in the extractor')
    parser.add_argument('-i', '--info', action='store_true',
                        help='Show detailed information')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List all available servers')
    parser.add_argument('-t', '--test', action='store_true',
                        help='Run offline self-test of extractors')
    parser.add_argument('--headers', action='store_true',
                        help='Print the headers needed to consume the link')

    args = parser.parse_args()

    if args.list:
        list_servers()
        return

    if args.test:
        sys.exit(0 if run_self_test() else 1)

    if not args.url:
        print_error("URL not provided")
        print(f"\nUsage: {sys.argv[0]} [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] [--headers] <URL>")
        print(f"\n{color_text('Available extractors:', Colors.BOLD)}")
        for key in EXTRACTOR_INFO.keys():
            print(f"  {color_text(key, Colors.CYAN)}")
        sys.exit(1)

    name = args.extractor or detect_extractor(args.url)
    if not name or name not in EXTRACTOR_INFO:
        print_error(f"No extractor found for URL: {args.url}")
        print(f"Use {color_text('--extractor', Colors.YELLOW)} to specify manually.")
        print(f"Available: {', '.join([color_text(k, Colors.CYAN) for k in EXTRACTOR_INFO.keys()])}")
        sys.exit(1)

    extractor_info = EXTRACTOR_INFO[name]
    extractor_name = extractor_info['name']

    if args.info:
        print_info(f"Using extractor: {color_text(extractor_name, Colors.CYAN)}")
        print_info(f"URL: {color_text(args.url, Colors.CYAN)}")
        print()

    try:
        result, extractor = run_extractor(name, args.url, debug=args.debug)
    except Exception as e:
        if args.info:
            print(f"{color_text('✗', Colors.RED)} {extractor_name}: {color_text('ERROR', Colors.RED)}")
            print(f"  {color_text(str(e), Colors.RED)}")
        else:
            print_error(str(e))
        sys.exit(1)

    if result:
        if args.info:
            print(f"{color_text('✓', Colors.GREEN)} {extractor_name}: {color_text('FOUND', Colors.GREEN)}")

        # Headers (si se piden y el extractor los soporta)
        if args.headers and hasattr(extractor, "obtener_headers"):
            h = extractor.obtener_headers()
            if h:
                for k, v in h.items():
                    print(f"# {k}: {v}")

        if args.info:
            print(f"  {color_text('URL:', Colors.CYAN)} {result}")
        else:
            print(f"{color_text(result, Colors.GREEN)}")
        sys.exit(0)
    else:
        if args.info:
            print(f"{color_text('⚠', Colors.YELLOW)} {extractor_name}: {color_text('EMPTY', Colors.YELLOW)}")
        else:
            print_error(f"Could not extract video from: {args.url}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{color_text('Interrupted by user', Colors.YELLOW)}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
