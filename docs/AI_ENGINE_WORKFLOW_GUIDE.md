# 🎬 AutoCut Influencer - AI Engine Workflow Development Guide

**สำหรับ Fullstack Developer ที่ยังไม่เคยจับงาน AI/Video Processing**

---

## 📋 Table of Contents

1. [ภาพรวมระบบ AI Engine](#ภาพรวมระบบ-ai-engine)
2. [สถาปัตยกรรมทั้งหมด](#สถาปัตยกรรมทั้งหมด)
3. [ขั้นตอนการพัฒนาทีละขั้น](#ขั้นตอนการพัฒนาทีละขั้น)
4. [โค้ดตัวอย่างทุกส่วน](#โค้ดตัวอย่างทุกส่วน)
5. [การ Deploy และ Testing](#การ-deploy-และ-testing)

---

## 🎯 ภาพรวมระบบ AI Engine

### Workflow ทั้งหมด (4 ขั้นตอนหลัก)

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS VIDEO                            │
│                    (Next.js Frontend)                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: TRANSCRIBE (ฟังเสียง)                                  │
│  ────────────────────────────────                                │
│  • Whisper API ถอดเสียงเป็นข้อความ                              │
│  • ได้ Transcript + Timestamp ของทุกคำ                          │
│  • เก็บใน jobs.transcription_json                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: ANALYZE (คิดวิเคราะห์)                                 │
│  ────────────────────────────────                                │
│  • Gemini API วิเคราะห์ Transcript                              │
│  • หาจุดเงียบที่ต้อง Jump Cut                                   │
│  • หาคำสำคัญสำหรับ Sound FX                                     │
│  • สร้าง "Editing Script" (JSON)                                │
│  • เก็บใน jobs.analysis_json                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: RENDER (ตัดต่อจริง)                                    │
│  ────────────────────────────────                                │
│  • Python Worker บน Replicate                                   │
│  • ใช้ FFmpeg ตัดต่อตาม Editing Script                          │
│  • ใส่ Subtitle แบบ Burn-in                                     │
│  • ปรับอัตราส่วน 9:16                                           │
│  • Export เป็น MP4                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: FINALIZE (เสร็จสิ้น)                                   │
│  ────────────────────────────────────                            │
│  • อัปโหลดวิดีโอกลับ Supabase Storage                           │
│  • Webhook แจ้ง Next.js API                                     │
│  • อัปเดต job status = COMPLETED                                │
│  • ส่งอีเมลแจ้งผู้ใช้                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ สถาปัตยกรรมทั้งหมด

### ส่วนประกอบหลัก 5 ส่วน

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                  │
│                    (Next.js 16 App Router)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Upload     │  │  Dashboard   │  │   Progress   │           │
│  │  Component   │  │     Page     │  │   Tracker    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      NEXT.JS API ROUTES                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ POST /api/   │  │ GET /api/    │  │ POST /api/   │           │
│  │ jobs/create  │  │ jobs/[id]    │  │ webhooks/    │           │
│  │              │  │              │  │ replicate    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│                         SUPABASE                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │   Storage    │  │     Auth     │           │
│  │  (Database)  │  │  (Videos)    │  │   (Users)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      EXTERNAL AI SERVICES                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Whisper    │  │    Gemini    │  │  Replicate   │           │
│  │     API      │  │  Flash API   │  │  (Python)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 ขั้นตอนการพัฒนาทีละขั้น

---

## PHASE 1: Setup โปรเจค Next.js 16

### 1.1 สร้างโปรเจค

```bash
# สร้างโปรเจค Next.js 16
npx create-next-app@latest autocut-influencer

# เลือก options:
# ✅ TypeScript: Yes
# ✅ ESLint: Yes
# ✅ Tailwind CSS: Yes
# ✅ src/ directory: Yes
# ✅ App Router: Yes
# ✅ Turbopack: Yes (faster)
# ❌ Import alias: No (ใช้ default)

cd autocut-influencer
```

### 1.2 ติดตั้ง Dependencies

```bash
# Supabase Client
npm install @supabase/supabase-js @supabase/ssr

# AI APIs
npm install openai @google/generative-ai replicate

# Video processing utilities
npm install ffmpeg-static fluent-ffmpeg

# UI Components (optional)
npm install @radix-ui/react-dialog @radix-ui/react-progress
npm install lucide-react class-variance-authority clsx tailwind-merge

# Form handling
npm install react-hook-form zod @hookform/resolvers

# Date utilities
npm install date-fns
```

### 1.3 โครงสร้างโปรเจค

```
autocut-influencer/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── signup/
│   │   │       └── page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   ├── jobs/
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   └── upload/
│   │   │       └── page.tsx
│   │   ├── api/
│   │   │   ├── jobs/
│   │   │   │   ├── create/
│   │   │   │   │   └── route.ts
│   │   │   │   └── [id]/
│   │   │   │       └── route.ts
│   │   │   ├── webhooks/
│   │   │   │   └── replicate/
│   │   │   │       └── route.ts
│   │   │   └── ai/
│   │   │       ├── transcribe/
│   │   │       │   └── route.ts
│   │   │       └── analyze/
│   │   │           └── route.ts
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── upload/
│   │   │   └── VideoUploader.tsx
│   │   ├── jobs/
│   │   │   ├── JobCard.tsx
│   │   │   └── JobProgress.tsx
│   │   └── ui/
│   │       └── ... (shadcn components)
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts
│   │   │   ├── server.ts
│   │   │   └── middleware.ts
│   │   ├── ai/
│   │   │   ├── whisper.ts
│   │   │   ├── gemini.ts
│   │   │   └── replicate.ts
│   │   └── utils.ts
│   └── types/
│       ├── database.types.ts
│       └── ai.types.ts
├── python-worker/
│   ├── main.py
│   ├── video_processor.py
│   ├── subtitle_generator.py
│   └── requirements.txt
├── .env.local
└── package.json
```

### 1.4 Environment Variables

สร้างไฟล์ `.env.local`:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI (Whisper)
OPENAI_API_KEY=sk-...

# Google AI (Gemini)
GOOGLE_AI_API_KEY=your-gemini-key

# Replicate
REPLICATE_API_TOKEN=r8_...

# App URL (for webhooks)
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## PHASE 2: Setup Supabase Client

### 2.1 Supabase Client (Browser)

สร้างไฟล์ `src/lib/supabase/client.ts`:

```typescript
import { createBrowserClient } from '@supabase/ssr'
import { Database } from '@/types/database.types'

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

### 2.2 Supabase Server Client

สร้างไฟล์ `src/lib/supabase/server.ts`:

```typescript
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { Database } from '@/types/database.types'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options })
          } catch (error) {
            // Handle error
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: '', ...options })
          } catch (error) {
            // Handle error
          }
        },
      },
    }
  )
}

