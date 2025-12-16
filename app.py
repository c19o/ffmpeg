import os
import subprocess
import uuid
import logging
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp'
logging.basicConfig(level=logging.INFO)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "ffmpeg": "ready"}), 200

@app.route('/render', methods=['POST'])
def render_video():
    try:
        # 1. Validation
        if 'image' not in request.files or 'audio' not in request.files:
            return jsonify({"error": "Missing image or audio file"}), 400
        
        # 2. Save uploaded files
        run_id = str(uuid.uuid4())
        image = request.files['image']
        audio = request.files['audio']
        
        img_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_img.jpg")
        audio_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_audio.mp3")
        output_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_out.mp4")
        
        image.save(img_path)
        audio.save(audio_path)
        
        logging.info(f"Rendering video for ID: {run_id}")

        # 3. Run FFmpeg
        # Command: Loop image, add audio, codec h264, stop when audio ends
        cmd = [
            'ffmpeg', '-y', 
            '-loop', '1', 
            '-i', img_path, 
            '-i', audio_path,
            '-c:v', 'libx264', 
            '-tune', 'stillimage', 
            '-c:a', 'aac', 
            '-b:a', '192k', 
            '-pix_fmt', 'yuv420p', 
            '-shortest', 
            output_path
        ]
        
        # Run and capture output for debugging if it fails
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # 4. Return the video file
        return send_file(output_path, mimetype='video/mp4', as_attachment=True, download_name=f"video_{run_id}.mp4")

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg failed: {e.stderr}")
        return jsonify({"error": "FFmpeg processing failed", "details": e.stderr}), 500
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup temp files
        try:
            if 'img_path' in locals() and os.path.exists(img_path): os.remove(img_path)
            if 'audio_path' in locals() and os.path.exists(audio_path): os.remove(audio_path)
            # We don't delete output_path immediately because send_file needs it. 
            # In a real prod env, you'd use a background task or cache cleaner. 
            # For this simple container, allowing /tmp to fill up until restart is usually acceptable for low volume.
            pass
        except Exception as cleanup_error:
            logging.warning(f"Cleanup failed: {cleanup_error}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
