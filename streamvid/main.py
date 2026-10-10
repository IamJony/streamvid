#!/usr/bin/env python3
# Main script for video extractors - CLI Interface
# Usage: streamvid <URL> [--extractor EXTRACTOR] [--info] [--list] [--test] [--debug]

from .mp4upload import MP4UploadExtractor
from .filemoon import FileMoonExtractor
from .voe import VoeExtractor
from .streamtape import StreamtapeExtractor
from .ok import OkRuExtractor
from .universal import UniversalExtractor

import argparse
import sys
import subprocess
import os


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


# Available extractors configuration
EXTRACTORS = {
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
    'ok': {
        'name': 'OkRu',
        'class': OkRuExtractor,
        'example': 'https://ok.ru/videoembed/6127798127135'
    },
    'universal': {
        'name': 'Universal',
        'class': UniversalExtractor,
        'example': 'https://luluvdo.com/e/k60tod6pn7zk'
    }
}

# Domain to extractor mapping
DOMAIN_MAP = {
    'mp4upload.com': 'mp4upload',
    'streamtape.com': 'streamtape',
    'sfastwish.com': 'filemoon',
    'filemoon.sx': 'filemoon',
    'voe.sx': 'voe',
    'ok.ru': 'ok',
    'luluvdo.com': 'universal'
}


def color_text(text, color):
    """Apply color to text"""
    return f"{color}{text}{Colors.END}"


def detect_extractor(url):
    """Auto-detect extractor based on URL domain"""
    for domain, extractor_key in DOMAIN_MAP.items():
        if domain in url:
            return extractor_key
    return None


def list_servers():
    """List all available servers"""
    print(f"\n{color_text('AVAILABLE SERVERS:', Colors.BOLD)}{Colors.END}\n")
    for key, info in EXTRACTORS.items():
        print(f"  {color_text(key, Colors.CYAN)} {info['example']}")


def run_test_script():
    """Execute the test_extractores.py script"""
    script_path = os.path.join(os.path.dirname(__file__), 'test_extractores.py')

    try:
        if not os.path.exists(script_path):
            print_error(f"Test script not found: {script_path}")
            return False

        print_info("Running extractor tests...\n")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            text=True
        )
        return result.returncode == 0

    except Exception as e:
        print_error(f"Error running test script: {str(e)}")
        return False


def print_error(message):
    """Print error message in red"""
    print(f"{color_text('Error:', Colors.RED)} {message}")


def print_success(message):
    """Print success message in green"""
    print(f"{color_text('Success:', Colors.GREEN)} {message}")


def print_info(message):
    """Print info message in blue"""
    print(f"{color_text('Info:', Colors.BLUE)} {message}")


def run_extractor(name, url, debug=False):
    """
    Instancia y ejecuta el extractor indicado.
    Devuelve el HLS o lanza excepción.
    """
    extractor_cls = EXTRACTORS[name]['class']
    extractor = extractor_cls(debug=debug)

    # Si el extractor expone extraer(), lo usamos.
    if hasattr(extractor, 'extraer'):
        return extractor.extraer(url)

    # Fallback por si algún extractor solo tiene el flujo partido (voe)
    if hasattr(extractor, 'obtener_contenido') and hasattr(extractor, 'extraer_video_src'):
        content = extractor.obtener_contenido(url)
        return extractor.extraer_video_src(content)

    raise RuntimeError(f"Extractor '{name}' no implementa extraer() ni el flujo alternativo")


def main():
    parser = argparse.ArgumentParser(
        description="Video extractor from multiple platforms",
        usage="%(prog)s [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] <URL>"
    )

    parser.add_argument('url', nargs='?', help='Video embed URL to extract')
    parser.add_argument('-e', '--extractor', choices=EXTRACTORS.keys(),
                        help='Specify extractor to use')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug logging in the extractor')
    parser.add_argument('-i', '--info', action='store_true',
                        help='Show detailed information')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List all available servers')
    parser.add_argument('-t', '--test', action='store_true',
                        help='Run test extractors script (test_extractores.py)')

    args = parser.parse_args()

    # --- Acciones que no requieren URL ---
    if args.list:
        list_servers()
        return

    if args.test:
        success = run_test_script()
        sys.exit(0 if success else 1)

    if not args.url:
        print_error("URL not provided")
        print(
            f"\nUsage: {sys.argv[0]} [--extractor EXTRACTOR] [--debug] [--info] [--list] [--test] <URL>")
        print(f"\n{color_text('Available extractors:', Colors.BOLD)}")
        for key in EXTRACTORS.keys():
            print(f"  {color_text(key, Colors.CYAN)}")
        sys.exit(1)

    # --- Detectar / validar extractor ---
    name = args.extractor or detect_extractor(args.url)
    if not name or name not in EXTRACTORS:
        print_error(f"No extractor found for URL: {args.url}")
        print(
            f"Use {color_text('--extractor', Colors.YELLOW)} to specify manually.")
        print(
            f"Available: {', '.join([color_text(k, Colors.CYAN) for k in EXTRACTORS.keys()])}")
        sys.exit(1)

    extractor_info = EXTRACTORS[name]
    extractor_name = extractor_info['name']

    if args.info:
        print_info(f"Using extractor: {color_text(extractor_name, Colors.CYAN)}")
        print_info(f"URL: {color_text(args.url, Colors.CYAN)}")
        print()

    # --- Extraer ---
    try:
        result = run_extractor(name, args.url, debug=args.debug)
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