// Service role client (for admin operations)
export function createServiceClient() {
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      cookies: {},
    }
  )
}
```

### 2.3 Generate TypeScript Types

```bash
# ติดตั้ง Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref your-project-ref

# Generate types
npx supabase gen types typescript --linked > src/types/database.types.ts
```

---

## PHASE 3: สร้างระบบ Upload วิดีโอ

### 3.1 Video Uploader Component

สร้างไฟล์ `src/components/upload/VideoUploader.tsx`:

```typescript
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

export function VideoUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const router = useRouter()
  const supabase = createClient()

  const handleUpload = async () => {
    if (!file) return

    try {
      setUploading(true)

      // 1. สร้าง job ใน database ก่อน
      const { data: job, error: jobError } = await supabase
        .from('jobs')
        .insert({
          job_name: file.name,
          status: 'UPLOADING',
          input_file_size_mb: file.size / (1024 * 1024),
        })
        .select()
        .single()

      if (jobError) throw jobError

      // 2. Upload วิดีโอไป Supabase Storage
      const { data: user } = await supabase.auth.getUser()
      const filePath = `raw-videos/${user.user?.id}/${job.id}/${file.name}`

      const { error: uploadError } = await supabase.storage
        .from('raw-videos')
        .upload(filePath, file, {
          onUploadProgress: (progress) => {
            const percent = (progress.loaded / progress.total) * 100
            setProgress(percent)
          },
        })

      if (uploadError) throw uploadError

      // 3. อัปเดต job ด้วย file path
      await supabase
        .from('jobs')
        .update({
          input_video_path: filePath,
          status: 'PENDING',
        })
        .eq('id', job.id)

      // 4. เรียก API เพื่อเริ่ม processing
      await fetch('/api/jobs/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobId: job.id }),
      })

      // 5. Redirect ไปหน้า job detail
      router.push(`/jobs/${job.id}`)
    } catch (error) {
      console.error('Upload error:', error)
      alert('เกิดข้อผิดพลาดในการอัปโหลด')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto p-6 border rounded-lg">
      <h2 className="text-2xl font-bold mb-4">อัปโหลดวิดีโอ</h2>
      
      <input
        type="file"
        accept="video/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="mb-4"
        disabled={uploading}
      />

      {file && (
        <div className="mb-4">
          <p>ไฟล์: {file.name}</p>
          <p>ขนาด: {(file.size / (1024 * 1024)).toFixed(2)} MB</p>
        </div>
      )}

      {uploading && (
        <div className="mb-4">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 mt-2">
            กำลังอัปโหลด... {progress.toFixed(0)}%
          </p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg disabled:opacity-50"
      >
        {uploading ? 'กำลังอัปโหลด...' : 'เริ่มตัดต่อ'}
      </button>
    </div>
  )
}
```

---

## PHASE 4: AI Processing Pipeline

### 4.1 STEP 1: Transcription (Whisper API)

สร้างไฟล์ `src/lib/ai/whisper.ts`:

```typescript
import OpenAI from 'openai'
import { createReadStream } from 'fs'

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
})

