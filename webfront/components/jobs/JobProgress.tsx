'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import {
    Loader2, CheckCircle2, XCircle, Clock,
    Download, Play, AlertCircle
} from 'lucide-react'

interface Job {
    id: string
    job_name: string
    status: string
    progress_percentage: number
    current_step: string | null
    error_message: string | null
    output_video_path: string | null
    created_at: string
    completed_at: string | null
}

export default function JobProgress({ jobId }: { jobId: string }) {
    const [job, setJob] = useState<Job | null>(null)
    const [loading, setLoading] = useState(true)
    const supabase = createClient()
    const router = useRouter()

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
                    setJob(payload.new as Job)
                }
            )
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [jobId])

    const fetchJob = async () => {
        try {
            const { data, error } = await supabase
                .from('jobs')
                .select('*')
                .eq('id', jobId)
                .single()

            if (error) throw error
            setJob(data)
        } catch (error) {
            console.error('Error fetching job:', error)
        } finally {
            setLoading(false)
        }
    }

    const downloadVideo = async () => {
        if (!job?.output_video_path) return

        try {
            const { data, error } = await supabase.storage
                .from('final-videos')
                .createSignedUrl(job.output_video_path, 3600) // 1 hour

            if (error) throw error

            // Download file
            const link = document.createElement('a')
            link.href = data.signedUrl
            link.download = job.job_name.replace(/\.[^/.]+$/, '_edited.mp4')
            link.click()
        } catch (error) {
            console.error('Download error:', error)
            alert('ไม่สามารถดาวน์โหลดวิดีโอได้')
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
            </div>
        )
    }

    if (!job) {
        return (
            <div className="max-w-2xl mx-auto p-8">
                <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
                    <XCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-red-900 mb-2">
                        ไม่พบงาน
                    </h2>
                    <p className="text-red-700 mb-4">
                        ไม่พบงานที่คุณกำลังค้นหา
                    </p>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                    >
                        กลับไปหน้าแรก
                    </button>
                </div>
            </div>
        )
    }

    const getStatusIcon = () => {
        switch (job.status) {
            case 'COMPLETED':
                return <CheckCircle2 className="w-8 h-8 text-green-600" />
            case 'FAILED':
                return <XCircle className="w-8 h-8 text-red-600" />
            case 'PENDING':
            case 'UPLOADING':
                return <Clock className="w-8 h-8 text-yellow-600" />
            default:
                return <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        }
    }

    const getStatusColor = () => {
        switch (job.status) {
            case 'COMPLETED':
                return 'bg-green-100 text-green-800 border-green-200'
            case 'FAILED':
                return 'bg-red-100 text-red-800 border-red-200'
            case 'PENDING':
            case 'UPLOADING':
                return 'bg-yellow-100 text-yellow-800 border-yellow-200'
            default:
                return 'bg-blue-100 text-blue-800 border-blue-200'
        }
    }

    const getStatusText = () => {
        const statusMap: Record<string, string> = {
            PENDING: 'รอดำเนินการ',
            UPLOADING: 'กำลังอัปโหลด',
            QUEUED: 'อยู่ในคิว',
            TRANSCRIBING: 'กำลังถอดเสียง',
            ANALYZING: 'กำลังวิเคราะห์',
            RENDERING: 'กำลังตัดต่อ',
            COMPLETED: 'เสร็จสิ้น',
            FAILED: 'ล้มเหลว',
            CANCELLED: 'ยกเลิก',
        }
        return statusMap[job.status] || job.status
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12">
            <div className="max-w-4xl mx-auto p-8">
                <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">
                                {job.job_name}
                            </h1>
                            <p className="text-gray-600">
                                สร้างเมื่อ: {new Date(job.created_at).toLocaleString('th-TH')}
                            </p>
                        </div>
                        <div className={`px-4 py-2 rounded-full border ${getStatusColor()} flex items-center gap-2`}>
                            {getStatusIcon()}
                            <span className="font-semibold">{getStatusText()}</span>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    {job.status !== 'COMPLETED' && job.status !== 'FAILED' && (
                        <div className="mb-8">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium text-gray-700">
                                    {job.current_step || 'กำลังประมวลผล...'}
                                </span>
                                <span className="text-sm font-medium text-blue-600">
                                    {job.progress_percentage}%
                                </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                                <div
                                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-4 rounded-full transition-all duration-500 ease-out"
                                    style={{ width: `${job.progress_percentage}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Completed State */}
                    {job.status === 'COMPLETED' && job.output_video_path && (
                        <div className="mb-8">
                            <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                                    <h3 className="text-lg font-semibold text-green-900">
                                        วิดีโอตัดต่อเสร็จแล้ว!
                                    </h3>
                                </div>
                                <p className="text-green-700 mb-4">
                                    วิดีโอของคุณพร้อมแล้ว คุณสามารถดาวน์โหลดได้เลย
                                </p>
                                <div className="flex gap-3">
                                    <button
                                        onClick={downloadVideo}
                                        className="flex-1 bg-green-600 text-white py-3 px-6 rounded-xl font-semibold hover:bg-green-700 transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
                                    >
                                        <Download className="w-5 h-5" />
                                        ดาวน์โหลดวิดีโอ
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Failed State */}
                    {job.status === 'FAILED' && (
                        <div className="mb-8">
                            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <AlertCircle className="w-6 h-6 text-red-600" />
                                    <h3 className="text-lg font-semibold text-red-900">
                                        เกิดข้อผิดพลาด
                                    </h3>
                                </div>
                                <p className="text-red-700 mb-2">
                                    {job.error_message || 'ไม่สามารถประมวลผลวิดีโอได้'}
                                </p>
                                <button
                                    onClick={() => router.push('/upload')}
                                    className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                                >
                                    ลองอีกครั้ง
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Processing Steps */}
                    <div className="space-y-3">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">
                            ขั้นตอนการประมวลผล
                        </h3>
                        {[
                            { step: 'UPLOADING', label: 'อัปโหลดวิดีโอ', icon: '📤' },
                            { step: 'TRANSCRIBING', label: 'ถอดเสียงด้วย AI', icon: '🎙️' },
                            { step: 'ANALYZING', label: 'วิเคราะห์เนื้อหา', icon: '🧠' },
                            { step: 'RENDERING', label: 'ตัดต่อวิดีโอ', icon: '🎬' },
                            { step: 'COMPLETED', label: 'เสร็จสิ้น', icon: '✅' },
                        ].map((item, index) => {
                            const isActive = job.status === item.step
                            const isDone = ['COMPLETED'].includes(job.status) ||
                                (job.progress_percentage > (index * 25))

                            return (
                                <div
                                    key={item.step}
                                    className={`flex items-center gap-4 p-4 rounded-lg border ${isActive
                                            ? 'bg-blue-50 border-blue-200'
                                            : isDone
                                                ? 'bg-green-50 border-green-200'
                                                : 'bg-gray-50 border-gray-200'
                                        }`}
                                >
                                    <span className="text-2xl">{item.icon}</span>
                                    <span className={`font-medium ${isActive ? 'text-blue-900' : isDone ? 'text-green-900' : 'text-gray-600'
                                        }`}>
                                        {item.label}
                                    </span>
                                    {isActive && (
                                        <Loader2 className="w-5 h-5 text-blue-600 animate-spin ml-auto" />
                                    )}
                                    {isDone && !isActive && (
                                        <CheckCircle2 className="w-5 h-5 text-green-600 ml-auto" />
                                    )}
                                </div>
                            )
                        })}
                    </div>
                </div>
            </div>
        </div>
    )
}
