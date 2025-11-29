from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import json
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from video_processor import VideoProcessor, ProcessingOptions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AutoCut Video Processor",
    description="Professional AI-powered video editing service",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
(TEMP_DIR / "uploads").mkdir(exist_ok=True)
(TEMP_DIR / "processing").mkdir(exist_ok=True)
(TEMP_DIR / "outputs").mkdir(exist_ok=True)

# Pydantic models
class EditingScript(BaseModel):
    """Editing script from AI analysis"""
    job_id: str
    jumpCuts: Optional[List[Dict]] = Field(default_factory=list)
    subtitles: Optional[List[Dict]] = Field(default_factory=list)
    highlights: Optional[List[Dict]] = Field(default_factory=list)
    style: Optional[str] = Field(default="professional", description="Subtitle style: professional, viral, minimal")
    color_grading: Optional[str] = Field(default="vibrant", description="Color grading: vibrant, cinematic, natural")
    enable_zoom: Optional[bool] = Field(default=True, description="Enable zoom effects on highlights")
    enable_transitions: Optional[bool] = Field(default=True, description="Enable smooth transitions")

class ProcessingStatus(BaseModel):
    """Processing status response"""
    job_id: str
    status: str
    progress: int
    current_step: str
    message: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    ffmpeg: Dict
    temp_dir: str
    directories: Dict
    version: str

# In-memory job status tracking
job_status: Dict[str, ProcessingStatus] = {}

@app.get("/", response_model=Dict)
def read_root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "AutoCut Python Worker is ready!",
        "version": "2.0.0",
        "features": [
            "Smart jump cuts with smooth transitions",
            "Professional animated subtitles (3 styles)",
            "Zoom effects on key moments",
            "Color grading (3 presets)",
            "Blurred background for better framing",
            "Audio enhancement",
            "9:16 aspect ratio conversion"
        ]
    }

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Detailed health check"""
    import subprocess
    
    # Check FFmpeg
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
    except subprocess.TimeoutExpired:
        ffmpeg_status = "timeout"
        ffmpeg_version = "FFmpeg check timed out"
    except Exception as e:
        ffmpeg_status = "not found"
        ffmpeg_version = str(e)
    
    return HealthResponse(
        status="healthy",
        ffmpeg={
            "status": ffmpeg_status,
            "version": ffmpeg_version
        },
        temp_dir=str(TEMP_DIR),
        directories={
            "uploads": (TEMP_DIR / "uploads").exists(),
            "processing": (TEMP_DIR / "processing").exists(),
            "outputs": (TEMP_DIR / "outputs").exists()
        },
        version="2.0.0"
    )

@app.post("/process", response_class=FileResponse)
async def process_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Input video file"),
    editing_script: str = Form(..., description="JSON editing script")
):
    """
    Process video with professional editing
    
    Features:
    - Smart jump cuts with smooth fade transitions
    - Professional subtitles with multiple styles
    - Zoom effects on highlighted moments
    - Color grading (vibrant/cinematic/natural)
    - Blurred background for better framing
    - Audio enhancement
    
    Returns:
        Processed video file ready for TikTok/Reels
    """
    job_id = None
    input_path = None
    
    try:
        # Parse and validate editing script
        try:
            script_data = json.loads(editing_script)
            script = EditingScript(**script_data)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in editing script: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid editing script format: {str(e)}"
            )
        
        job_id = script.job_id
        logger.info(f"📥 Starting job: {job_id}")
        
        # Initialize job status
        job_status[job_id] = ProcessingStatus(
            job_id=job_id,
            status="uploading",
            progress=0,
            current_step="Uploading video..."
        )
        
        # Validate video file
        if not video.content_type or not video.content_type.startswith('video/'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {video.content_type}. Must be a video file."
            )
        
        # Save uploaded video
        input_path = TEMP_DIR / "uploads" / f"{job_id}_input.mp4"
        with open(input_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"✅ Video saved: {input_path} ({file_size_mb:.2f} MB)")
        
        # Update status
        job_status[job_id].status = "processing"
        job_status[job_id].progress = 10
        job_status[job_id].current_step = "Initializing processor..."
        
        # Initialize processor with options
        output_path = TEMP_DIR / "outputs" / f"{job_id}_output.mp4"
        options = ProcessingOptions(
            subtitle_style=script.style,
            color_grading=script.color_grading,
            enable_zoom=script.enable_zoom,
            enable_transitions=script.enable_transitions
        )
        processor = VideoProcessor(str(input_path), str(output_path), options)
        
        current_video = str(input_path)
        total_steps = 5
        current_step_num = 0
        
        # Step 1: Apply jump cuts with smooth transitions
        if script.jumpCuts and len(script.jumpCuts) > 0:
            current_step_num += 1
            job_status[job_id].current_step = f"Applying {len(script.jumpCuts)} jump cuts..."
            job_status[job_id].progress = int((current_step_num / total_steps) * 100)
            logger.info(f"✂️  Step {current_step_num}/{total_steps}: Applying jump cuts")
            
            current_video = processor.apply_jump_cuts(script.jumpCuts)
            logger.info(f"✅ Jump cuts applied")
        
        # Step 2: Add zoom effects on highlights
        if script.enable_zoom and script.highlights and len(script.highlights) > 0:
            current_step_num += 1
            job_status[job_id].current_step = f"Adding zoom effects at {len(script.highlights)} moments..."
            job_status[job_id].progress = int((current_step_num / total_steps) * 100)
            logger.info(f"🔍 Step {current_step_num}/{total_steps}: Adding zoom effects")
            
            current_video = processor.add_zoom_effects(current_video, script.highlights)
            logger.info(f"✅ Zoom effects added")
        
        # Step 3: Apply color grading
        current_step_num += 1
        job_status[job_id].current_step = f"Applying {script.color_grading} color grading..."
        job_status[job_id].progress = int((current_step_num / total_steps) * 100)
        logger.info(f"🎨 Step {current_step_num}/{total_steps}: Color grading")
        
        current_video = processor.add_color_grading(current_video, script.color_grading)
        logger.info(f"✅ Color grading applied")
        
        # Step 4: Add professional subtitles
        if script.subtitles and len(script.subtitles) > 0:
            current_step_num += 1
            job_status[job_id].current_step = f"Adding {len(script.subtitles)} subtitles ({script.style} style)..."
            job_status[job_id].progress = int((current_step_num / total_steps) * 100)
            logger.info(f"💬 Step {current_step_num}/{total_steps}: Adding subtitles")
            
            current_video = processor.add_subtitles(script.subtitles, current_video, script.style)
            logger.info(f"✅ Subtitles added")
        
        # Step 5: Convert to 9:16 with blurred background
        current_step_num += 1
        job_status[job_id].current_step = "Converting to 9:16 format..."
        job_status[job_id].progress = int((current_step_num / total_steps) * 100)
        logger.info(f"📐 Step {current_step_num}/{total_steps}: Converting aspect ratio")
        
        final_path = processor.change_aspect_ratio(current_video, '9:16')
        logger.info(f"✅ Video processed successfully: {final_path}")
        
        # Update final status
        job_status[job_id].status = "completed"
        job_status[job_id].progress = 100
        job_status[job_id].current_step = "Processing complete!"
        job_status[job_id].message = f"Video processed successfully in {total_steps} steps"
        
        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_temp_files, job_id, keep_output=True)
        
        # Return processed video
        return FileResponse(
            final_path,
            media_type="video/mp4",
            filename=f"{job_id}_output.mp4",
            headers={
                "Content-Disposition": f"attachment; filename={job_id}_output.mp4",
                "X-Job-ID": job_id,
                "X-Processing-Steps": str(total_steps)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Processing error for job {job_id}: {e}", exc_info=True)
        
        if job_id:
            job_status[job_id].status = "failed"
            job_status[job_id].current_step = "Processing failed"
            job_status[job_id].error = str(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Video processing failed",
                "message": str(e),
                "job_id": job_id
            }
        )

@app.get("/status/{job_id}", response_model=ProcessingStatus)
def get_job_status(job_id: str):
    """Get processing status for a job"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]