export interface TranscriptionSegment {
  id: number
  start: number // seconds
  end: number
  text: string
}

export interface TranscriptionResult {
  text: string // Full transcript
  segments: TranscriptionSegment[]
  language: string
  duration: number
}

export async function transcribeVideo(
  videoPath: string
): Promise<TranscriptionResult> {
  try {
    // Whisper API รับได้แค่ไฟล์ไม่เกิน 25MB
    // ถ้าใหญ่กว่าต้องแยกเป็นชิ้นเล็กก่อน
    
    const transcription = await openai.audio.transcriptions.create({
      file: createReadStream(videoPath),
      model: 'whisper-1',
      response_format: 'verbose_json', // ได้ timestamp ด้วย
      language: 'th', // ภาษาไทย (หรือ auto-detect)
    })

    return {
      text: transcription.text,
      segments: transcription.segments || [],
      language: transcription.language || 'th',
      duration: transcription.duration || 0,
    }
  } catch (error) {
    console.error('Whisper API error:', error)
    throw new Error('Failed to transcribe video')
  }
}
```

### 4.2 STEP 2: Analysis (Gemini API)

สร้างไฟล์ `src/lib/ai/gemini.ts`:

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai'

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY!)

export interface JumpCut {
  start: number // timestamp เริ่มต้น (วินาที)
  end: number   // timestamp สิ้นสุด (วินาที)
  reason: string // เหตุผลที่ตัด (เช่น "ช่วงเงียบ 2 วินาที")
}

export interface SoundEffect {
  timestamp: number // เวลาที่ใส่เสียง (วินาที)
  type: string // ประเภทเสียง (เช่น "whoosh", "pop", "ding")
  keyword: string // คำที่ trigger (เช่น "เท่", "เจ๋ง")
}

export interface EditingScript {
  jumpCuts: JumpCut[]
  soundEffects: SoundEffect[]
  highlights: number[] // timestamp ของคำสำคัญที่ควร highlight
  summary: string // สรุปเนื้อหา
}

export async function analyzeTranscript(
  transcript: string,
  segments: any[]
): Promise<EditingScript> {
  try {
    const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' })

    const prompt = `
คุณเป็น AI Video Editor ที่เชี่ยวชาญในการตัดต่อวิดีโอสไตล์ไวรัลสำหรับ TikTok/Reels

ให้วิเคราะห์ transcript นี้และสร้าง Editing Script:

TRANSCRIPT:
${transcript}

SEGMENTS WITH TIMESTAMPS:
${JSON.stringify(segments, null, 2)}

กรุณาวิเคราะห์และส่งคืนเป็น JSON ในรูปแบบนี้:

{
  "jumpCuts": [
    {
      "start": 5.2,
      "end": 7.8,
      "reason": "ช่วงเงียบ 2.6 วินาที"
    }
  ],
  "soundEffects": [
    {
      "timestamp": 10.5,
      "type": "whoosh",
      "keyword": "เร็วมาก"
    }
  ],
  "highlights": [15.2, 23.5, 45.1],
  "summary": "สรุปเนื้อหาวิดีโอ"
}

เกณฑ์การตัดต่อ:
1. Jump Cut: ตัดช่วงเงียบที่เกิน 1.5 วินาที
2. Sound FX: ใส่เสียงเมื่อมีคำแสดงอารมณ์ (เช่น "เจ๋ง", "เท่", "สุดยอด")
3. Highlights: เน้นคำสำคัญที่น่าสนใจ

