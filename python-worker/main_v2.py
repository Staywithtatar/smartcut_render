# AI-Driven Video Processor - FastAPI Server v2
# Clean architecture with AI-controlled processing
# Now with performance monitoring and optimization

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import json
import logging
from pathlib import Path
from datetime import datetime

from ai_models import AIEditingScript
from pipeline import ProcessingPipeline
from performance_utils import memory_monitor, check_disk_space, temp_file_cleanup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AutoCut AI Video Processor",
    description="AI-driven professional video editing",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
(TEMP_DIR / "uploads").mkdir(exist_ok=True)
(TEMP_DIR / "outputs").mkdir(exist_ok=True)

# Job status tracking
class ProcessingStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    current_step: str
    message: Optional[str] = None
    error: Optional[str] = None

job_status: Dict[str, ProcessingStatus] = {}

@app.get("/")
def read_root():
    """Health check"""
    return {
        "status": "running",
        "message": "AutoCut AI Video Processor v2.0",
        "architecture": "AI-Driven FFmpeg",
        "features": [
            "AI content analysis",
            "Dynamic zoom with easing",
            "Selective blur effects",
            "Audio normalization",
            "Smart color grading",
            "Keyword-highlighted subtitles",
            "Aspect ratio conversion"
        ]
    }

@app.get("/health")
def health_check():
    """Detailed health check"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        ffmpeg_status = "installed"
        ffmpeg_version = result.stdout.split('\n')[0]
    except Exception as e:
        ffmpeg_status = "not found"
        ffmpeg_version = str(e)
    
    return {
        "status": "healthy",
        "ffmpeg": {
            "status": ffmpeg_status,
            "version": ffmpeg_version
        },
        "temp_dir": str(TEMP_DIR),
        "version": "2.0.0"
    }

@app.post("/process", response_class=FileResponse)
async def process_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    editing_script: str = Form(...)
):
    """
    Process video with AI-driven editing
    
    The editing_script should be a JSON string containing AIEditingScript
    """
    job_id = None
    
    try:
        # Parse AI editing script
        try:
            script_data = json.loads(editing_script)
            script = AIEditingScript(**script_data)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid editing script: {str(e)}"
            )
        
        job_id = script.job_id
        logger.info(f"Starting job: {job_id}")
        logger.info(f"Content: {script.metadata.contentType}, Mood: {script.metadata.mood}")
        
        # Initialize job status
        job_status[job_id] = ProcessingStatus(
            job_id=job_id,
            status="uploading",
            progress=0,
            current_step="Uploading video..."
        )
        
        # Validate video
        if not video.content_type or not video.content_type.startswith('video/'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {video.content_type}"
            )
        
        # Check disk space
        if not check_disk_space(TEMP_DIR, required_gb=2.0):
            raise HTTPException(
                status_code=507,
                detail="Insufficient disk space"
            )
        
        # Save uploaded video
        input_path = TEMP_DIR / "uploads" / f"{job_id}_input.mp4"
        with open(input_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"Video saved: {input_path} ({file_size_mb:.2f} MB)")
        
        # Update status
        job_status[job_id].status = "processing"
        job_status[job_id].progress = 10
        job_status[job_id].current_step = "Initializing AI pipeline..."
        
        # Process with memory monitoring and cleanup
        with memory_monitor(job_id):
            with temp_file_cleanup(input_path):
                # Initialize pipeline
                output_path = TEMP_DIR / "outputs" / f"{job_id}_output.mp4"
                pipeline = ProcessingPipeline(input_path, output_path, script)
                
                # Execute AI-driven processing
                job_status[job_id].progress = 20
                job_status[job_id].current_step = "Processing with AI instructions..."
                
                final_path = pipeline.execute()
        
        # Update final status
        job_status[job_id].status = "completed"
        job_status[job_id].progress = 100
        job_status[job_id].current_step = "Complete!"
        job_status[job_id].message = "AI-driven processing complete"
        
        # Schedule cleanup (but keep output)
        background_tasks.add_task(cleanup_temp_files, job_id, keep_output=True)
        
        # Return processed video
        return FileResponse(
            final_path,
            media_type="video/mp4",
            filename=f"{job_id}_output.mp4",
            headers={
                "Content-Disposition": f"attachment; filename={job_id}_output.mp4",
                "X-Job-ID": job_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error for job {job_id}: {e}", exc_info=True)
        
        if job_id:
            job_status[job_id].status = "failed"
            job_status[job_id].current_step = "Failed"
            job_status[job_id].error = str(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Processing failed",
                "message": str(e),
                "job_id": job_id
            }
        )

@app.get("/status/{job_id}", response_model=ProcessingStatus)
def get_job_status(job_id: str):
    """Get processing status"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status[job_id]

def cleanup_temp_files(job_id: str, keep_output: bool = True):
    """Cleanup temporary files"""
    try:
        # Remove input
        input_file = TEMP_DIR / "uploads" / f"{job_id}_input.mp4"
        if input_file.exists():
            input_file.unlink()
        
        # Remove processing files
        processing_dir = TEMP_DIR / "processing"
        if processing_dir.exists():
            import shutil
            shutil.rmtree(processing_dir)
        
        # Optionally remove output
        if not keep_output:
            output_file = TEMP_DIR / "outputs" / f"{job_id}_output.mp4"
            if output_file.exists():
                output_file.unlink()
                
        logger.info(f"Cleaned up files for job: {job_id}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("AutoCut AI Video Processor v2.0")
    print("=" * 70)
    print(f"Temp directory: {TEMP_DIR}")
    print(f"Server: http://localhost:8000")
    print(f"Docs: http://localhost:8000/docs")
    print("=" * 70)
    print("\nFeatures:")
    print("  - AI-driven editing decisions")
    print("  - Dynamic zoom with easing")
    print("  - Selective blur effects")
    print("  - Audio normalization")
    print("  - Smart color grading")
    print("  - Keyword-highlighted subtitles")
    print("\nReady to process videos!\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
