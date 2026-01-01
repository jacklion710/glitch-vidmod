"""
Simple video viewer to view original and corrupted videos side by side
Controls:
  - A/D: Navigate to previous/next video pair
  - Space: Play/Pause
  - Q or ESC: Quit
"""

import os
import argparse
import cv2
import glob
import numpy as np

# Runtime: O(N) to scan videos and build pairs, where N = number of files in vids/
def parse_args():
    parser = argparse.ArgumentParser(description="Side-by-side original vs corrupted video viewer")
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Video filename or base name to start on (e.g. 'bball.mov' or 'bball')",
    )
    parser.add_argument(
        "--paused",
        action="store_true",
        help="Start paused",
    )
    return parser.parse_args()

args = parse_args()

# Get all video files from vids directory
video_extensions = ['*.mp4', '*.mov', '*.avi', '*.mkv', '*.m4v', '*.webm']
original_videos = []
for ext in video_extensions:
    original_videos.extend(glob.glob(f'vids/{ext}'))

# Sort videos and extract base names
original_videos = sorted(original_videos)
video_pairs = []

for orig_path in original_videos:
    base_name = os.path.splitext(os.path.basename(orig_path))[0]
    corrupted_path = f'out/{base_name}_corrupted.mp4'
    
    if os.path.exists(corrupted_path):
        video_pairs.append({
            'name': base_name,
            'original': orig_path,
            'corrupted': corrupted_path
        })

if not video_pairs:
    print("No video pairs found!")
    exit(1)

# Current state
current_pair_index = 0
is_playing = not args.paused
original_cap = None
corrupted_cap = None
original_frame = None
corrupted_frame = None

# Runtime: O(N) where N = len(video_pairs)
def find_pair_index(video_arg: str) -> int:
    if not video_arg:
        return 0
    base = os.path.splitext(os.path.basename(video_arg))[0].strip()
    if not base:
        return 0
    for i, pair in enumerate(video_pairs):
        if pair.get("name") == base:
            return i
    return 0

def load_video_pair(pair_index):
    global original_cap, corrupted_cap, original_frame, corrupted_frame
    
    if original_cap is not None:
        original_cap.release()
    if corrupted_cap is not None:
        corrupted_cap.release()
    
    pair = video_pairs[pair_index]
    
    original_cap = cv2.VideoCapture(pair['original'])
    corrupted_cap = cv2.VideoCapture(pair['corrupted'])
    
    if not original_cap.isOpened():
        print(f"Error opening original video: {pair['original']}")
        return False
    if not corrupted_cap.isOpened():
        print(f"Error opening corrupted video: {pair['corrupted']}")
        return False
    
    ret1, original_frame = original_cap.read()
    ret2, corrupted_frame = corrupted_cap.read()
    return ret1 and ret2

def resize_frame(frame, max_width, max_height):
    if frame is None:
        return None
    height, width = frame.shape[:2]
    if width > max_width or height > max_height:
        scale = min(max_width / width, max_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(frame, (new_width, new_height))
    return frame

def combine_frames_side_by_side(orig_frame, corr_frame, max_width_per_video, max_height):
    orig_resized = resize_frame(orig_frame, max_width_per_video, max_height)
    corr_resized = resize_frame(corr_frame, max_width_per_video, max_height)
    
    if orig_resized is None or corr_resized is None:
        return None
    
    # Make both frames the same height
    target_height = max(orig_resized.shape[0], corr_resized.shape[0])
    orig_h, orig_w = orig_resized.shape[:2]
    corr_h, corr_w = corr_resized.shape[:2]
    
    # Resize to same height
    orig_scale = target_height / orig_h
    corr_scale = target_height / corr_h
    orig_new_w = int(orig_w * orig_scale)
    corr_new_w = int(corr_w * corr_scale)
    
    orig_resized = cv2.resize(orig_resized, (orig_new_w, target_height))
    corr_resized = cv2.resize(corr_resized, (corr_new_w, target_height))
    
    # Combine side by side
    combined = np.hstack([orig_resized, corr_resized])
    return combined

# Load first video pair
current_pair_index = find_pair_index(args.video)
if args.video and current_pair_index == 0:
    requested = os.path.splitext(os.path.basename(args.video))[0]
    if requested and video_pairs and video_pairs[0].get("name") != requested:
        print(f"Requested video '{args.video}' not found in pairs. Starting at first pair.")

if not load_video_pair(current_pair_index):
    print("Failed to load first video pair")
    exit(1)

print(f"Loaded {len(video_pairs)} video pairs")
print("Controls: A/D = prev/next pair, Space = play/pause, Q/ESC = quit")

while True:
    if original_frame is not None and corrupted_frame is not None:
        # Combine frames side by side (each video max 640x720, total 1280x720)
        combined_frame = combine_frames_side_by_side(original_frame, corrupted_frame, 640, 720)
        
        if combined_frame is not None:
            # Add text overlays
            pair = video_pairs[current_pair_index]
            title = f"{pair['name']} ({current_pair_index + 1}/{len(video_pairs)})"
            cv2.putText(combined_frame, title, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add labels for each side
            frame_height = combined_frame.shape[0]
            frame_width = combined_frame.shape[1]
            left_width = frame_width // 2
            
            # Left side label (ORIGINAL)
            cv2.putText(combined_frame, "ORIGINAL", (10, frame_height - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Right side label (CORRUPTED)
            cv2.putText(combined_frame, "CORRUPTED", (left_width + 10, frame_height - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # Add controls hint
            cv2.putText(combined_frame, "A/D: Prev/Next Pair | Space: Play/Pause | Q: Quit", 
                       (10, frame_height - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('Video Viewer - Side by Side', combined_frame)
    
    if is_playing:
        ret1, original_frame = original_cap.read()
        ret2, corrupted_frame = corrupted_cap.read()
        
        if not ret1 or not ret2:
            # Loop both videos
            original_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            corrupted_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret1, original_frame = original_cap.read()
            ret2, corrupted_frame = corrupted_cap.read()
    
    key = cv2.waitKey(30)
    
    if key == ord('q') or key == 27:  # 'q' or ESC
        break
    elif key == ord(' '):  # Space - play/pause
        is_playing = not is_playing
    elif key == ord('a') or key == ord('A'):  # 'a' - previous pair
        current_pair_index = (current_pair_index - 1) % len(video_pairs)
        load_video_pair(current_pair_index)
    elif key == ord('d') or key == ord('D'):  # 'd' - next pair
        current_pair_index = (current_pair_index + 1) % len(video_pairs)
        load_video_pair(current_pair_index)

# Cleanup
if original_cap is not None:
    original_cap.release()
if corrupted_cap is not None:
    corrupted_cap.release()
cv2.destroyAllWindows()

