// AI Service Configuration and Management
// Handles API key validation, fallback logic, and error handling

export interface TranscriptionResult {
    text: string
    segments: Array<{
        start: number
        end: number
        text: string
    }>
}

export interface AnalysisResult {
    summary: string
    highlights: Array<{
        start: number
        end: number
        reason: string
    }>
    jumpCuts: Array<{
        start: number
        end: number
        reason: string
    }>
    keywords?: string[]
    visual_style?: {
        color_grading?: string
        apply_blur?: boolean
        pacing?: string
    }
    subtitle_settings?: {
        position?: string
        highlight_color?: string
    }
}

export class AIServiceManager {
    private googleAIKey: string | undefined
    private openAIKey: string | undefined

    constructor() {
        this.googleAIKey = process.env.GOOGLE_AI_API_KEY
        this.openAIKey = process.env.OPENAI_API_KEY
    }

    // Check which services are available
    getAvailableServices(): string[] {
        const services: string[] = []
        if (this.googleAIKey) services.push('google-ai')
        if (this.openAIKey) services.push('whisper')
        return services
    }

    // Transcribe with automatic fallback
    async transcribe(videoBlob: Blob): Promise<TranscriptionResult> {
        const errors: Array<{ service: string; error: any }> = []

        // Try Google AI first (free tier)
        if (this.googleAIKey) {
            try {
                console.log('🤖 Attempting transcription with Google AI (New SDK)...')
                return await this.transcribeWithGoogleAI(videoBlob)
            } catch (error) {
                console.error('❌ Google AI failed:', error)
                errors.push({ service: 'Google AI', error })
            }
        }

        // Fallback to Whisper
        if (this.openAIKey) {
            try {
                console.log('🎙️ Attempting transcription with Whisper...')
                return await this.transcribeWithWhisper(videoBlob)
            } catch (error) {
                console.error('❌ Whisper failed:', error)
                errors.push({ service: 'Whisper', error })
            }
        }

        // Last resort: Mock service (for development stability)
        console.log('⚠️ All AI services failed, using Mock fallback for stability...')
        return this.mockTranscription()
    }

    // Mock transcription for development
    private mockTranscription(): TranscriptionResult {
        return {
            text: "นี่คือข้อความตัวอย่างสำหรับการทดสอบระบบ เนื่องจาก AI Service ไม่สามารถใช้งานได้ในขณะนี้ ระบบจึงใช้ข้อมูลจำลองเพื่อให้การทำงานดำเนินต่อไปได้",
            segments: [
                { start: 0, end: 3, text: "นี่คือข้อความตัวอย่าง" },
                { start: 3, end: 6, text: "สำหรับการทดสอบระบบ" },
                { start: 6, end: 10, text: "เนื่องจาก AI Service ไม่พร้อมใช้งาน" },
                { start: 10, end: 15, text: "ระบบจึงใช้ข้อมูลจำลองแทน" }
            ]
        }
    }

