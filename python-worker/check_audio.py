import ffmpeg
import sys

def check_audio(video_path):
    """Check if video has audio stream"""
    try:
        probe = ffmpeg.probe(video_path)
        
        print(f"=== Video Info: {video_path} ===")
        print(f"Format: {probe['format']['format_name']}")
        print(f"Duration: {probe['format']['duration']}s")
        print(f"\nStreams:")
        
        has_audio = False
        for stream in probe['streams']:
            codec_type = stream['codec_type']
            codec_name = stream.get('codec_name', 'unknown')
            
            if codec_type == 'video':
                print(f"  - Video: {codec_name} ({stream['width']}x{stream['height']})")
            elif codec_type == 'audio':
                has_audio = True
                channels = stream.get('channels', 'unknown')
                sample_rate = stream.get('sample_rate', 'unknown')
                print(f"  - Audio: {codec_name} ({channels} channels, {sample_rate} Hz)")
        
        if not has_audio:
            print("\n⚠️  WARNING: No audio stream found!")
        else:
            print("\n✅ Audio stream present")
            
        return has_audio
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py check_audio.py <video_file>")
        sys.exit(1)
    
    check_audio(sys.argv[1])
