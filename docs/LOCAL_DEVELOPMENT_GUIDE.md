# 🏠 AutoCut Influencer - Local Development Guide

**เทสทุกอย่างบน Local โดยไม่ต้องจ่ายเงิน!**

---

## 🎯 เป้าหมาย

- ✅ ทดสอบทุกอย่างบน Local (localhost)
- ✅ ไม่ต้องซื้อ Domain
- ✅ ไม่ต้องเช่า Replicate (ใช้ Python Local)
- ✅ ประหยัดค่าใช้จ่าย API (ใช้แค่ Whisper + Gemini)
- ✅ Debug ง่าย เห็นทุก step

---

## 📋 สิ่งที่ต้องติดตั้ง

### 1. Software พื้นฐาน

```bash
# Node.js 18+
node --version  # ต้อง >= 18

# Python 3.10+
python --version  # ต้อง >= 3.10

# FFmpeg (สำคัญมาก!)
ffmpeg -version
```

### ติดตั้ง FFmpeg:

**Windows:**
```bash
# ใช้ Chocolatey
choco install ffmpeg

# หรือ download จาก https://ffmpeg.org/download.html
# แล้ว add to PATH
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

---

## 🚀 Setup โปรเจค Local

### Step 1: สร้างโปรเจค Next.js

```bash
cd d:\autocut

# สร้าง Next.js project
npx create-next-app@latest . --typescript --tailwind --app

# ติดตั้ง dependencies
npm install @supabase/supabase-js @supabase/ssr
npm install openai @google/generative-ai
npm install react-dropzone
```

### Step 2: สร้าง Python Environment

```bash
# สร้าง virtual environment
cd d:\autocut
python -m venv venv

# Activate
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# ติดตั้ง packages
pip install ffmpeg-python pillow openai google-generativeai
```

### Step 3: Environment Variables

สร้างไฟล์ `.env.local`:

```bash
# Supabase (Free tier)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI (Whisper) - ใช้จริง แต่ถูก
OPENAI_API_KEY=sk-...

# Google AI (Gemini) - ฟรี!
GOOGLE_AI_API_KEY=your-gemini-key

