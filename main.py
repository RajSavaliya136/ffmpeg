import os
import subprocess
from flask import Flask, Response, request, abort

app = Flask(__name__)

# Path to your video file
VIDEO_FILE_PATH = '1.mp4'


def generate_stream():
    """
    Function to stream video using FFmpeg.
    It reads the video file and streams it as chunks.
    """
    ffmpeg_command = [
        'ffmpeg',
        '-i', VIDEO_FILE_PATH,       # Input file
        '-f', 'mp4',                 # Format: MP4
        '-movflags', 'frag_keyframe+empty_moov',  # Fragmented MP4 for streaming
        '-c:v', 'libx264',           # Video codec
        '-c:a', 'aac',               # Audio codec
        '-f', 'mpegts',              # MPEG transport stream (for chunked output)
        'pipe:1'                     # Output to pipe
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        data = process.stdout.read(1024)
        if not data:
            break
        yield data

    process.stdout.close()
    process.wait()


@app.route('/stream')
def stream():
    """
    Stream the video content to the client.
    """
    if not os.path.exists(VIDEO_FILE_PATH):
        abort(404)

    range_header = request.headers.get('Range', None)
    file_size = os.path.getsize(VIDEO_FILE_PATH)

    try:
        if range_header:
            # Example Range header: bytes=0-1024
            byte_range = range_header.replace('bytes=', '').split('-')
            start_byte = int(byte_range[0])
            end_byte = int(byte_range[1]) if byte_range[1] else file_size - 1

            # Ensure the requested range is valid
            if start_byte >= file_size or end_byte >= file_size or start_byte > end_byte:
                abort(416, description="Requested Range Not Satisfiable")

            # Length of content to be sent
            content_length = end_byte - start_byte + 1

            def partial_stream(start_byte):
                with open(VIDEO_FILE_PATH, 'rb') as f:
                    f.seek(start_byte)  # Move the pointer to the start byte
                    chunk_size = 1024 * 8  # Chunk size for streaming
                    while start_byte <= end_byte:
                        chunk = f.read(min(chunk_size, end_byte - start_byte + 1))
                        if not chunk:
                            break
                        start_byte += len(chunk)
                        yield chunk

            headers = {
                'Content-Range': f'bytes {start_byte}-{end_byte}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': content_length,
                'Content-Type': 'video/mp4',
            }

            return Response(partial_stream(start_byte), status=206, headers=headers)

        else:
            # Full video stream (No Range header provided)
            def full_stream():
                with open(VIDEO_FILE_PATH, 'rb') as f:
                    while chunk := f.read(1024 * 8):
                        yield chunk

            headers = {
                'Content-Length': file_size,
                'Content-Type': 'video/mp4',
            }
            return Response(full_stream(), status=200, headers=headers)

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error: {str(e)}")
        abort(500, description="An error occurred while streaming the video")




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9100, debug=True)
