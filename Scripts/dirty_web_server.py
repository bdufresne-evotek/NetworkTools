# Author - Bryan Dufresne
# Description:
"""Creates a temporary web server and hosts content from the directory 'C:\Web'."""

import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# Specify the directory you want to serve
directory_to_serve = 'C:\Web'
if not os.path.exists(directory_to_serve):
    os.makedirs(directory_to_serve)

# Potentially create a browse button to select the Web dir.

# Change the working directory to the specified directory
os.chdir(directory_to_serve)

# Specify the host and port for the server
host = '10.2.2.184'
port = 80

# Create a custom request handler to disable directory listing
class NoListingHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):
        self.send_error(404, "No permission to list directory")

# Create and run the HTTP server
with TCPServer((host, port), NoListingHandler) as httpd:
    print(f"Serving on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is stopped.")