ส่งคืนเฉพาะ JSON เท่านั้น ไม่ต้องมีคำอธิบายเพิ่มเติม
`

    const result = await model.generateContent(prompt)
    const response = result.response.text()
    
    // Parse JSON จาก response
    const jsonMatch = response.match(/\{[\s\S]*\}/)
    if (!jsonMatch) {
      throw new Error('Invalid JSON response from Gemini')
    }

    const editingScript: EditingScript = JSON.parse(jsonMatch[0])
    return editingScript
  } catch (error) {
    console.error('Gemini API error:', error)
    throw new Error('Failed to analyze transcript')
  }
}
```

### 4.3 API Route: Process Job

สร้างไฟล์ `src/app/api/jobs/process/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { transcribeVideo } from '@/lib/ai/whisper'
import { analyzeTranscript } from '@/lib/ai/gemini'
import Replicate from 'replicate'

const replicate = new Replicate({
  auth: process.env.REPLICATE_API_TOKEN!,
})

export async function POST(request: NextRequest) {
  try {
    const { jobId } = await request.json()
    const supabase = createServiceClient()

    // 1. ดึงข้อมูล job
    const { data: job, error } = await supabase
      .from('jobs')
      .select('*')
      .eq('id', jobId)
      .single()

    if (error || !job) {
      return NextResponse.json({ error: 'Job not found' }, { status: 404 })
    }

    // 2. Download วิดีโอจาก Supabase Storage
    const { data: videoData } = await supabase.storage
      .from('raw-videos')
      .download(job.input_video_path)

    if (!videoData) {
      throw new Error('Failed to download video')
    }

    // บันทึกเป็นไฟล์ชั่วคราว
    const tempVideoPath = `/tmp/${jobId}.mp4`
    // ... save videoData to tempVideoPath

    // 3. STEP 1: Transcribe
    await supabase
      .from('jobs')
      .update({ status: 'TRANSCRIBING', current_step: 'กำลังถอดเสียง...' })
      .eq('id', jobId)

    const transcription = await transcribeVideo(tempVideoPath)

    await supabase
      .from('jobs')
      .update({
        transcription_json: transcription,
        progress_percentage: 33,
      })
      .eq('id', jobId)

    // 4. STEP 2: Analyze
    await supabase
      .from('jobs')
      .update({ status: 'ANALYZING', current_step: 'กำลังวิเคราะห์...' })
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

    // 5. STEP 3: Render (ส่งไป Replicate)
    await supabase
      .from('jobs')
      .update({ status: 'RENDERING', current_step: 'กำลังตัดต่อวิดีโอ...' })
      .eq('id', jobId)

    const prediction = await replicate.predictions.create({
      version: 'your-model-version-id',
      input: {
        video_url: job.input_video_path,
        editing_script: editingScript,
        aspect_ratio: '9:16',
      },
      webhook: `${process.env.NEXT_PUBLIC_APP_URL}/api/webhooks/replicate`,
      webhook_events_filter: ['completed'],
    })

    await supabase
      .from('jobs')
      .update({
        replicate_prediction_id: prediction.id,
      })
      .eq('id', jobId)

    return NextResponse.json({ success: true, jobId, predictionId: prediction.id })
  } catch (error) {
    console.error('Process job error:', error)
    return NextResponse.json(
      { error: 'Failed to process job' },
      { status: 500 }
    )
  }
}
```

---

## PHASE 5: Python Worker (Replicate)

### 5.1 โครงสร้าง Python Worker

สร้างโฟลเดอร์ `python-worker/`:

```
python-worker/
├── main.py                 # Entry point
├── video_processor.py      # FFmpeg processing
├── subtitle_generator.py   # Subtitle rendering
├── requirements.txt        # Dependencies
├── cog.yaml               # Replicate config
└── predict.py             # Replicate prediction handler
```

### 5.2 requirements.txt

```txt
ffmpeg-python==0.2.0
Pillow==10.0.0
numpy==1.24.3
```

### 5.3 video_processor.py