    // Google AI (Gemini) transcription using new SDK
    private async transcribeWithGoogleAI(
        videoBlob: Blob
    ): Promise<TranscriptionResult> {
        const { GoogleGenAI } = require('@google/genai')
        const ai = new GoogleGenAI({ apiKey: this.googleAIKey })

        // Convert to base64
        const arrayBuffer = await videoBlob.arrayBuffer()
        const base64Video = Buffer.from(arrayBuffer).toString('base64')

        // Check file size (Gemini has limits)
        const sizeMB = videoBlob.size / (1024 * 1024)
        if (sizeMB > 50) {
            throw new Error(`Video too large for Google AI: ${sizeMB.toFixed(2)}MB (max 50MB)`)
        }

        const prompt = `ถอดเสียงจากวิดีโอนี้เป็นภาษาไทย และส่งคืนเป็น JSON ในรูปแบบนี้:

{
  "text": "ข้อความทั้งหมดที่ถอดได้",
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "ประโยคแรก"},
    {"start": 2.5, "end": 5.0, "text": "ประโยคที่สอง"}
  ]
}

กฎ:
- แบ่งประโยคละ 2-5 วินาที
- ถอดเสียงให้ถูกต้องและครบถ้วน
- ส่งคืนเฉพาะ JSON ไม่ต้องมีคำอธิบาย`

        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: [
                {
                    role: 'user',
                    parts: [
                        { text: prompt },
                        {
                            inlineData: {
                                mimeType: 'video/mp4',
                                data: base64Video
                            }
                        }
                    ]
                }
            ]
        })

        const responseText = response.text
        if (!responseText) {
            throw new Error('Empty response from Google AI')
        }

        // Extract JSON from response
        const jsonMatch = responseText.match(/\{[\s\S]*\}/)
        if (!jsonMatch) {
            throw new Error('Invalid JSON response from Google AI')
        }

        // Sanitize JSON before parsing (remove control characters)
        const sanitizedJson = jsonMatch[0]
            .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // Remove control characters
            .replace(/\\n/g, ' ') // Replace literal \n with space
            .replace(/\\r/g, '') // Remove literal \r
            .replace(/\\t/g, ' ') // Replace literal \t with space

        const parsed = JSON.parse(sanitizedJson)

        // Validate response structure
        if (!parsed.text || !Array.isArray(parsed.segments)) {
            throw new Error('Invalid response structure from Google AI')
        }

        console.log(`✅ Google AI transcribed: ${parsed.segments.length} segments`)
        return parsed
    }

    // Whisper API transcription
    private async transcribeWithWhisper(
        videoBlob: Blob
    ): Promise<TranscriptionResult> {
        const formData = new FormData()
        formData.append('file', videoBlob, 'video.mp4')
        formData.append('model', 'whisper-1')
        formData.append('response_format', 'verbose_json')
        formData.append('language', 'th')
        formData.append('timestamp_granularities[]', 'segment')

        const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${this.openAIKey}`,
            },
            body: formData,
        })

        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`Whisper API error (${response.status}): ${errorText}`)
        }

        const result = await response.json()

        // Validate response
        if (!result.text || !Array.isArray(result.segments)) {
            throw new Error('Invalid response structure from Whisper')
        }

        console.log(`✅ Whisper transcribed: ${result.segments.length} segments`)
        return result
    }

    // Analyze transcript with Gemini (optional enhancement)
    async analyzeTranscript(transcript: TranscriptionResult): Promise<AnalysisResult | null> {
        // If using mock transcription, return mock analysis
        if (transcript.text.includes("ข้อมูลจำลอง")) {
            return {
                summary: "นี่คือการวิเคราะห์จำลองสำหรับการทดสอบ",
                highlights: [
                    { start: 0, end: 3, reason: "จุดเริ่มต้นที่น่าสนใจ" }
                ],
                jumpCuts: [],
                keywords: ["ทดสอบ", "จำลอง"]
            }
        }

        if (!this.googleAIKey) {
            console.log('⚠️ No Google AI key, skipping analysis')
            return null
        }

        try {
            const { GoogleGenAI } = require('@google/genai')
            const ai = new GoogleGenAI({ apiKey: this.googleAIKey })

            const prompt = `วิเคราะห์ transcript นี้และแนะนำการตัดต่อแบบมืออาชีพ:

${transcript.text}

ส่งคืนเป็น JSON เท่านั้น:
{
  "summary": "สรุปเนื้อหาและอารมณ์ของวิดีโอ",
  "visual_style": {
    "color_grading": "vibrant", // vibrant, cinematic, natural, black_and_white
    "apply_blur": false, // true only for vertical video with horizontal background
    "pacing": "fast" // fast, medium, slow
  },
  "subtitle_settings": {
    "position": "bottom", // bottom, center, top (center for shorts/reels)
    "highlight_color": "yellow" // yellow, green, cyan
  },
  "highlights": [
    {
      "start": 5.0, 
      "end": 10.0, 
      "reason": "จุดพีคที่ต้องเน้น",
      "effects": {
        "zoom": {
          "intensity": "medium", // subtle, medium, strong
          "easing": "ease-in-out"
        }
      }
    }
  ],
  "jumpCuts": [
    {
      "start": 0.0,
      "end": 1.5,
      "reason": "ช่วงเงียบ/พูดผิด"
    }
  ],
  "keywords": [
    "คำสำคัญ1", "คำสำคัญ2"
  ]
}

เงื่อนไขการตัดสินใจ (Smart Tool Selection):
1. **Visual Style**:
   - **Color Grading**: เลือก 'vibrant' สำหรับ Vlog/Travel, 'cinematic' สำหรับหนังสั้น, 'natural' สำหรับสัมภาษณ์
   - **Blur**: ใช้เฉพาะเมื่อจำเป็นต้องเบลอขอบ หรือพื้นหลังที่ไม่สวยงาม

2. **Subtitles**:
   - **Position**: ถ้าเป็น Vertical Video (Shorts/Reels) ให้เลือก 'center' หรือ 'bottom' ที่สูงขึ้นมาหน่อยเพื่อไม่ให้โดน UI บัง
   - **Highlight**: เลือกสีที่ตัดกับพื้นหลังวิดีโอ (Yellow คือค่ามาตรฐานที่ดีที่สุด)

3. **Highlights & Zoom**:
   - อย่า Zoom พร่ำเพรื่อ! เลือกเฉพาะจุดที่สำคัญจริงๆ
   - Zoom เพื่อเน้นอารมณ์ หรือเปลี่ยนจังหวะ

4. **Jump Cuts**:
   - ตัดช่วงเงียบเกิน 0.5 วินาที และคำฟุ่มเฟือย
`

            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: [
                    {
                        role: 'user',
                        parts: [{ text: prompt }]
                    }
                ]
            })

            const responseText = response.text
            const jsonMatch = responseText?.match(/\{[\s\S]*\}/)

            if (jsonMatch) {
                return JSON.parse(jsonMatch[0])
            }
        } catch (error) {
            console.error('Analysis failed:', error)
        }

        return null
    }
}
