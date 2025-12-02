import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase/server'
import { AIServiceManager } from '@/lib/ai/service-manager'

export async function POST(request: NextRequest) {
    const aiService = new AIServiceManager()

    try {
        const { jobId } = await request.json()

        if (!jobId) {
            return NextResponse.json({ error: 'Job ID is required' }, { status: 400 })
        }

        // Check available AI services
        const availableServices = aiService.getAvailableServices()
        if (availableServices.length === 0) {
            return NextResponse.json(
                { error: 'No AI service configured. Please set GOOGLE_AI_API_KEY or OPENAI_API_KEY' },
                { status: 500 }
            )
        }

        console.log(`🔑 Available AI services: ${availableServices.join(', ')}`)

        const supabase = createServiceClient()

        // Get job details
        const { data: job, error: jobError } = await supabase
            .from('jobs')
            .select('*')
            .eq('id', jobId)
            .single()

        if (jobError || !job) {
            return NextResponse.json({ error: 'Job not found' }, { status: 404 })
        }

        // Download video
        const { data: videoData, error: downloadError } = await supabase.storage
            .from('raw-videos')
            .download(job.input_video_path)

        if (downloadError || !videoData) {
            throw new Error(`Failed to download video: ${downloadError?.message}`)
        }

        console.log(`📥 Downloaded video: ${(videoData.size / (1024 * 1024)).toFixed(2)}MB`)

        // Step 1: Transcribe
        await supabase
            .from('jobs')
            .update({
                status: 'TRANSCRIBING',
                current_step: 'กำลังถอดเสียง...',
                progress_percentage: 10,
            })
            .eq('id', jobId)

        const transcription = await aiService.transcribe(videoData)

        await supabase
            .from('jobs')
            .update({
                transcription_json: transcription,
                progress_percentage: 30,
                current_step: 'วิเคราะห์เนื้อหา...',
            })
            .eq('id', jobId)

        // Step 2: Analyze (optional)
        const analysis = await aiService.analyzeTranscript(transcription)
        if (analysis) {
            await supabase
                .from('jobs')
                .update({
                    analysis_json: analysis,
                })
                .eq('id', jobId)
        }

        // Step 3: Process video
        await supabase
            .from('jobs')
            .update({
                status: 'RENDERING',
                current_step: 'กำลังตัดต่อวิดีโอ...',
                progress_percentage: 50,
            })
            .eq('id', jobId)

        const formData = new FormData()
        formData.append('video', videoData, `${jobId}_input.mp4`)
        formData.append(
            'editing_script',
            JSON.stringify({
                job_id: jobId,

                // Metadata (AI content understanding)
                metadata: {
                    contentType: 'vlog',  // AI can detect this
                    topic: analysis?.summary || '',
                    mood: 'casual',
                    pacing: 'medium',
                    targetAudience: 'general'
                },

                // Timeline operations
                timeline: {
                    cuts: (analysis?.jumpCuts || []).map(cut => ({
                        start: cut.start,
                        end: cut.end,
                        reason: cut.reason || 'AI detected',
                        type: 'silence'
                    })),
                    highlights: (analysis?.highlights || []).map(h => ({
                        start: h.start,
                        end: h.end,
                        reason: h.reason || 'Key moment',
                        effects: {
                            zoom: {
                                intensity: 'medium',
                                easing: 'ease-in-out',
                                duration: 1.0
                            }
                        }
                    })),
                    transitions: []
                },

                // Audio processing
                audio: {
                    normalization: {
                        enabled: true,
                        targetLoudness: -16  // LUFS for social media
                    },
                    segments: [],
                    backgroundMusic: null
                },

                // Visual processing
                visual: {
                    colorGrading: {
                        preset: analysis?.visual_style?.color_grading || 'vibrant'
                    },
                    aspectRatio: {
                        target: '9:16',
                        strategy: analysis?.visual_style?.apply_blur ? 'blur_background' : 'center_crop'
                    }
                },

                // Subtitles
                subtitles: {
                    segments: transcription.segments.map((seg) => ({
                        start: seg.start,
                        end: seg.end,
                        text: seg.text,
                    })),
                    style: {
                        font: 'Kanit ExtraBold',
                        size: 'auto',
                        position: analysis?.subtitle_settings?.position || 'bottom',
                        color: 'white',
                        backgroundColor: null,
                        outline: true
                    },
                    keywords: analysis?.keywords || []
                },

                // Recommendations
                recommendations: {
                    targetDuration: null,
                    suggestedThumbnailTimestamp: null,
                    qualityScore: 75,
                    improvementSuggestions: []
                }
            })
        )

        const pythonResponse = await fetch(
            `${process.env.PYTHON_WORKER_URL || 'http://localhost:8000'}/process`,
            {
                method: 'POST',
                body: formData,
            }
        )

        if (!pythonResponse.ok) {
            const errorText = await pythonResponse.text()
            throw new Error(`Python worker failed: ${errorText}`)
        }

        await supabase
            .from('jobs')
            .update({
                progress_percentage: 80,
                current_step: 'กำลังบันทึกวิดีโอ...',
            })
            .eq('id', jobId)

        const processedVideo = await pythonResponse.blob()

        // Upload result
        const finalPath = `${job.user_id}/${jobId}/output.mp4`
        const { error: uploadError } = await supabase.storage
            .from('final-videos')
            .upload(finalPath, processedVideo, {
                contentType: 'video/mp4',
                upsert: true,
            })

        if (uploadError) throw uploadError

        // Complete
        await supabase
            .from('jobs')
            .update({
                status: 'COMPLETED',
                output_video_path: finalPath,
                progress_percentage: 100,
                current_step: 'เสร็จสิ้น',
                completed_at: new Date().toISOString(),
            })
            .eq('id', jobId)

        console.log(`✅ Job completed: ${jobId}`)

        return NextResponse.json({
            success: true,
            jobId,
            outputPath: finalPath,
            servicesUsed: availableServices,
        })
    } catch (error: any) {
        console.error('❌ Process job error:', error)

        try {
            const { jobId } = await request.json()
            if (jobId) {
                const supabase = createServiceClient()
                await supabase
                    .from('jobs')
                    .update({
                        status: 'FAILED',
                        error_message: error.message,
                        current_step: 'ล้มเหลว',
                    })
                    .eq('id', jobId)
            }
        } catch {
            // Ignore
        }

        return NextResponse.json({ error: error.message }, { status: 500 })
    }
}
