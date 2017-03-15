import os
import techela
import threading
import webbrowser

port = 5543
url = "http://127.0.0.1:{0}".format(port)

print(port, url)
threading.Timer(1.25, lambda: webbrowser.open(url)).start()

os.chdir(os.path.expanduser('~/Box Sync/s17-06-364/assignments'))

techela.app.run(port=port, debug=True)