```python
import ffmpeg
import json
from typing import List, Dict

class VideoProcessor:
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
    
    def apply_jump_cuts(self, jump_cuts: List[Dict]) -> str:
        """
        ตัดช่วงเงียบออกจากวิดีโอ
        """
        # สร้าง filter complex สำหรับ FFmpeg
        segments = []
        current_time = 0
        
        for i, cut in enumerate(sorted(jump_cuts, key=lambda x: x['start'])):
            # เก็บส่วนก่อนหน้า jump cut
            if current_time < cut['start']:
                segments.append(f"between(t,{current_time},{cut['start']})")
            current_time = cut['end']
        
        # เก็บส่วนสุดท้าย
        segments.append(f"gte(t,{current_time})")
        
        # สร้าง filter
        select_filter = '+'.join(segments)
        
        temp_output = self.output_path.replace('.mp4', '_cut.mp4')
        
        (
            ffmpeg
            .input(self.input_path)
            .output(
                temp_output,
                vf=f"select='{select_filter}',setpts=N/FRAME_RATE/TB",
                af=f"aselect='{select_filter}',asetpts=N/SR/TB"
            )
            .overwrite_output()
            .run()
        )
        
        return temp_output
    
    def add_subtitles(self, subtitles: List[Dict], video_path: str) -> str:
        """
        ใส่ซับไตเติ้ลแบบ burn-in
        """
        # สร้างไฟล์ SRT
        srt_path = video_path.replace('.mp4', '.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_time(sub['start'])} --> {self._format_time(sub['end'])}\n")
                f.write(f"{sub['text']}\n\n")
        
        temp_output = video_path.replace('.mp4', '_subtitled.mp4')
        
        (
            ffmpeg
            .input(video_path)
            .output(
                temp_output,
                vf=f"subtitles={srt_path}:force_style='FontName=Kanit,FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2'"
            )
            .overwrite_output()
            .run()
        )
        
        return temp_output
    
    def change_aspect_ratio(self, video_path: str, ratio: str = '9:16') -> str:
        """
        เปลี่ยนอัตราส่วนเป็น 9:16 (TikTok/Reels)
        """
        width, height = 1080, 1920  # 9:16
        
        (
            ffmpeg
            .input(video_path)
            .output(
                self.output_path,
                vf=f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                video_bitrate='5M',
                audio_bitrate='192k'
            )
            .overwrite_output()
            .run()
        )
        
        return self.output_path
    
    def _format_time(self, seconds: float) -> str:
        """แปลงวินาทีเป็น SRT time format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

### 5.4 predict.py (Replicate Handler)

```python
from cog import BasePredictor, Input, Path
import json
from video_processor import VideoProcessor

class Predictor(BasePredictor):
    def predict(
        self,
        video_url: str = Input(description="URL of input video"),
        editing_script: str = Input(description="JSON editing script from Gemini"),
    ) -> Path:
        """
        Process video according to editing script
        """
        # Parse editing script
        script = json.loads(editing_script)
        
        # Download video
        input_path = "/tmp/input.mp4"
        # ... download video from video_url to input_path
        
        output_path = "/tmp/output.mp4"
        processor = VideoProcessor(input_path, output_path)
        
        # Step 1: Apply jump cuts
        cut_video = processor.apply_jump_cuts(script['jumpCuts'])
        
        # Step 2: Add subtitles
        subtitled_video = processor.add_subtitles(script['segments'], cut_video)
        
        # Step 3: Change aspect ratio
        final_video = processor.change_aspect_ratio(subtitled_video, '9:16')
        
        return Path(final_video)
```

---

## PHASE 6: Webhook Handler

### 6.1 Replicate Webhook

สร้างไฟล์ `src/app/api/webhooks/replicate/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json()
    const supabase = createServiceClient()

    // Log webhook
    await supabase.from('webhook_logs').insert({
      provider: 'replicate',
      event_type: payload.status,
      payload: payload,
    })

    // ถ้า prediction สำเร็จ
    if (payload.status === 'succeeded') {
      const outputUrl = payload.output // URL ของวิดีโอที่ตัดต่อเสร็จ

      // หา job จาก prediction_id
      const { data: job } = await supabase
        .from('jobs')
        .select('*')
        .eq('replicate_prediction_id', payload.id)
        .single()

      if (!job) {
        return NextResponse.json({ error: 'Job not found' }, { status: 404 })
      }

      // Download วิดีโอจาก Replicate
      const response = await fetch(outputUrl)
      const videoBlob = await response.blob()

      // Upload ไป Supabase Storage
      const finalPath = `final-videos/${job.user_id}/${job.id}/output.mp4`
      await supabase.storage.from('final-videos').upload(finalPath, videoBlob)

      // อัปเดต job status
      await supabase
        .from('jobs')
        .update({
          status: 'COMPLETED',
          output_video_path: finalPath,
          progress_percentage: 100,
          completed_at: new Date().toISOString(),
        })
        .eq('id', job.id)

      // TODO: ส่งอีเมลแจ้งผู้ใช้
    } else if (payload.status === 'failed') {
      // ถ้า prediction ล้มเหลว
      const { data: job } = await supabase
        .from('jobs')
        .select('*')
        .eq('replicate_prediction_id', payload.id)
        .single()

      if (job) {
        await supabase
          .from('jobs')
          .update({
            status: 'FAILED',
            error_message: payload.error || 'Unknown error',
          })
          .eq('id', job.id)
      }
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Webhook error:', error)
    return NextResponse.json({ error: 'Webhook failed' }, { status: 500 })
  }
}
```

---

## PHASE 7: Frontend - Job Progress Tracker

### 7.1 Job Progress Component

สร้างไฟล์ `src/components/jobs/JobProgress.tsx`:

```typescript
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

