import re

# Comprueba si contiene funciones eval, regresa true o false


def isEval(html_content):

    return bool(re.search(
        r'<script[^>]*type=[\'"]text/javascript[\'"][^>]*>.*?eval\(function\(p,a,c,k,e,d\).*?</script>',
        html_content,
        re.DOTALL | re.IGNORECASE
    ))
