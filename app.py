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
        
        # Handle optional subtitles
        subs_path = None
        if 'subtitles' in request.files:
            logging.info(f"ID {run_id}: Subtitles file received.")
            subs_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_subs.ass")
            request.files['subtitles'].save(subs_path)
        else:
            logging.info(f"ID {run_id}: No subtitles file received.")
        
        logging.info(f"Rendering video for ID: {run_id}")

        # 3. Run FFmpeg
        cmd = [
            'ffmpeg', '-y', 
            '-loop', '1', 
            '-i', img_path, 
            '-i', audio_path
        ]

        # Add subtitle filter if present
        if subs_path:
            # Escape the path for the filter
            escaped_subs_path = subs_path.replace(":", "\\:").replace("'", "\\'")
            cmd.extend(['-vf', f"subtitles='{escaped_subs_path}'"])

        cmd.extend([
            '-c:v', 'libx264', 
            '-tune', 'stillimage', 
            '-c:a', 'aac', 
            '-b:a', '192k', 
            '-pix_fmt', 'yuv420p', 
            '-shortest', 
            output_path
        ])
        
        # Log the full command
        logging.info(f"ID {run_id}: Running command: {' '.join(cmd)}")
        
        # Run and capture output
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Log stderr (where ffmpeg prints stats and warnings)
        logging.info(f"ID {run_id}: FFmpeg Output:\n{result.stderr}")
        
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
            if 'subs_path' in locals() and subs_path and os.path.exists(subs_path): os.remove(subs_path)
        except Exception as cleanup_error:
            logging.warning(f"Cleanup failed: {cleanup_error}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