interface JobProgressProps {
  jobId: string
}

export function JobProgress({ jobId }: JobProgressProps) {
  const [job, setJob] = useState<any>(null)
  const supabase = createClient()

  useEffect(() => {
    // Fetch initial job data
    fetchJob()

    // Subscribe to realtime updates
    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'jobs',
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          setJob(payload.new)
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [jobId])

  const fetchJob = async () => {
    const { data } = await supabase
      .from('jobs')
      .select('*')
      .eq('id', jobId)
      .single()
    setJob(data)
  }

  if (!job) return <div>Loading...</div>

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">{job.job_name}</h2>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between mb-2">
          <span className="text-sm font-medium">{job.current_step}</span>
          <span className="text-sm font-medium">{job.progress_percentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className="bg-blue-600 h-4 rounded-full transition-all duration-500"
            style={{ width: `${job.progress_percentage}%` }}
          />
        </div>
      </div>

      {/* Status */}
      <div className="mb-6">
        <StatusBadge status={job.status} />
      </div>

      {/* Video Preview */}
      {job.status === 'COMPLETED' && job.output_video_path && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">วิดีโอที่ตัดต่อเสร็จแล้ว</h3>
          <VideoPlayer videoPath={job.output_video_path} />
          <button
            onClick={() => downloadVideo(job.output_video_path)}
            className="mt-4 bg-green-600 text-white py-2 px-4 rounded-lg"
          >
            ดาวน์โหลดวิดีโอ
          </button>
        </div>
      )}

      {/* Error */}
      {job.status === 'FAILED' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">เกิดข้อผิดพลาด: {job.error_message}</p>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    PENDING: 'bg-gray-100 text-gray-800',
    UPLOADING: 'bg-blue-100 text-blue-800',
    QUEUED: 'bg-yellow-100 text-yellow-800',
    TRANSCRIBING: 'bg-purple-100 text-purple-800',
    ANALYZING: 'bg-indigo-100 text-indigo-800',
    RENDERING: 'bg-orange-100 text-orange-800',
    COMPLETED: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status]}`}>
      {status}
    </span>
  )
}
```

---

## 📊 สรุปการทำงานทั้งหมด

```
1. User อัปโหลดวิดีโอ
   └─> VideoUploader.tsx
       └─> Supabase Storage (raw-videos bucket)
       └─> สร้าง job ใน database

2. เริ่ม Processing
   └─> POST /api/jobs/process
       │
       ├─> STEP 1: Whisper API (ถอดเสียง)
       │   └─> เก็บใน jobs.transcription_json
       │
       ├─> STEP 2: Gemini API (วิเคราะห์)
       │   └─> เก็บใน jobs.analysis_json
       │
       └─> STEP 3: Replicate (ตัดต่อ)
           └─> Python Worker
               ├─> FFmpeg: Jump Cuts
               ├─> FFmpeg: Subtitles
               └─> FFmpeg: Aspect Ratio

3. Replicate เสร็จ
   └─> Webhook → POST /api/webhooks/replicate
       └─> Download วิดีโอ
       └─> Upload ไป Supabase Storage (final-videos)
       └─> อัปเดต job.status = COMPLETED

4. User ดูผลลัพธ์
   └─> JobProgress.tsx (Realtime updates)
       └─> ดาวน์โหลดวิดีโอ
```

---

## 🎯 Next Steps

1. **ทดสอบแต่ละส่วน:**
   - Upload → ✅
   - Transcription → ✅
   - Analysis → ✅
   - Rendering → ✅
   - Webhook → ✅

2. **เพิ่มฟีเจอร์:**
   - Credit system
   - Payment integration
   - Email notifications
   - Error handling & retry

3. **Optimize:**
   - Caching
   - Queue management
   - Cost monitoring

---

มีคำถามเพิ่มเติมหรือต้องการให้อธิบายส่วนไหนเพิ่มไหมครับ? 😊