@app.post("/test")
async def test_upload(video: UploadFile = File(...)):
    """Simple test endpoint to verify file upload works"""
    try:
        content = await video.read()
        return {
            "filename": video.filename,
            "content_type": video.content_type,
            "size": len(content),
            "size_mb": round(len(content) / (1024 * 1024), 2),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cleanup/{job_id}")
def cleanup_job(job_id: str):
    """Manually cleanup job files"""
    try:
        cleanup_temp_files(job_id, keep_output=False)
        if job_id in job_status:
            del job_status[job_id]
        return {"message": f"Job {job_id} cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def cleanup_temp_files(job_id: str, keep_output: bool = True):
    """
    Cleanup temporary files for a job
    
    Args:
        job_id: Job ID
        keep_output: Whether to keep the output file
    """
    try:
        # Remove input file
        input_file = TEMP_DIR / "uploads" / f"{job_id}_input.mp4"
        if input_file.exists():
            input_file.unlink()
            logger.info(f"🗑️  Cleaned up input file: {input_file}")
        
        # Remove processing files
        processing_dir = TEMP_DIR / "processing"
        for file in processing_dir.glob(f"*{job_id}*"):
            file.unlink()
            logger.info(f"🗑️  Cleaned up processing file: {file}")
        
        # Optionally remove output file
        if not keep_output:
            output_file = TEMP_DIR / "outputs" / f"{job_id}_output.mp4"
            if output_file.exists():
                output_file.unlink()
                logger.info(f"🗑️  Cleaned up output file: {output_file}")
    except Exception as e:
        logger.error(f"Error cleaning up job {job_id}: {e}")

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🚀 AutoCut Python Worker starting...")
    logger.info(f"📁 Temp directory: {TEMP_DIR}")
    logger.info(f"🌐 Server ready on http://0.0.0.0:8000")
    logger.info(f"📖 API docs: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("👋 AutoCut Python Worker shutting down...")

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🚀 AutoCut Python Worker - Production Ready")
    print("=" * 70)
    print(f"📁 Temp directory: {TEMP_DIR}")
    print(f"🌐 Server: http://localhost:8000")
    print(f"📖 API docs: http://localhost:8000/docs")
    print(f"📊 Health check: http://localhost:8000/health")
    print("=" * 70)
    print("\n✨ Features:")
    print("  • Smart jump cuts with smooth transitions")
    print("  • Professional subtitles (3 styles)")
    print("  • Zoom effects on key moments")
    print("  • Color grading (vibrant/cinematic/natural)")
    print("  • Blurred background for better framing")
    print("  • 9:16 aspect ratio for TikTok/Reels")
    print("\n🎬 Ready to process videos!\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
