"""
ffmpeg -y -i "input.mp4" -c:v libx264 -x264-params keyint=10:keyint_min=10:bframes=0 -bsf:v noise=amount='3000*not(key)' -pix_fmt yuv420p "corrupted_vid.mp4"
"""

# For each video in the vid/ directory, run the command above
# Save the corrupted video in the out/ directory
# Keep the original videos filename but append _corrupted to the end
# Print the filename of the corrupted video

import os
import subprocess

# Get the list of videos in the vids/ directory
videos = os.listdir('vids')

# Video file extensions to process
video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.webm'}

# For each video, run the command above
for video in videos:
    # Skip directories and non-video files
    if os.path.isdir(f'vids/{video}') or not any(video.lower().endswith(ext) for ext in video_extensions):
        continue
    
    output_filename = f"{video.split('.')[0]}_corrupted.mp4"
    subprocess.run(['ffmpeg', '-y', '-i', f'vids/{video}', '-c:v', 'libx264', '-x264-params', 'keyint=10:keyint_min=10:bframes=0', '-bsf:v', 'noise=amount=3000*not(key)', '-pix_fmt', 'yuv420p', f'out/{output_filename}'])
    print(output_filename)