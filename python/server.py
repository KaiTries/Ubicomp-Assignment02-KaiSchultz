import http.server
import socketserver

PORT = 8081

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the length of the data
        content_length = int(self.headers['Content-Length'])
        # Read the data itself
        post_data = self.rfile.read(content_length)
        print(post_data)
        # Send response status code
        self.send_response(200)
        # Send headers
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Send the response body
        response = f"Received POST request with data: {post_data.decode('utf-8')}"
        self.wfile.write(response.encode('utf-8'))

with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()