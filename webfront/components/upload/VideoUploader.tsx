'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Upload, Loader2 } from 'lucide-react'

export default function VideoUploader() {
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [error, setError] = useState<string | null>(null)
    const router = useRouter()
    const supabase = createClient()

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0]
        if (selectedFile) {
            if (!selectedFile.type.startsWith('video/')) {
                setError('กรุณาเลือกไฟล์วิดีโอเท่านั้น')
                return
            }

            if (selectedFile.size > 50 * 1024 * 1024) {
                setError('ไฟล์ใหญ่เกิน 50MB')
                return
            }

            setFile(selectedFile)
            setError(null)
        }
    }

    const handleUpload = async () => {
        if (!file) return

        try {
            setUploading(true)
            setError(null)
            setProgress(10)

            const userId = '00000000-0000-0000-0000-000000000001'

            setProgress(20)

            const { data: job, error: jobError } = await supabase
                .from('jobs')
                .insert({
                    job_name: file.name,
                    status: 'UPLOADING',
                    input_file_size_mb: file.size / (1024 * 1024),
                    user_id: userId,
                })
                .select()
                .single()

            if (jobError) {
                console.error('Job creation error:', jobError)
                throw new Error(`Database error: ${jobError.message}`)
            }

            setProgress(40)

            const filePath = `${userId}/${job.id}/${file.name}`

            const { error: uploadError } = await supabase.storage
                .from('raw-videos')
                .upload(filePath, file, {
                    cacheControl: '3600',
                    upsert: false,
                })

            if (uploadError) {
                console.error('Storage upload error:', uploadError)
                throw new Error(`Upload error: ${uploadError.message}`)
            }

            setProgress(70)

            const { error: updateError } = await supabase
                .from('jobs')
                .update({
                    input_video_path: filePath,
                    status: 'PENDING',
                })
                .eq('id', job.id)

            if (updateError) {
                console.error('Job update error:', updateError)
                throw new Error(`Update error: ${updateError.message}`)
            }

            setProgress(90)

            const response = await fetch('/api/jobs/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jobId: job.id }),
            })

            if (!response.ok) {
                throw new Error('ไม่สามารถเริ่มประมวลผลได้')
            }

            setProgress(100)
            router.push(`/jobs/${job.id}`)
        } catch (err: any) {
            console.error('Upload error:', err)
            setError(err.message || 'เกิดข้อผิดพลาดในการอัปโหลด')
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="max-w-2xl mx-auto p-8">
            <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-4">
                        <Upload className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">
                        อัปโหลดวิดีโอ
                    </h2>
                    <p className="text-gray-600">
                        AI จะตัดต่อวิดีโอให้คุณอัตโนมัติ
                    </p>
                </div>

                <div className="mb-6">
                    <label htmlFor="video-upload" className="block w-full cursor-pointer">
                        <div className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-blue-500 hover:bg-blue-50 transition-all">
                            {file ? (
                                <div>
                                    <p className="text-lg font-semibold text-gray-900 mb-2">{file.name}</p>
                                    <p className="text-sm text-gray-600">ขนาด: {(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                                </div>
                            ) : (
                                <div>
                                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                                    <p className="text-lg font-semibold text-gray-900 mb-2">คลิกเพื่อเลือกวิดีโอ</p>
                                    <p className="text-sm text-gray-600">รองรับ MP4, MOV, AVI (สูงสุด 50MB)</p>
                                </div>
                            )}
                        </div>
                        <input
                            id="video-upload"
                            type="file"
                            accept="video/*"
                            onChange={handleFileChange}
                            disabled={uploading}
                            className="hidden"
                        />
                    </label>
                </div>

                {uploading && (
                    <div className="mb-6">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-700">กำลังอัปโหลด...</span>
                            <span className="text-sm font-medium text-blue-600">{progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                            <div
                                className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                )}

                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-800">{error}</p>
                    </div>
                )}

                <button
                    onClick={handleUpload}
                    disabled={!file || uploading}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
                >
                    {uploading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            กำลังอัปโหลด...
                        </>
                    ) : (
                        <>
                            <Upload className="w-5 h-5" />
                            เริ่มตัดต่อวิดีโอ
                        </>
                    )}
                </button>

                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-800">
                        💡 <strong>เคล็ดลับ:</strong> วิดีโอที่มีเสียงพูดชัดเจนจะได้ผลลัพธ์ที่ดีที่สุด
                    </p>
                </div>
            </div>
        </div>
    )
}