# Local URLs
NEXT_PUBLIC_APP_URL=http://localhost:3000
PYTHON_WORKER_URL=http://localhost:8000
```

---

## 🏗️ สถาปัตยกรรม Local

```
┌─────────────────────────────────────────────────────────┐
│  Next.js (localhost:3000)                               │
│  ├─ Frontend (Upload, Dashboard)                        │
│  └─ API Routes (/api/jobs/*, /api/ai/*)                │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─> Supabase (Cloud - Free Tier)
               │   ├─ Database
               │   └─ Storage
               │
               ├─> Whisper API (Cloud - Pay per use)
               │
               ├─> Gemini API (Cloud - FREE!)
               │
               └─> Python Worker (localhost:8000) ⭐ LOCAL!
                   └─ FFmpeg processing
```

---

## 📁 โครงสร้างโปรเจค Local

```
d:\autocut\
├── src/                    # Next.js app
│   ├── app/
│   ├── components/
│   └── lib/
├── python-worker/          # Python local worker
│   ├── main.py
│   ├── video_processor.py
│   └── requirements.txt
├── temp/                   # ไฟล์ชั่วคราว
│   ├── uploads/
│   ├── processing/
│   └── outputs/
└── .env.local
```

---

## 🐍 Python Local Worker

### 1. สร้างโครงสร้าง

```bash
mkdir python-worker
cd python-worker
```

### 2. `requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
ffmpeg-python==0.2.0
Pillow==10.0.0
python-multipart==0.0.6
```

ติดตั้ง:
```bash
pip install -r requirements.txt
```

### 3. `main.py` - FastAPI Server

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from video_processor import VideoProcessor

app = FastAPI()

# Enable CORS สำหรับ Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "../temp"
os.makedirs(f"{TEMP_DIR}/uploads", exist_ok=True)
os.makedirs(f"{TEMP_DIR}/processing", exist_ok=True)
os.makedirs(f"{TEMP_DIR}/outputs", exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "Python Worker is running!"}

@app.post("/process")
async def process_video(
    video: UploadFile = File(...),
    editing_script: str = File(...)
):
    """
    รับวิดีโอและ editing script แล้วประมวลผล
    """
    try:
        # Parse editing script
        script = json.loads(editing_script)
        
        # บันทึกวิดีโอที่อัปโหลด
        job_id = script.get('job_id', 'test')
        input_path = f"{TEMP_DIR}/uploads/{job_id}_input.mp4"
        
        with open(input_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # ประมวลผลวิดีโอ
        output_path = f"{TEMP_DIR}/outputs/{job_id}_output.mp4"
        processor = VideoProcessor(input_path, output_path)
        
        # Step 1: Apply jump cuts
        if script.get('jumpCuts'):
            print(f"Applying {len(script['jumpCuts'])} jump cuts...")
            input_path = processor.apply_jump_cuts(script['jumpCuts'])
        
        # Step 2: Add subtitles
        if script.get('subtitles'):
            print(f"Adding {len(script['subtitles'])} subtitles...")
            input_path = processor.add_subtitles(script['subtitles'], input_path)
        
        # Step 3: Change aspect ratio
        print("Converting to 9:16...")
        final_path = processor.change_aspect_ratio(input_path, '9:16')
        
        # ส่งไฟล์กลับ
        return FileResponse(
            final_path,
            media_type="video/mp4",
            filename=f"{job_id}_output.mp4"
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "ffmpeg": check_ffmpeg()}

def check_ffmpeg():
    """ตรวจสอบว่ามี FFmpeg หรือไม่"""
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "installed"
    except:
        return "not found"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4. `video_processor.py`

```python
import ffmpeg
import os
from typing import List, Dict

class VideoProcessor:
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.temp_dir = os.path.dirname(output_path)
    
    def apply_jump_cuts(self, jump_cuts: List[Dict]) -> str:
        """ตัดช่วงเงียบออก"""
        if not jump_cuts:
            return self.input_path
        
        print(f"Processing {len(jump_cuts)} jump cuts...")
        
        # สร้าง list ของช่วงเวลาที่เก็บ
        segments = []
        current_time = 0.0
        
        for cut in sorted(jump_cuts, key=lambda x: x['start']):
            # เก็บช่วงก่อน jump cut
            if current_time < cut['start']:
                segments.append((current_time, cut['start']))
            current_time = cut['end']
        
        # เก็บช่วงสุดท้าย
        probe = ffmpeg.probe(self.input_path)
        duration = float(probe['format']['duration'])
        if current_time < duration:
            segments.append((current_time, duration))
        
        # ตัดและต่อวิดีโอ
        temp_files = []
        for i, (start, end) in enumerate(segments):
            temp_file = f"{self.temp_dir}/segment_{i}.mp4"
            (
                ffmpeg
                .input(self.input_path, ss=start, t=end-start)
                .output(temp_file, c='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            temp_files.append(temp_file)
        
        # ต่อทุก segment เข้าด้วยกัน
        output_file = f"{self.temp_dir}/cut_output.mp4"
        
        # สร้าง concat file
        concat_file = f"{self.temp_dir}/concat.txt"
        with open(concat_file, 'w') as f:
            for temp_file in temp_files:
                f.write(f"file '{os.path.abspath(temp_file)}'\n")
        
        (
            ffmpeg
            .input(concat_file, format='concat', safe=0)
            .output(output_file, c='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        
        # ลบไฟล์ชั่วคราว
        for temp_file in temp_files:
            os.remove(temp_file)
        os.remove(concat_file)
        
        return output_file
    
    def add_subtitles(self, subtitles: List[Dict], video_path: str) -> str:
        """ใส่ซับไตเติ้ล"""
        if not subtitles:
            return video_path
        
        print(f"Adding {len(subtitles)} subtitles...")
        
        # สร้างไฟล์ SRT
        srt_path = f"{self.temp_dir}/subtitles.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_srt_time(sub['start'])} --> {self._format_srt_time(sub['end'])}\n")
                f.write(f"{sub['text']}\n\n")
        
        output_file = f"{self.temp_dir}/subtitled_output.mp4"
        
        # ใส่ซับด้วย FFmpeg
        (
            ffmpeg
            .input(video_path)
            .output(
                output_file,
                vf=f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Bold=1,Alignment=2'"
            )
            .overwrite_output()
            .run(quiet=True)
        )
        
        return output_file
    
    def change_aspect_ratio(self, video_path: str, ratio: str = '9:16') -> str:
        """เปลี่ยนอัตราส่วนเป็น 9:16"""
        print(f"Converting to {ratio}...")
        
        width, height = 1080, 1920  # 9:16 for TikTok/Reels
        
        (
            ffmpeg
            .input(video_path)
            .output(
                self.output_path,
                vf=f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                video_bitrate='5M',
                audio_bitrate='192k',
                preset='medium'
            )
            .overwrite_output()
            .run(quiet=True)
        )
        
        return self.output_path
    
    def _format_srt_time(self, seconds: float) -> str:
        """แปลงวินาทีเป็น SRT time format (00:00:00,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

### 5. รัน Python Worker

```bash
cd python-worker
python main.py

# จะเห็น:
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

ทดสอบ:
```bash
# เปิด browser ไปที่
http://localhost:8000

# ควรเห็น: {"status": "Python Worker is running!"}
```

---

## 🔧 Next.js API Routes (Local Version)

### 1. `src/app/api/jobs/process-local/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { transcribeVideo } from '@/lib/ai/whisper'
import { analyzeTranscript } from '@/lib/ai/gemini'
import FormData from 'form-data'
import fetch from 'node-fetch'

export async function POST(request: NextRequest) {
  try {
    const { jobId } = await request.json()
    const supabase = createServiceClient()

    // 1. ดึงข้อมูล job
    const { data: job } = await supabase
      .from('jobs')
      .select('*')
      .eq('id', jobId)
      .single()

    if (!job) {
      return NextResponse.json({ error: 'Job not found' }, { status: 404 })
    }

    // 2. Download วิดีโอจาก Supabase
    const { data: videoBlob } = await supabase.storage
      .from('raw-videos')
      .download(job.input_video_path)

    if (!videoBlob) {
      throw new Error('Failed to download video')
    }

    // 3. บันทึกเป็นไฟล์ชั่วคราว
    const tempVideoPath = `./temp/uploads/${jobId}_input.mp4`
    const arrayBuffer = await videoBlob.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)
    await fs.promises.writeFile(tempVideoPath, buffer)

    // 4. STEP 1: Transcribe
    await supabase
      .from('jobs')
      .update({ 
        status: 'TRANSCRIBING', 
        current_step: 'กำลังถอดเสียง...',
        progress_percentage: 10 
      })
      .eq('id', jobId)

    const transcription = await transcribeVideo(tempVideoPath)

    await supabase
      .from('jobs')
      .update({
        transcription_json: transcription,
        progress_percentage: 33,
      })
      .eq('id', jobId)

    // 5. STEP 2: Analyze
    await supabase
      .from('jobs')
      .update({ 
        status: 'ANALYZING', 
        current_step: 'กำลังวิเคราะห์...',
        progress_percentage: 40 
      })
      .eq('id', jobId)

    const editingScript = await analyzeTranscript(
      transcription.text,
      transcription.segments
    )

    await supabase
      .from('jobs')
      .update({
        analysis_json: editingScript,
        progress_percentage: 66,
      })
      .eq('id', jobId)

    // 6. STEP 3: Render (ส่งไป Python Worker LOCAL!)
    await supabase
      .from('jobs')
      .update({ 
        status: 'RENDERING', 
        current_step: 'กำลังตัดต่อวิดีโอ...',
        progress_percentage: 70 
      })
      .eq('id', jobId)

    // สร้าง FormData สำหรับส่งไป Python
    const formData = new FormData()
    formData.append('video', buffer, `${jobId}_input.mp4`)
    formData.append('editing_script', JSON.stringify({
      job_id: jobId,
      jumpCuts: editingScript.jumpCuts,
      subtitles: transcription.segments.map(seg => ({
        start: seg.start,
        end: seg.end,
        text: seg.text
      }))
    }))

    // เรียก Python Worker
    const pythonResponse = await fetch('http://localhost:8000/process', {
      method: 'POST',
      body: formData,
    })

    if (!pythonResponse.ok) {
      throw new Error('Python worker failed')
    }

    // 7. รับวิดีโอที่ตัดต่อเสร็จ
    const processedVideo = await pythonResponse.buffer()

    // 8. Upload กลับ Supabase
    const finalPath = `final-videos/${job.user_id}/${jobId}/output.mp4`
    await supabase.storage
      .from('final-videos')
      .upload(finalPath, processedVideo, {
        contentType: 'video/mp4',
        upsert: true
      })

    // 9. อัปเดต job เป็น COMPLETED
    await supabase
      .from('jobs')
      .update({
        status: 'COMPLETED',
        output_video_path: finalPath,
        progress_percentage: 100,
        completed_at: new Date().toISOString(),
      })
      .eq('id', jobId)

    return NextResponse.json({ 
      success: true, 
      jobId,
      outputPath: finalPath 
    })

  } catch (error) {
    console.error('Process job error:', error)
    
    // อัปเดต job เป็น FAILED
    const { jobId } = await request.json()
    if (jobId) {
      const supabase = createServiceClient()
      await supabase
        .from('jobs')
        .update({
          status: 'FAILED',
          error_message: error.message,
        })
        .eq('id', jobId)
    }

    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    )
  }
}
```

---

## 🎬 วิธีใช้งาน Local

### 1. เริ่ม Services ทั้งหมด

**Terminal 1 - Python Worker:**
```bash
cd d:\autocut\python-worker
python main.py
```

**Terminal 2 - Next.js:**
```bash
cd d:\autocut
npm run dev
```

### 2. ทดสอบ

1. เปิด browser: `http://localhost:3000`
2. อัปโหลดวิดีโอ (ควรเป็นวิดีโอสั้นๆ 30 วินาที สำหรับทดสอบ)
3. ดู progress แบบ real-time
4. ดาวน์โหลดวิดีโอที่ตัดต่อเสร็จ

### 3. Debug

**ดู logs:**
- Python Worker: ดูใน Terminal 1
- Next.js API: ดูใน Terminal 2
- Supabase: ดูใน Supabase Dashboard

**ดูไฟล์ชั่วคราว:**
```
d:\autocut\temp\
├── uploads\      # วิดีโอที่อัปโหลด
├── processing\   # ไฟล์ระหว่างประมวลผล
└── outputs\      # วิดีโอที่ตัดต่อเสร็จ
```

---

## 💰 ค่าใช้จ่าย Local Development

| Service | ค่าใช้จ่าย | หมายเหตุ |
|---------|-----------|----------|
| **Supabase** | ฟรี | Free tier: 500MB database, 1GB storage |
| **Whisper API** | ~$0.006/นาที | วิดีโอ 1 นาที = 6 สตางค์ |
| **Gemini API** | ฟรี! | 60 requests/minute ฟรี |
| **Python Worker** | ฟรี | รันบน Local |
| **FFmpeg** | ฟรี | Open source |

**ประมาณการ:**
- ทดสอบ 10 วิดีโอ (1 นาที/วิดีโอ) = ~60 สตางค์
- ทดสอบ 100 วิดีโอ = ~6 บาท

---

## 🐛 Troubleshooting

### ปัญหา: FFmpeg not found

```bash
# Windows
where ffmpeg

# Mac/Linux
which ffmpeg

# ถ้าไม่เจอ ให้ติดตั้งใหม่และ restart terminal
```

### ปัญหา: Python Worker ไม่ทำงาน

```bash
# ตรวจสอบ port 8000 ว่าว่างไหม
# Windows:
netstat -ano | findstr :8000

# Mac/Linux:
lsof -i :8000

# ถ้ามีโปรแกรมอื่นใช้ ให้เปลี่ยน port ใน main.py
```

### ปัญหา: วิดีโอตัดต่อไม่ออก

```bash
# ทดสอบ FFmpeg ด้วยตัวเอง
ffmpeg -i input.mp4 -vf "scale=1080:1920" output.mp4

# ถ้าได้ แสดงว่า FFmpeg ใช้งานได้
# ปัญหาอาจอยู่ที่โค้ด Python
```

---

## ✅ Checklist ก่อนเริ่มทดสอบ

- [ ] ติดตั้ง Node.js 18+
- [ ] ติดตั้ง Python 3.10+
- [ ] ติดตั้ง FFmpeg
- [ ] สร้าง Supabase project (Free tier)
- [ ] ได้ OpenAI API key
- [ ] ได้ Gemini API key (ฟรี)
- [ ] รัน `npm install` สำเร็จ
- [ ] รัน `pip install -r requirements.txt` สำเร็จ
- [ ] Python Worker รันได้ (port 8000)
- [ ] Next.js รันได้ (port 3000)

---

## 🚀 เมื่อพร้อม Deploy จริง

เมื่อทดสอบบน Local เรียบร้อยแล้ว ค่อยไป:

1. **Deploy Next.js** → Vercel (ฟรี)
2. **Deploy Python Worker** → Replicate (pay-as-you-go)
3. **ซื้อ Domain** → Namecheap (~300 บาท/ปี)
4. **Setup Webhook** → ใช้ domain จริง

แต่ตอนนี้ยังไม่ต้องรีบ! ทดสอบบน Local ให้เรียบร้อยก่อน 😊

---

มีคำถามเพิ่มเติมไหมครับ? พร้อมช่วยเสมอ!
