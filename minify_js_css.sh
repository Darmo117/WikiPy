# Minifies the JS and CSS files within the static directory of WikiPy app only.
python manage.py minify_js_css WikiPy/static/WikiPy/js WikiPy/static/WikiPy/js/special_pages \
  WikiPy/static/WikiPy/css WikiPy/static/WikiPy/css/special_pages WikiPy/static/WikiPy/skins/default
